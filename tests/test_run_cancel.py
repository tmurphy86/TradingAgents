"""Regression tests for run cancellation (issue #9).

A run in progress must stop spending tokens once it is cancelled or deleted.

The API tests drive the real ``api.main`` app and the real ``_execute_run``
worker thread. Only the compiled LangGraph is replaced: ``TradingAgentsGraph``
is subclassed so that construction needs no LLM clients, while ``propagate``
and ``_run_graph`` are the production implementations running against a fake
``graph.stream`` generator. Each step of that generator stands in for one
graph node (one or more LLM calls), so "no further steps" means "no further
tokens".

Everything is synchronised with ``threading.Event`` — there are no sleeps.

Run:  docker compose run --rm test pytest tests/test_run_cancel.py -v
"""

from __future__ import annotations

import asyncio
import json
import threading
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import api.main as api_module
from api.main import _run_queues, _run_records, app
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.trading_graph import TradingAgentsGraph

# Generous upper bound for cross-thread hand-offs; only ever hit on failure.
_TIMEOUT = 10

_VALID_RUN = {
    "ticker": "AAPL",
    "date": "2026-01-15",
    "llm_provider": "openai",
    "analysts": ["market", "news"],
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "asset_type": "stock",
}

# One watched field per fake graph step, in pipeline order.
_STEPS = [
    "market_report",
    "news_report",
    "investment_plan",
    "trader_investment_plan",
    "final_trade_decision",
]
_HOLD_AT = 1  # the run is held while this step (index) is "in flight"


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _SteppedGraph:
    """Stands in for the compiled LangGraph.

    ``stream`` yields one full-state snapshot per step (``stream_mode="values"``
    semantics). ``executed`` records every step whose node body ran. While step
    ``hold_at`` is in flight the generator signals ``reached`` and blocks until
    ``release`` is set, which lets a test issue a cancel/delete mid-run.
    """

    def __init__(self, hold_at: int | None = _HOLD_AT):
        self.hold_at = hold_at
        self.executed: list[str] = []
        self.reached = threading.Event()
        self.release = threading.Event()

    def stream(self, init_state, **_kwargs):
        state = dict(init_state)
        for i, field in enumerate(_STEPS):
            self.executed.append(field)  # the node runs here — this is the token spend
            state = {**state, field: f"{field} content"}
            if i == self.hold_at:
                self.reached.set()
                assert self.release.wait(_TIMEOUT), "test never released the held step"
            yield state


def _stub_graph_cls(fake_graph: _SteppedGraph, tmp_path):
    """A TradingAgentsGraph whose constructor skips LLM/graph setup.

    ``propagate`` / ``_run_graph`` / ``_emit_state_events`` are inherited
    unchanged, so the production cancellation path is what gets exercised.
    """

    class _StubTradingAgentsGraph(TradingAgentsGraph):
        def __init__(self, selected_analysts=None, debug=False, config=None, callbacks=None):
            self.debug = False
            self.config = {
                "results_dir": str(tmp_path / "results"),
                "data_cache_dir": str(tmp_path / "cache"),
                "checkpoint_enabled": False,
            }
            self.callbacks = []
            self.propagator = Propagator()
            self.memory_log = MagicMock()
            self.memory_log.get_pending_entries.return_value = []
            self.memory_log.get_past_context.return_value = ""
            self.signal_processor = MagicMock()
            self.signal_processor.process_signal.return_value = "Buy"
            self.graph = fake_graph
            self._checkpointer_ctx = None
            self.curr_state = None
            self.ticker = None
            self.log_states_dict = {}

    return _StubTradingAgentsGraph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Redirect filesystem storage to tmp_path and clear in-memory state."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setattr(api_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(api_module, "WATCHLISTS_FILE", tmp_path / "watchlists.json")

    _run_records.clear()
    _run_queues.clear()
    yield
    _run_records.clear()
    _run_queues.clear()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def fake_graph(tmp_path, monkeypatch):
    """Install the stepped stub graph behind ``api.main.TradingAgentsGraph``."""
    fake = _SteppedGraph()
    monkeypatch.setattr(api_module, "TradingAgentsGraph", _stub_graph_cls(fake, tmp_path))
    yield fake
    fake.release.set()  # never leave a worker thread parked


@pytest.fixture()
def worker(monkeypatch):
    """Observe the real ``_execute_run``: when it returned and whether it raised."""
    real_execute_run = api_module._execute_run
    observed = MagicMock()
    observed.done = threading.Event()
    observed.errors = []

    def _observed_execute_run(*args, **kwargs):
        try:
            real_execute_run(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - recorded for the assertion
            observed.errors.append(exc)
            raise
        finally:
            observed.done.set()

    monkeypatch.setattr(api_module, "_execute_run", _observed_execute_run)
    return observed


def _start_held_run(client, fake_graph) -> str:
    """Start a run and wait until its worker is parked mid-step."""
    run_id = client.post("/api/runs", json=_VALID_RUN).json()["run_id"]
    assert fake_graph.reached.wait(_TIMEOUT), "worker never reached the held step"
    return run_id


def _drain(client, q: asyncio.Queue) -> list:
    """Return everything the worker pushed onto a run's live queue."""
    # The worker hands events over with loop.call_soon_threadsafe; a round trip
    # through the app's loop guarantees those callbacks have run.
    client.get("/health")
    items = []
    while True:
        try:
            items.append(q.get_nowait())
        except asyncio.QueueEmpty:
            return items


# ---------------------------------------------------------------------------
# API layer — real app, real _execute_run thread, real _run_graph
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestCancelRunningRun:
    def test_cancel_stops_graph_before_next_step(self, client, fake_graph, worker, tmp_path):
        run_id = _start_held_run(client, fake_graph)
        live_q = _run_queues[run_id]

        r = client.post(f"/api/runs/{run_id}/cancel")
        fake_graph.release.set()
        assert worker.done.wait(_TIMEOUT), "worker thread did not finish"

        # The step that was in flight finishes; nothing after it starts.
        assert fake_graph.executed == _STEPS[: _HOLD_AT + 1]
        assert r.status_code == 200
        assert worker.errors == []

        # Record is persisted as cancelled, in memory and on disk.
        record = _run_records[run_id]
        assert record["status"] == "cancelled"
        assert record["completed_at"] is not None
        on_disk = json.loads((tmp_path / "runs" / f"{run_id}.json").read_text())
        assert on_disk["status"] == "cancelled"
        assert on_disk["completed_at"] is not None
        assert on_disk["result"] is None

        # Live stream: run_cancelled, then the sentinel, and nothing else after.
        events = _drain(client, live_q)
        types = [e["type"] if e else None for e in events]
        assert types[-2:] == ["run_cancelled", None]
        assert "run_complete" not in types
        assert "run_error" not in types

        # Reconnecting replays run_cancelled and closes the stream.
        body = client.get(f"/api/runs/{run_id}/stream").text
        assert "run_cancelled" in body
        assert "stream_end" in body

        # The run is finished now, so a second cancel is a conflict.
        assert client.post(f"/api/runs/{run_id}/cancel").status_code == 409
        assert client.get(f"/api/runs/{run_id}").json()["status"] == "cancelled"

    def test_delete_running_run_stops_graph_and_stays_deleted(
        self, client, fake_graph, worker, tmp_path
    ):
        run_id = _start_held_run(client, fake_graph)
        run_file = tmp_path / "runs" / f"{run_id}.json"
        assert run_file.exists()

        r = client.delete(f"/api/runs/{run_id}")
        fake_graph.release.set()
        assert worker.done.wait(_TIMEOUT), "worker thread did not finish"

        # The step that was in flight finishes; nothing after it starts.
        assert fake_graph.executed == _STEPS[: _HOLD_AT + 1]
        assert r.status_code == 200
        assert r.json() == {"deleted": run_id}

        # The worker neither raised nor resurrected the record.
        assert worker.errors == []
        assert run_id not in _run_records
        assert not run_file.exists()
        assert client.get(f"/api/runs/{run_id}").status_code == 404

    def test_uncancelled_run_still_completes(self, client, fake_graph, worker):
        """Guard: the cancel plumbing must not disturb a normal run."""
        fake_graph.release.set()
        run_id = client.post("/api/runs", json=_VALID_RUN).json()["run_id"]
        assert worker.done.wait(_TIMEOUT), "worker thread did not finish"

        assert fake_graph.executed == _STEPS
        record = _run_records[run_id]
        assert record["status"] == "complete"
        assert record["result"]["decision"] == "Buy"
        types = [e["type"] for e in record["events"]]
        assert types.count("agent_update") == len(_STEPS)
        assert types[-1] == "run_complete"
        # A finished run cannot be cancelled.
        assert client.post(f"/api/runs/{run_id}/cancel").status_code == 409


@pytest.mark.regression
class TestStartupHealing:
    def test_cancelled_run_not_rewritten_on_startup(self, tmp_path):
        record = {
            "run_id": "c-1",
            "ticker": "AAPL",
            "date": "2026-01-15",
            "status": "cancelled",
            "started_at": "2026-01-15T10:00:00",
            "completed_at": "2026-01-15T10:01:00",
            "config": _VALID_RUN,
            "result": None,
            "events": [{"type": "run_cancelled"}],
            "error": None,
        }
        run_file = tmp_path / "runs" / "c-1.json"
        run_file.write_text(json.dumps(record, indent=2))

        with TestClient(app) as c:  # entering the client runs the startup handler
            assert c.get("/api/runs/c-1").json()["status"] == "cancelled"

        assert json.loads(run_file.read_text()) == record


# ---------------------------------------------------------------------------
# Graph layer — the real _run_graph against a fake graph.stream
# ---------------------------------------------------------------------------


def _bare_graph(fake_graph: _SteppedGraph, tmp_path) -> TradingAgentsGraph:
    return _stub_graph_cls(fake_graph, tmp_path)()


@pytest.mark.unit
class TestRunGraphCancellation:
    def test_stops_between_steps_when_cancel_set_mid_stream(self, tmp_path):
        from tradingagents.graph.trading_graph import RunCancelled

        fake = _SteppedGraph(hold_at=None)
        ta = _bare_graph(fake, tmp_path)
        cancel = threading.Event()
        events: list[dict] = []

        def on_event(event: dict) -> None:
            events.append(event)
            if event["field"] == _STEPS[1]:
                cancel.set()  # cancel arrives while step 1's output is being emitted

        with pytest.raises(RunCancelled):
            ta.propagate("AAPL", "2026-01-15", event_callback=on_event, cancel_event=cancel)

        assert fake.executed == _STEPS[:2]
        # Output produced before the cancel is still emitted, via the unchanged diff logic.
        assert [e["field"] for e in events] == _STEPS[:2]
        # A cancelled run is not recorded as a decision and writes no state log.
        ta.memory_log.store_decision.assert_not_called()
        ta.signal_processor.process_signal.assert_not_called()
        assert not (tmp_path / "results").exists()

    def test_cancel_set_before_start_runs_no_step(self, tmp_path):
        from tradingagents.graph.trading_graph import RunCancelled

        fake = _SteppedGraph(hold_at=None)
        ta = _bare_graph(fake, tmp_path)
        cancel = threading.Event()
        cancel.set()

        with pytest.raises(RunCancelled):
            ta.propagate("AAPL", "2026-01-15", event_callback=lambda e: None, cancel_event=cancel)

        assert fake.executed == []
        # Pending-entry reflection (an LLM call) is skipped too.
        ta.memory_log.get_pending_entries.assert_not_called()

    def test_cancel_event_without_callback_still_cancels(self, tmp_path):
        from tradingagents.graph.trading_graph import RunCancelled

        fake = _SteppedGraph(hold_at=None)
        ta = _bare_graph(fake, tmp_path)
        cancel = threading.Event()
        real_stream = fake.stream

        def stream_then_cancel(init_state, **kwargs):
            for i, state in enumerate(real_stream(init_state, **kwargs)):
                if i == 0:
                    cancel.set()
                yield state

        fake.stream = stream_then_cancel

        with pytest.raises(RunCancelled):
            ta.propagate("AAPL", "2026-01-15", cancel_event=cancel)

        assert fake.executed == _STEPS[:1]

    def test_unset_cancel_event_runs_to_completion(self, tmp_path):
        fake = _SteppedGraph(hold_at=None)
        ta = _bare_graph(fake, tmp_path)
        events: list[dict] = []

        final_state, decision = ta.propagate(
            "AAPL", "2026-01-15", event_callback=events.append, cancel_event=threading.Event()
        )

        assert fake.executed == _STEPS
        assert decision == "Buy"
        assert final_state["final_trade_decision"] == "final_trade_decision content"
        assert [e["field"] for e in events] == _STEPS
        ta.memory_log.store_decision.assert_called_once()

    def test_default_call_without_cancel_event_uses_invoke(self, tmp_path):
        """CLI path: no callback, no cancel event -> graph.invoke, exactly as before."""
        fake = _SteppedGraph(hold_at=None)
        full_state: dict = {}

        def invoke(init_state, **_kwargs):
            for state in fake.stream(init_state):
                full_state.update(state)
            return full_state

        fake.invoke = invoke
        ta = _bare_graph(fake, tmp_path)

        final_state, decision = ta.propagate("AAPL", "2026-01-15")

        assert final_state is full_state
        assert decision == "Buy"
        ta.memory_log.store_decision.assert_called_once()
