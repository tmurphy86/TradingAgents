# ui/ — Web Dashboard

React + Vite + Tailwind. Dev: `npm run dev` (proxies `/api` → `http://localhost:8080`). Prod/Docker: FastAPI serves `ui/dist/` at `/`.

## Pages

- `/new` — configure and launch a run (ticker, date, provider, models, debate rounds)
- `/runs/:runId` — live SSE view of all 12 agent steps; color-coded decision banner
- `/history` — past runs with BUY/HOLD/SELL badges; delete
- `/watchlists` — named ticker lists; one-click launch to `/new?ticker=...`

## Key files

- `src/api.ts` — fetch-based API client; `streamRun(id)` returns `new EventSource(...)`
- `src/pages/RunPage.tsx` — SSE consumer; `PIPELINE` constant maps 12 state fields to display labels
- `src/types.ts` — `RunRequest`, `RunRecord`, `RunResult`, `Watchlist`, `AgentEntry`

## Rules

- **No new state-management library** — React state has been sufficient; demonstrate the pain first.
- Keep `types.ts` in sync with API response shapes; SSE schema changes land with the backend PR.
- New SSE event types must be handled (or explicitly ignored) in `RunPage.tsx` — unknown events must not break the stream.
