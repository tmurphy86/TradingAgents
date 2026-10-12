# ui/ — Web Dashboard

React + Vite + Tailwind. Dev: `npm run dev` (proxies `/api` → `http://localhost:8080`). Prod/Docker: FastAPI serves `ui/dist/` at `/`.

## Pages

- `/new` — configure and launch a run (ticker, date, provider, models, debate rounds)
- `/runs/:runId` — live SSE view of all 12 agent steps; color-coded decision banner; Cancel button while `running`
- `/history` — past runs with BUY/HOLD/SELL badges and a status badge (`running` / `complete` / `error` / `cancelled`); delete
- `/watchlists` — named ticker lists; one-click launch to `/new?ticker=...`

## Key files

- `src/api.ts` — fetch-based API client; `streamRun(id)` returns `new EventSource(...)`; non-2xx responses throw `ApiError` (carries `.status`); `cancelRun(id)` → `POST /api/runs/{id}/cancel`
- `src/pages/RunPage.tsx` — SSE consumer; `PIPELINE` constant maps 12 state fields to display labels. Handles `agent_update`, `run_complete`, `run_error`, `run_cancelled`, `stream_end`; anything else is ignored
- `src/types.ts` — `RunRequest`, `RunRecord`, `RunStatus`, `RunResult`, `Watchlist`, `AgentEntry`

## Cancelling a run

Cancellation is cooperative: `cancelRun` returning 200 only means the request was accepted, and the run stays `running` until the agent in flight finishes. The button therefore stays disabled ("Cancelling…") until the `run_cancelled` event sets the status to `cancelled` — never flip the status on the POST response. A 409 means the run finished first: re-fetch the record and show its real status rather than an error. `cancelled` is a terminal status of its own (neutral badge, no error banner).

## Rules

- **No new state-management library** — React state has been sufficient; demonstrate the pain first.
- Keep `types.ts` in sync with API response shapes; SSE schema changes land with the backend PR.
- New SSE event types must be handled (or explicitly ignored) in `RunPage.tsx` — unknown events must not break the stream.
