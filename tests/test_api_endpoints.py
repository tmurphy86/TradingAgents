"""Regression tests for the FastAPI API surface.

All LLM and graph calls are mocked — these tests verify routing,
request validation, persistence, SSE event shape, and watchlist CRUD
without requiring any external services.

Run:  docker compose run --rm test pytest tests/test_api_endpoints.py -v
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import api.main as api_module
from api.main import _run_queues, _run_records, app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_RUN = {
    "ticker": "AAPL",
    "date": "2026-01-15",
    "llm_provider": "openai",
    "analysts": ["market", "news"],
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "asset_type": "stock",
}


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Redirect filesystem storage to tmp_path and clear in-memory state before each test."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    watchlists_file = tmp_path / "watchlists.json"

    monkeypatch.setattr(api_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(api_module, "WATCHLISTS_FILE", watchlists_file)

    _run_records.clear()
    _run_queues.clear()
    yield
    _run_records.clear()
    _run_queues.clear()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _seed_run(run_id: str, status: str = "complete", events: list | None = None) -> dict:
    """Insert a fake run record directly into in-memory state (no LLM needed)."""
    record: dict = {
        "run_id": run_id,
        "ticker": "TSLA",
        "date": "2026-01-15",
        "status": status,
        "started_at": "2026-01-15T10:00:00",
        "completed_at": "2026-01-15T10:05:00" if status == "complete" else None,
        "config": _VALID_RUN,
        "result": {"decision": "Buy"} if status == "complete" else None,
        "events": events or [],
        "error": None,
    }
    _run_records[run_id] = record
    api_module._save_run(run_id)
    return record


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestHealth:
    def test_returns_ok(self, client):
        assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/runs — create
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestRunCreate:
    def test_returns_run_id(self, client):
        with patch("api.main._execute_run"):
            r = client.post("/api/runs", json=_VALID_RUN)
        assert r.status_code == 200
        assert "run_id" in r.json()

    def test_record_persisted_to_disk(self, client, tmp_path):
        with patch("api.main._execute_run"):
            run_id = client.post("/api/runs", json=_VALID_RUN).json()["run_id"]
        saved = tmp_path / "runs" / f"{run_id}.json"
        assert saved.exists()
        record = json.loads(saved.read_text())
        assert record["ticker"] == "AAPL"
        assert record["status"] == "running"

    def test_ticker_uppercased(self, client):
        with patch("api.main._execute_run"):
            run_id = client.post("/api/runs", json={**_VALID_RUN, "ticker": "aapl"}).json()[
                "run_id"
            ]
        assert _run_records[run_id]["ticker"] == "AAPL"

    def test_path_traversal_ticker_rejected(self, client):
        r = client.post("/api/runs", json={**_VALID_RUN, "ticker": "../etc/passwd"})
        assert r.status_code == 422

    def test_invalid_date_rejected(self, client):
        r = client.post("/api/runs", json={**_VALID_RUN, "date": "not-a-date"})
        assert r.status_code == 422

    def test_unknown_analyst_rejected(self, client):
        r = client.post("/api/runs", json={**_VALID_RUN, "analysts": ["market", "macro"]})
        assert r.status_code == 422

    def test_invalid_asset_type_rejected(self, client):
        r = client.post("/api/runs", json={**_VALID_RUN, "asset_type": "nft"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/runs & GET /api/runs/{id}
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestRunRead:
    def test_get_existing_run_excludes_events(self, client):
        _seed_run("r1")
        r = client.get("/api/runs/r1")
        assert r.status_code == 200
        data = r.json()
        assert data["run_id"] == "r1"
        assert "events" not in data

    def test_get_missing_run_returns_404(self, client):
        assert client.get("/api/runs/no-such").status_code == 404

    def test_list_runs_returns_all_persisted(self, client):
        _seed_run("r1")
        _seed_run("r2")
        runs = client.get("/api/runs").json()
        assert len(runs) == 2

    def test_list_runs_empty(self, client):
        assert client.get("/api/runs").json() == []

    def test_list_runs_excludes_events_field(self, client):
        _seed_run("r1", events=[{"type": "agent_update", "content": "x"}])
        for run in client.get("/api/runs").json():
            assert "events" not in run


# ---------------------------------------------------------------------------
# DELETE /api/runs/{id}
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestRunDelete:
    def test_delete_existing(self, client, tmp_path):
        _seed_run("del-1")
        r = client.delete("/api/runs/del-1")
        assert r.status_code == 200
        assert r.json()["deleted"] == "del-1"
        assert "del-1" not in _run_records
        assert not (tmp_path / "runs" / "del-1.json").exists()

    def test_delete_missing_returns_404(self, client):
        assert client.delete("/api/runs/no-such").status_code == 404


# ---------------------------------------------------------------------------
# GET /api/runs/{id}/stream
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestSSEStream:
    def test_stream_missing_run_returns_404(self, client):
        assert client.get("/api/runs/no-such/stream").status_code == 404

    def test_stream_replays_stored_events_and_ends(self, client):
        _seed_run(
            "sse-1",
            events=[
                {"type": "agent_update", "agent": "Market Analyst", "content": "report"},
                {"type": "run_complete", "decision": "Buy"},
            ],
        )
        r = client.get("/api/runs/sse-1/stream")
        assert r.status_code == 200
        body = r.text
        assert "agent_update" in body
        assert "run_complete" in body
        assert "stream_end" in body

    def test_stream_content_type_is_sse(self, client):
        _seed_run("sse-2")
        r = client.get("/api/runs/sse-2/stream")
        assert "text/event-stream" in r.headers["content-type"]

    def test_orphaned_running_run_marked_error(self, client):
        """A run stuck in 'running' with no live queue should be served as error."""
        _seed_run("orphan-1", status="running")
        # No queue for this run — simulates a server restart mid-run
        body = client.get("/api/runs/orphan-1/stream").text
        assert "stream_end" in body
        assert _run_records["orphan-1"]["status"] == "error"


# ---------------------------------------------------------------------------
# Watchlists CRUD
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestWatchlists:
    def test_list_empty(self, client):
        assert client.get("/api/watchlists").json() == []

    def test_create_returns_id_and_uppercased_tickers(self, client):
        r = client.post("/api/watchlists", json={"name": "Tech", "tickers": ["aapl", "NVDA"]})
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["name"] == "Tech"
        assert set(data["tickers"]) == {"AAPL", "NVDA"}

    def test_create_persists(self, client):
        client.post("/api/watchlists", json={"name": "AI", "tickers": ["NVDA"]})
        assert len(client.get("/api/watchlists").json()) == 1

    def test_update_watchlist(self, client):
        wl_id = client.post("/api/watchlists", json={"name": "Old", "tickers": ["AAPL"]}).json()[
            "id"
        ]
        r = client.put(f"/api/watchlists/{wl_id}", json={"name": "New", "tickers": ["TSLA"]})
        assert r.status_code == 200
        assert r.json()["name"] == "New"
        assert r.json()["tickers"] == ["TSLA"]

    def test_update_missing_returns_404(self, client):
        r = client.put("/api/watchlists/bad-id", json={"name": "X", "tickers": []})
        assert r.status_code == 404

    def test_delete_watchlist(self, client):
        wl_id = client.post("/api/watchlists", json={"name": "Del", "tickers": []}).json()["id"]
        assert client.delete(f"/api/watchlists/{wl_id}").status_code == 200
        assert client.get("/api/watchlists").json() == []

    def test_delete_missing_returns_404(self, client):
        assert client.delete("/api/watchlists/no-such").status_code == 404

    def test_blank_tickers_stripped(self, client):
        r = client.post("/api/watchlists", json={"name": "Sparse", "tickers": ["AAPL", "  ", ""]})
        assert r.json()["tickers"] == ["AAPL"]


# ---------------------------------------------------------------------------
# Legacy /analyze endpoint (backward-compat)
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestLegacyAnalyze:
    def test_returns_ticker_and_date(self, client):
        mock_state = {}
        with patch("api.main.TradingAgentsGraph") as MockGraph:
            instance = MockGraph.return_value
            instance.propagate.return_value = (mock_state, "Buy")
            r = client.post("/analyze", json=_VALID_RUN)
        assert r.status_code == 200
        data = r.json()
        assert data["ticker"] == "AAPL"
        assert data["date"] == "2026-01-15"
        assert data["decision"] == "Buy"

    def test_path_traversal_ticker_rejected(self, client):
        r = client.post("/analyze", json={**_VALID_RUN, "ticker": "../../etc"})
        assert r.status_code == 422
