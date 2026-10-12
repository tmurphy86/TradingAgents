import asyncio
import json
import logging
import threading
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from tradingagents.dataflows.utils import safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import RunCancelled, TradingAgentsGraph

logger = logging.getLogger(__name__)

RUNS_DIR = Path.home() / ".tradingagents" / "runs"
WATCHLISTS_FILE = Path.home() / ".tradingagents" / "watchlists.json"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
WATCHLISTS_FILE.parent.mkdir(parents=True, exist_ok=True)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

VALID_ANALYSTS = {"market", "social", "news", "fundamentals"}

# In-memory state: run records + per-run async queues
_run_records: dict[str, dict] = {}
_run_queues: dict[str, asyncio.Queue] = {}
# Per-run cancel flags. Present only while the run's worker thread is alive;
# set by the cancel/delete endpoints, polled by the graph between steps.
_run_cancels: dict[str, threading.Event] = {}
# Serialises a worker's terminal record write against DELETE, so a deleted
# run's file can never be recreated by its worker.
_runs_lock = threading.Lock()

_FINISHED_STATUSES = ("complete", "error", "cancelled")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Mark any runs that were 'running' when the server last died as errors."""
    for p in RUNS_DIR.glob("*.json"):
        try:
            with open(p) as f:
                record = json.load(f)
            if record.get("status") == "running":
                record["status"] = "error"
                record["error"] = "Server restarted while run was active."
                with open(p, "w") as f:
                    json.dump(record, f, indent=2)
        except Exception:
            pass
    yield


def _utcnow_iso() -> str:
    """Naive-UTC ISO timestamp (no offset suffix) - the stored/consumed shape."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


app = FastAPI(title="TradingAgents API", version="0.3.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _runs_file(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.json"


def _save_run(run_id: str) -> None:
    record = _run_records.get(run_id)
    if record:
        with open(_runs_file(run_id), "w") as f:
            json.dump(record, f, indent=2, default=str)


def _get_run_record(run_id: str) -> Optional[dict]:
    if run_id in _run_records:
        return _run_records[run_id]
    f = _runs_file(run_id)
    if f.exists():
        with open(f) as fp:
            record = json.load(fp)
            _run_records[run_id] = record
            return record
    return None


def _list_runs() -> list[dict]:
    runs = []
    for p in sorted(RUNS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(p) as f:
                data = json.load(f)
                # Return lightweight summary (omit full events list)
                runs.append({k: v for k, v in data.items() if k != "events"})
        except Exception:
            pass
    return runs


def _load_watchlists() -> list[dict]:
    if WATCHLISTS_FILE.exists():
        with open(WATCHLISTS_FILE) as f:
            return json.load(f)
    return []


def _save_watchlists(watchlists: list[dict]) -> None:
    with open(WATCHLISTS_FILE, "w") as f:
        json.dump(watchlists, f, indent=2)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    ticker: str
    date: str
    llm_provider: str = "openai"
    deep_think_llm: str = DEFAULT_CONFIG.get("deep_think_llm", "gpt-4o")
    quick_think_llm: str = DEFAULT_CONFIG.get("quick_think_llm", "gpt-4o-mini")
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    analysts: list[str] = ["market", "social", "news", "fundamentals"]
    asset_type: Literal["stock", "crypto"] = "stock"

    @field_validator("ticker")
    @classmethod
    def _v_ticker(cls, v: str) -> str:
        return safe_ticker_component(v).upper()

    @field_validator("date")
    @classmethod
    def _v_date(cls, v: str) -> str:
        from datetime import date as date_cls

        date_cls.fromisoformat(v)
        return v

    @field_validator("analysts")
    @classmethod
    def _v_analysts(cls, v: list[str]) -> list[str]:
        unknown = set(v) - VALID_ANALYSTS
        if unknown:
            raise ValueError(
                f"unknown analysts: {sorted(unknown)}. Valid keys: {sorted(VALID_ANALYSTS)}"
            )
        return v


class WatchlistRequest(BaseModel):
    name: str
    tickers: list[str]


# ---------------------------------------------------------------------------
# Background execution
# ---------------------------------------------------------------------------


def _safe_dict(v: Any) -> Any:
    """Strip LangChain BaseMessage objects; convert TypedDicts to plain dicts."""
    if isinstance(v, dict):
        return {k: _safe_dict(vv) for k, vv in v.items() if k != "messages"}
    if isinstance(v, list):
        return [_safe_dict(i) for i in v]
    return v


def _execute_run(run_id: str, req: RunRequest, loop: asyncio.AbstractEventLoop) -> None:
    """Runs in a daemon thread; puts SSE events onto the asyncio queue."""
    q = _run_queues.get(run_id)
    cancel_event = _run_cancels.get(run_id)

    def emit(event: dict) -> None:
        # Accumulate events on the record for replay on reconnect
        record = _run_records.get(run_id)
        if record is not None:
            record.setdefault("events", []).append(event)
        if q is not None:
            loop.call_soon_threadsafe(q.put_nowait, event)

    def finish(update: dict, event: dict) -> None:
        """Write the run's terminal state. No-op if the run was deleted meanwhile."""
        with _runs_lock:
            record = _run_records.get(run_id)
            if record is None:
                return
            record.update(update)
            record.setdefault("events", []).append(event)
            _save_run(run_id)
        if q:
            loop.call_soon_threadsafe(q.put_nowait, event)

    try:
        config = DEFAULT_CONFIG.copy()
        config.update(
            {
                "llm_provider": req.llm_provider,
                "deep_think_llm": req.deep_think_llm,
                "quick_think_llm": req.quick_think_llm,
                "max_debate_rounds": req.max_debate_rounds,
                "max_risk_discuss_rounds": req.max_risk_discuss_rounds,
            }
        )

        ta = TradingAgentsGraph(selected_analysts=req.analysts, config=config)
        final_state, decision = ta.propagate(
            req.ticker,
            req.date,
            asset_type=req.asset_type,
            event_callback=emit,
            cancel_event=cancel_event,
        )

        result: dict = {
            "decision": decision,
            "market_report": final_state.get("market_report", ""),
            "sentiment_report": final_state.get("sentiment_report", ""),
            "news_report": final_state.get("news_report", ""),
            "fundamentals_report": final_state.get("fundamentals_report", ""),
            "investment_plan": final_state.get("investment_plan", ""),
            "trader_investment_plan": final_state.get("trader_investment_plan", ""),
            "final_trade_decision": final_state.get("final_trade_decision", ""),
            "investment_debate_state": _safe_dict(
                dict(final_state.get("investment_debate_state") or {})
            ),
            "risk_debate_state": _safe_dict(dict(final_state.get("risk_debate_state") or {})),
        }

        finish(
            {
                "status": "complete",
                "completed_at": _utcnow_iso(),
                "result": result,
            },
            {"type": "run_complete", "decision": decision, "result": result},
        )

    except RunCancelled:
        logger.info("Run %s cancelled", run_id)
        finish(
            {"status": "cancelled", "completed_at": _utcnow_iso()},
            {"type": "run_cancelled"},
        )
    except Exception as e:
        logger.exception("Run %s failed", run_id)
        finish({"status": "error", "error": str(e)}, {"type": "run_error", "message": str(e)})
    finally:
        if q:
            loop.call_soon_threadsafe(q.put_nowait, None)  # sentinel
        _run_queues.pop(run_id, None)
        _run_cancels.pop(run_id, None)


# ---------------------------------------------------------------------------
# Run endpoints
# ---------------------------------------------------------------------------


@app.post("/api/runs")
async def create_run(req: RunRequest) -> dict:
    run_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = q
    _run_cancels[run_id] = threading.Event()

    record: dict = {
        "run_id": run_id,
        "ticker": req.ticker,
        "date": req.date,
        "status": "running",
        "started_at": _utcnow_iso(),
        "completed_at": None,
        "config": req.model_dump(),
        "result": None,
        "events": [],
        "error": None,
    }
    _run_records[run_id] = record
    _save_run(run_id)

    loop = asyncio.get_running_loop()
    threading.Thread(
        target=_execute_run,
        args=(run_id, req, loop),
        daemon=True,
    ).start()

    return {"run_id": run_id}


@app.get("/api/runs")
async def list_runs() -> list:
    return _list_runs()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    record = _get_run_record(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    return {k: v for k, v in record.items() if k != "events"}


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: str) -> dict:
    record = _get_run_record(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    with _runs_lock:
        # Cancel first so a live worker stops before its next graph step; it
        # finds no record when it winds down and therefore writes nothing.
        cancel_event = _run_cancels.get(run_id)
        if cancel_event is not None:
            cancel_event.set()
        _run_records.pop(run_id, None)
        _run_queues.pop(run_id, None)
        _runs_file(run_id).unlink(missing_ok=True)
    return {"deleted": run_id}


@app.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict:
    record = _get_run_record(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    cancel_event = _run_cancels.get(run_id)
    if record["status"] in _FINISHED_STATUSES or cancel_event is None:
        raise HTTPException(409, f"Run is not in progress (status: {record['status']})")
    # Cooperative: the worker notices between graph steps and persists the
    # cancelled record itself.
    cancel_event.set()
    return {"run_id": run_id, "status": "cancelling"}


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    record = _get_run_record(run_id)
    if not record:
        raise HTTPException(404, "Run not found")

    # If run is marked running but server was restarted (no queue), mark error
    if record["status"] == "running" and run_id not in _run_queues:
        record["status"] = "error"
        record["error"] = "Server restarted while run was active."
        _run_records[run_id] = record
        _save_run(run_id)

    stored_events: list = list(record.get("events", []))

    async def generate():
        # Replay stored events first (catches up late subscribers)
        for ev in stored_events:
            yield f"data: {json.dumps(ev)}\n\n"

        if record["status"] in _FINISHED_STATUSES:
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
            return

        # Live run — subscribe to queue for remaining events
        live_q = _run_queues.get(run_id)
        if not live_q:
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
            return

        while True:
            ev = await live_q.get()
            if ev is None:
                yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                break
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


# ---------------------------------------------------------------------------
# Watchlist endpoints
# ---------------------------------------------------------------------------


@app.get("/api/watchlists")
async def list_watchlists() -> list:
    return _load_watchlists()


@app.post("/api/watchlists")
async def create_watchlist(req: WatchlistRequest) -> dict:
    watchlists = _load_watchlists()
    wl = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "tickers": [t.strip().upper() for t in req.tickers if t.strip()],
        "created_at": _utcnow_iso(),
    }
    watchlists.append(wl)
    _save_watchlists(watchlists)
    return wl


@app.put("/api/watchlists/{wl_id}")
async def update_watchlist(wl_id: str, req: WatchlistRequest) -> dict:
    watchlists = _load_watchlists()
    for wl in watchlists:
        if wl["id"] == wl_id:
            wl["name"] = req.name
            wl["tickers"] = [t.strip().upper() for t in req.tickers if t.strip()]
            _save_watchlists(watchlists)
            return wl
    raise HTTPException(404, "Watchlist not found")


@app.delete("/api/watchlists/{wl_id}")
async def delete_watchlist(wl_id: str) -> dict:
    watchlists = _load_watchlists()
    new_wls = [w for w in watchlists if w["id"] != wl_id]
    if len(new_wls) == len(watchlists):
        raise HTTPException(404, "Watchlist not found")
    _save_watchlists(new_wls)
    return {"deleted": wl_id}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve built frontend (must be last — catches all unmatched routes)
# ---------------------------------------------------------------------------

_UI_DIST = Path(__file__).parent.parent / "ui" / "dist"
if _UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")
