# TradingAgents — Claude Code Guide

Multi-agent LLM trading framework: LangGraph pipeline + FastAPI/SSE backend + React dashboard, deployed on GCP Cloud Run.

## Commands

Use `make`. Hooks, CI and agents call these exact targets — never invent an equivalent.

| Target | Does |
|---|---|
| `make install` | `uv sync` (api + dev extras) and `npm ci` in `ui/` |
| `make dev` | full stack at http://localhost:8080 (`docker compose up api`) |
| `make test` | full suite — unit + smoke + regression, same container as CI |
| `make test-quick` | unit + smoke, no Docker; the commit hook runs it |
| `make verify` | everything CI gates on: ruff, bandit HIGH, tests, UI build |
| `make preview` | `terraform plan` (apply is human-only) |

Also: `tradingagents` (interactive CLI, or `python -m cli.main`) · `uvicorn api.main:app --reload --port 8080` + `cd ui && npm run dev` for hot-reload dev.

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

## Lifecycle config (read by lifecycle-os skills and hooks — keep the field names exact)

`lifecycle: v1.0.0-rc.3`

- **Delivery:** pr
- **Merge:** auto-when-green
- **Tracker:** github:tmurphy86/TradingAgents
- **Cloud:** gcp
- **Invariants:** Hard Invariants 1–5 above; safety ladder stages (paper → live-confirm → live-auto) are promoted only by soak evidence, never by schedule or code change; `terraform apply` is human-only; `max_instance_count = 1` stays under Terraform control; defined-risk options strategies only.
- **Protected paths:** `tradingagents/execution/**`, `terraform/**`, `.github/workflows/**` — security-reviewer + owner merge (a merge to `main` deploys, and `terraform.yml` applies on push)
- **Escalate to program lead (never decide):** any safety-ladder stage change; anything under `tradingagents/execution/`; broker adapter choice; persistence layout changes under `~/.tradingagents/`; new dependencies; revisions to IMPROVEMENT_PLAN assumptions A1–A7.
- **Default worker:** the domain subagent named in the ticket (graph/data/ui/infra-engineer); lifecycle-os `coder`/`senior-coder` only for work outside those domains. `reviewer` runs on every diff regardless of who wrote it; `execution-safety-reviewer` additionally on anything touching execution.
- **Doc mapping:** strategy & phasing → `docs/IMPROVEMENT_PLAN.md` (SPEC-analog); dispatchable tickets → GitHub issues labelled `type:ticket` (phases = milestones); owner bug inbox → issues labelled `bug`; prod postmortems stay in `docs/INCIDENTS.md` (via `incident` skill); sync state → `docs/PROJECT_STATE.md`; program-lead entry → `docs/BOOTSTRAP.md`.
- **Lint/format:** `ruff` (backend, via `make verify`); `ui/` has no lint script yet — `npm run build` (tsc) is the only frontend gate.
