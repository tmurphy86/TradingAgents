# api/ — FastAPI Backend

## Endpoints (`main.py`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/runs` | Start a run; returns `{"run_id": "..."}` |
| `GET` | `/api/runs` | List all run records |
| `GET` | `/api/runs/{id}` | Get a single run record |
| `DELETE` | `/api/runs/{id}` | Delete a run record (cancels it first if still running) |
| `POST` | `/api/runs/{id}/cancel` | Cancel a running run — cooperative; 200 running, 409 finished, 404 unknown |
| `GET` | `/api/runs/{id}/stream` | SSE stream; replays stored events then goes live |
| `GET/POST/PUT/DELETE` | `/api/watchlists[/{id}]` | Watchlist CRUD |
| `GET` | `/health` | Health check |

Run records: `~/.tradingagents/runs/<id>.json` · Watchlists: `~/.tradingagents/watchlists.json`

## SSE / Streaming

- Event types: `agent_update` · `run_complete` · `run_error` · `run_cancelled` · `stream_end`
- `propagate(..., event_callback=fn)` switches `_run_graph()` to `graph.stream()`; `_emit_state_events()` diffs snapshots against `_WATCHED_FIELDS` / `_DEBATE_FIELDS` (see `tradingagents/graph/trading_graph.py`).
- **Thread bridge rule:** events cross from the sync background thread to the async loop via `loop.call_soon_threadsafe(q.put_nowait, event)`. Never call `asyncio.Queue` methods directly from a non-async thread.
- **Cancellation:** each live run has a `threading.Event` in `_run_cancels`, passed as `propagate(cancel_event=...)` and checked between graph steps (the node in flight finishes; the next never starts). The worker persists `status: "cancelled"` and emits `run_cancelled`. `_runs_lock` serialises the worker's terminal write against `DELETE` so a deleted run is never recreated.
- Orphaned run records are healed on startup: the lifespan startup handler marks any record stuck in `running` as `error` (cancelled records are left alone).
- Changing the SSE event schema? Update `ui/src/api.ts` + `RunPage.tsx` in the same PR, and add a `regression` test.
