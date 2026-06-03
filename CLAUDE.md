# TradingAgents — Claude Code Guide

## Commands

```bash
# Install (editable dev install)
pip install -e .
pip install -e ".[api]"          # also installs fastapi + uvicorn for the API layer

# Interactive CLI
tradingagents
python -m cli.main               # alternative

# Run tests  (markers: unit | integration | smoke)
python -m pytest tests/ -m "unit or smoke" -q
python -m pytest tests/ -m integration -q   # requires live API keys

# API server (local)
uvicorn api.main:app --reload --port 8080

# Docker (interactive CLI)
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
```

**Execution order:** Market Analyst → Sentiment Analyst → News Analyst → Fundamentals Analyst → Bull ↔ Bear debate (N rounds) → Research Manager → Trader → Aggressive ↔ Conservative ↔ Neutral debate (N rounds) → Portfolio Manager → `final_trade_decision`

**Two LLM tiers:** `deep_think_llm` (Research Manager, Portfolio Manager) and `quick_think_llm` (all analysts and researchers). Both are set in `DEFAULT_CONFIG` and overridable per-call.

## Key Patterns

### Adding an analyst
1. Create `tradingagents/agents/analysts/my_analyst.py` — return a string report, tool-calling or pre-loaded.
2. Register the node in `tradingagents/graph/setup.py` (add to the node chain and conditional routing).
3. Add the report field to `AgentState` in `tradingagents/agents/utils/agent_states.py`.
4. Update `tradingagents/graph/conditional_logic.py` if the analyst uses tool-calling (add a `should_continue_*` function).

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

On GCP (Cloud Run), `~/.tradingagents/` is a GCS FUSE volume mount — no code changes needed.

## Testing

| Marker | What it covers | Needs API keys |
| --- | --- | --- |
| `unit` | Isolated logic, no external calls | No |
| `smoke` | Quick sanity checks | No |
| `integration` | Live LLM / data provider calls | Yes |

Fixtures live in `tests/conftest.py`. Tests cover: analyst execution planning, LLM providers, env-var overrides, checkpoint/resume, memory log, model catalog, crypto asset mode, ticker path-traversal security.

## GCP Deployment

**Infrastructure:** `terraform/` — one `terraform apply` provisions Cloud Run, GCS bucket (mounted as `~/.tradingagents`), Secret Manager, Artifact Registry, and a Cloud Build trigger.

**CI/CD:** `cloudbuild.yaml` — push to `main` → run unit/smoke tests → build `api/Dockerfile` → push to Artifact Registry → `gcloud run deploy`.

**API surface:** `api/main.py` — `POST /analyze` accepts ticker + date + provider/model overrides, calls `TradingAgentsGraph.propagate()` in a thread, returns the `PortfolioDecision`. Invocations are IAM-authenticated (no public access).

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
