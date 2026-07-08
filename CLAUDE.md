# TradingAgents — Claude Code Guide

Multi-agent LLM trading framework: LangGraph pipeline + FastAPI/SSE backend + React dashboard, deployed on GCP Cloud Run.

## Commands

```bash
uv sync --extra api                          # install (dev, incl. FastAPI)
tradingagents                                # interactive CLI (or: python -m cli.main)
docker compose up api                        # full stack at http://localhost:8080
uvicorn api.main:app --reload --port 8080    # dev backend (+ `cd ui && npm run dev` for frontend)
docker compose run --rm test                 # test suite (unit + smoke + regression, same container as CI)
python -m pytest tests/ -m "unit or smoke" -q  # quick local tests, no Docker
cd terraform && terraform plan               # infra preview (apply is human-only)
```

## Architecture

**Execution order:** Market → Sentiment → News → Fundamentals analysts → Bull ↔ Bear debate → Research Manager → Trader → Aggressive ↔ Conservative ↔ Neutral debate → Portfolio Manager → `final_trade_decision`

**Two LLM tiers:** `deep_think_llm` (Research + Portfolio Manager) and `quick_think_llm` (everyone else), set in `tradingagents/default_config.py`.

**Persistence:** everything under `~/.tradingagents/` (GCS FUSE mount on Cloud Run): `memory/trading_memory.md` (decision log), `cache/checkpoints/<TICKER>.db`, `logs/<TICKER>/`, `runs/<id>.json`, `watchlists.json`. Override via `TRADINGAGENTS_*_DIR` env vars.

## Hard Invariants (cross-cutting — never violate)

1. `create_msg_delete()` clears messages between phases — intentional, keep it.
2. Debate rounds multiply: `max_debate_rounds=1` → 2 LLM calls (Bull+Bear); risk debate → 3.
3. Structured output only through `tradingagents/agents/utils/structured.py` — never raw `response_format`/`tool_choice`.
4. Ticker sanitization (`dataflows/utils.py`) guards every file path built from a ticker.
5. Check `llm_clients/capabilities.py` flags before passing `reasoning_effort`/`thinking` kwargs.

## Where the detail lives

- Pipeline / agents / LLM clients → `tradingagents/CLAUDE.md`
- Data vendors → `tradingagents/dataflows/CLAUDE.md`
- API + SSE streaming → `api/CLAUDE.md`
- Frontend → `ui/CLAUDE.md`
- Infra / CI/CD / GCP → `terraform/CLAUDE.md`
- Tests → `tests/CLAUDE.md`
- Strategy & workstreams → `docs/IMPROVEMENT_PLAN.md` · Claude config → `docs/CLAUDE_CONFIG_PLAN.md`

## Procedures (skills)

Use the project skills instead of improvising: `add-analyst`, `add-llm-provider`, `release`, `incident`.

## Delegation

Prefer scoped subagents (`.claude/agents/`): **graph-engineer** (pipeline/schemas/LLM clients), **data-engineer** (dataflows only), **ui-engineer** (ui only), **infra-engineer** (terraform/workflows, plan-only), **test-runner** (runs suites, read-only), **release-manager**. Once `tradingagents/execution/` exists, any change there requires an **execution-safety-reviewer** pass before merge.
