# TradingAgents — Claude Code Guide

## Commands

```bash
# Install (editable dev install — uv.lock ensures reproducibility)
uv sync                          # base deps
uv sync --extra api              # also installs fastapi + uvicorn for the API layer

# Interactive CLI
tradingagents
python -m cli.main               # alternative

# Run tests  (markers: unit | integration | smoke)
python -m pytest tests/ -m "unit or smoke" -q
python -m pytest tests/ -m integration -q   # requires live API keys

# API server + web dashboard (local, two-terminal dev setup)
uvicorn api.main:app --reload --port 8080   # terminal 1: FastAPI backend
cd ui && npm run dev                         # terminal 2: Vite dev server (proxies /api → :8080)

# Full stack via Docker Compose (single command, recommended for local validation)
docker compose up api            # builds UI + backend, serves both at http://localhost:8080

# Run the test suite (same container used in CI)
docker compose run --rm test                                     # unit + smoke + regression
docker compose run --rm test pytest tests/ -m regression -v      # regression only
docker compose run --rm test pytest tests/ -m integration -v     # integration (needs real API keys)

# Docker (interactive CLI only)
docker compose run --rm tradingagents

# Terraform (GCP infra)
cd terraform && terraform init && terraform apply
```

## Architecture in One Page

```
tradingagents/graph/trading_graph.py   ← TradingAgentsGraph  (entry point)
tradingagents/graph/setup.py           ← builds the LangGraph StateGraph
tradingagents/graph/conditional_logic.py ← all routing decisions
tradingagents/agents/utils/agent_states.py ← AgentState (TypedDict, the full graph state)
tradingagents/agents/schemas.py        ← Pydantic output models (ResearchPlan, TraderProposal, PortfolioDecision)
tradingagents/default_config.py        ← DEFAULT_CONFIG + TRADINGAGENTS_* env-var overrides
tradingagents/llm_clients/factory.py   ← create_llm_client() dispatch to all providers
tradingagents/dataflows/interface.py   ← data vendor routing (yfinance / alpha_vantage)
api/main.py                            ← FastAPI: run management, SSE streaming, watchlist CRUD
ui/src/                                ← React + Vite + Tailwind frontend (ui/dist/ in prod)
```

**Execution order:** Market Analyst → Sentiment Analyst → News Analyst → Fundamentals Analyst → Bull ↔ Bear debate (N rounds) → Research Manager → Trader → Aggressive ↔ Conservative ↔ Neutral debate (N rounds) → Portfolio Manager → `final_trade_decision`

**Two LLM tiers:** `deep_think_llm` (Research Manager, Portfolio Manager) and `quick_think_llm` (all analysts and researchers). Both are set in `DEFAULT_CONFIG` and overridable per-call.

## Web Dashboard (`ui/`)

React + Vite + Tailwind frontend. In dev, Vite proxies `/api` → `http://localhost:8080`. In production/Docker, FastAPI mounts `ui/dist/` as static files at `/`.

**Pages:**
- `/new` — configure and launch a run (ticker, date, provider, models, debate rounds)
- `/runs/:runId` — live SSE view of all 12 agent steps; color-coded final decision banner
- `/history` — table of past runs with BUY/HOLD/SELL badges; delete
- `/watchlists` — named ticker lists; one-click launch to `/new?ticker=...`

**Key files:**
- `ui/src/api.ts` — fetch-based API client; `streamRun(id)` returns `new EventSource(...)`
- `ui/src/pages/RunPage.tsx` — SSE consumer; `PIPELINE` constant maps 12 state fields to display labels
- `ui/src/types.ts` — `RunRequest`, `RunRecord`, `RunResult`, `Watchlist`, `AgentEntry` interfaces

## API Surface (`api/main.py`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/runs` | Start a run; returns `{"run_id": "..."}` |
| `GET` | `/api/runs` | List all run records |
| `GET` | `/api/runs/{id}` | Get a single run record |
| `DELETE` | `/api/runs/{id}` | Delete a run record |
| `GET` | `/api/runs/{id}/stream` | SSE stream; replays stored events then goes live |
| `GET` | `/api/watchlists` | List watchlists |
| `POST` | `/api/watchlists` | Create watchlist |
| `PUT` | `/api/watchlists/{id}` | Update watchlist |
| `DELETE` | `/api/watchlists/{id}` | Delete watchlist |
| `POST` | `/analyze` | Legacy synchronous analysis (backward-compat) |
| `GET` | `/health` | Health check |

Run records persist to `~/.tradingagents/runs/<id>.json`; watchlists to `~/.tradingagents/watchlists.json`.

**SSE event types:** `agent_update` · `complete` · `error` · `stream_end`

## Real-Time Streaming

`propagate()` accepts `event_callback`:

```python
ta.propagate("NVDA", "2026-01-15", event_callback=my_fn)
```

When provided, `_run_graph()` uses `graph.stream()` instead of `graph.invoke()`, diffs consecutive state snapshots, and calls `event_callback({"type": "agent_update", "agent": ..., "content": ...})` for each new agent output. The diff logic in `_emit_state_events()` watches `_WATCHED_FIELDS` (main reports) and `_DEBATE_FIELDS` (debate history sub-fields).

Events bridge from the sync background thread to the async FastAPI loop via `loop.call_soon_threadsafe(q.put_nowait, event)`. Do not call `asyncio.Queue` from a non-async thread directly.

## Key Patterns

### Adding an analyst
1. Create `tradingagents/agents/analysts/my_analyst.py` — return a string report, tool-calling or pre-loaded.
2. Register the node in `tradingagents/graph/setup.py` (add to the node chain and conditional routing).
3. Add the report field to `AgentState` in `tradingagents/agents/utils/agent_states.py`.
4. Update `tradingagents/graph/conditional_logic.py` if the analyst uses tool-calling (add a `should_continue_*` function).
5. Add the field to `_WATCHED_FIELDS` in `trading_graph.py` so the dashboard streams it live.

### Adding an LLM provider
1. Subclass `BaseLLMClient` in `tradingagents/llm_clients/`.
2. Add to `factory.py` dispatch.
3. Add model list to `model_catalog.py`.
4. Add capability flags to `capabilities.py` (structured output mode, reasoning effort support).
5. Add API key env var to `api_key_env.py`.

### Structured output (managers only)
`tradingagents/agents/utils/structured.py` handles the provider-specific binding. Pass a Pydantic model class; the helper binds it correctly for each provider's structured-output mechanism.

### Config overrides
`DEFAULT_CONFIG` in `default_config.py` is the single source of truth. All `TRADINGAGENTS_*` env vars are declared in `_ENV_OVERRIDES` with type coercion. Programmatic overrides (passing a modified config dict to `TradingAgentsGraph`) take highest precedence.

### Persistence paths
All runtime state writes to `~/.tradingagents/` (or `TRADINGAGENTS_*_DIR` env var overrides):
- `memory/trading_memory.md` — append-only decision log
- `cache/checkpoints/<TICKER>.db` — SQLite checkpoint per ticker
- `logs/<TICKER>/TradingAgentsStrategy_logs/` — full state JSON per run
- `runs/<id>.json` — web dashboard run records
- `watchlists.json` — web dashboard watchlists

On GCP (Cloud Run), `~/.tradingagents/` is a GCS FUSE volume mount — no code changes needed.

## Testing

All tests run in a dedicated Docker container built from the `test` stage of `api/Dockerfile`. This guarantees the same Python version, OS, and dependencies in local dev and GitHub Actions CI.

```bash
docker compose run --rm test                         # default: unit + smoke + regression
docker compose run --rm test pytest tests/ -v        # verbose, all non-integration
```

| Marker | What it covers | Needs API keys |
| --- | --- | --- |
| `unit` | Isolated logic, no external calls | No |
| `smoke` | Quick sanity checks | No |
| `regression` | FastAPI endpoint shape, SSE streaming, watchlist CRUD — all mocked | No |
| `integration` | Live LLM / data provider calls | Yes |

**Test container build target:** `api/Dockerfile` stage `test` — extends `py-builder`, installs `.[api,dev]` (adds `httpx`, `ruff`, `bandit`), sets `PYTHONPATH=/build`.

**`tests/conftest.py`** injects placeholder values for all API key env vars so unit/smoke/regression tests never fail on missing secrets.

Fixtures live in `tests/conftest.py`. Tests cover: analyst execution planning, LLM providers, env-var overrides, checkpoint/resume, memory log, model catalog, crypto asset mode, ticker path-traversal security, API endpoints, SSE streaming, watchlist CRUD.

## CI / CD

```
PR opened → GitHub Actions (ci.yml)
  ├── build test container (cached via GHA layer cache)
  ├── lint          ruff check + format --check
  ├── security      bandit -r tradingagents/ api/
  ├── test          docker run tradingagents-test (unit + smoke + regression)
  ├── ui-build      npm ci + npm run build
  └── code-review   Claude claude-sonnet-4-6 reviews the diff, posts PR comment (non-blocking)

Merge to main → GitHub Actions (deploy.yml)
  ├── test          same test container (gate before push)
  ├── build         build production image (api/Dockerfile default target)
  ├── push          push to Artifact Registry
  └── deploy        gcloud run deploy (via Workload Identity Federation)

terraform/ changes → GitHub Actions (terraform.yml)
  ├── PR:   terraform plan, posts plan as PR comment
  └── main: terraform apply
```

## Required GitHub Actions Variables

Set these in **Settings → Secrets and variables → Actions** before CI/CD will work:

| Variable | Workflow | Description |
|---|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | deploy, terraform | WIF provider (from `terraform output workload_identity_provider`) |
| `GCP_DEPLOY_SA` | deploy | Deploy SA email (from `terraform output github_deploy_sa`) |
| `GCP_REGION` | deploy | GCP region (e.g. `us-central1`) |
| `GCP_IMAGE_REPO` | deploy | Artifact Registry path |
| `GCP_CLOUD_RUN_SERVICE` | deploy | Cloud Run service name |
| `GCP_TERRAFORM_SA` | terraform | Terraform SA email (from `terraform output github_terraform_sa`) |
| `GCP_TF_STATE_BUCKET` | terraform | GCS bucket for Terraform state |
| `TF_VAR_PROJECT_ID` | terraform | GCP project ID |
| `TF_VAR_REGION` | terraform | GCP region |
| `TF_VAR_INVOKER_EMAIL` | terraform | Cloud Run invoker IAM email |
| `TF_VAR_ACTIVE_SECRETS` | terraform | Comma-separated secret names to mount |
| `ANTHROPIC_API_KEY` | ci (code review) | Required for AI code review job (non-blocking if missing) |

Run `terraform apply` once first — the three `workload_identity_*` outputs give you the WIF values for deploy and terraform workflows.

## GCP Deployment

**Infrastructure:** `terraform/` — one `terraform apply` provisions Cloud Run, GCS bucket (mounted as `~/.tradingagents`), Secret Manager, Artifact Registry, and Workload Identity Federation for GitHub Actions.

**CI/CD:** `.github/workflows/deploy.yml` — push to `main` → run unit/smoke tests → build `api/Dockerfile` → push to Artifact Registry → `gcloud run deploy` (authenticated via WIF; no long-lived service account keys). `cloudbuild.yaml` is deprecated.

**Docker image:** `api/Dockerfile` is a 3-stage build — Node 20 builds the React UI, `ghcr.io/astral-sh/uv` installs Python deps into a venv, slim runtime copies both. One container serves the full stack.

**API surface:** `api/main.py` — full run management, SSE streaming, watchlists, and legacy `/analyze`. IAM-authenticated (no public access).

**Secrets workflow:** Create stubs with `terraform apply`, then populate values:
```bash
echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```
Add the name to `active_secrets` in `terraform.tfvars`, re-apply.

## Things to Know

- **Messages are cleared between phases.** `create_msg_delete()` wipes `AgentState.messages` after each analyst completes. This is intentional — avoids context bloat. Do not remove it when adding agents.
- **Debate counts are doubled/tripled.** Investment debate alternates Bull → Bear, so `max_debate_rounds=1` means 2 total calls (1 Bull + 1 Bear). Risk debate cycles three agents, so `max_risk_discuss_rounds=1` means 3 total calls.
- **Crypto mode skips fundamentals.** When `asset_type="crypto"`, the fundamentals analyst is excluded from the execution plan automatically. Check `analyst_execution.py` if adding crypto-aware agents.
- **Ticker validation blocks path traversal.** `dataflows/utils.py` sanitises tickers before they are used in file paths. Keep this validation in place when adding new storage writes.
- **Structured output varies by provider.** Never assume `response_format` or `tool_choice` — always go through `structured.py` so the provider capability matrix is respected.
- **`deep_think_llm` supports extended thinking/reasoning on some providers.** The capability flags in `capabilities.py` control whether `reasoning_effort` / `thinking` kwargs are passed. Check these flags before adding new model calls.
- **Orphaned run records are healed on startup.** The FastAPI lifespan handler reads all `~/.tradingagents/runs/*.json` files and marks any record stuck in `running` status as `error`. This handles server restarts mid-analysis.
