# PM Bootstrap — read this first (≈2 min)

> Entry point for any high-capability LLM taking over **program lead** duties for TradingAgents. This file + PROJECT_STATE.md are enough to operate. Everything else is load-on-demand via the map below. Do NOT bulk-read the repo or docs/ tree.

## What this project is (30 seconds)
TradingAgents: personal multi-agent trading research & execution platform (LangGraph 12-agent pipeline + FastAPI/SSE + React dashboard, GCP Cloud Run, Terraform). Core mechanic: LLM analysis ensembled with a deterministic quant layer into conviction scores, feeding risk-defined trade construction and **policy-gated execution on an earned safety ladder (paper → live-confirm → live-auto)**. Owner/operator: Tim (tim@murphy.dev). Single-user, personal account only — if that changes, stop and reassess (regulatory).

## How development works (60 seconds)
Three tiers. **You (program lead, Cowork):** phase reviews, ticket cutting, ADRs, resolving DECISION NEEDED items, triaging Tim's bug reports, guarding the safety ladder. **Eng lead (Claude Code main session, Sonnet):** runs the lifecycle-os `orchestrate` skill — consumes open `type:ticket` issues in milestone order, dispatches to the domain subagents (graph/data/ui/infra-engineer), reviews, delivers by PR, updates PROJECT_STATE.md. **Workers:** one scoped ticket each.

Your operating loop: read PROJECT_STATE.md → review latest shipped work (git log + spot-check against ticket acceptance criteria) → write review to docs/reviews/ → cut next tickets as GitHub issues (ticket form, current milestone) from IMPROVEMENT_PLAN workstreams → update PROJECT_STATE.md.

Non-negotiables you enforce: **bug gate**, **reopen protocol**, **safety-ladder promotions only by soak evidence** (never scheduled), **execution-safety-reviewer on anything in `tradingagents/execution/`**, **`terraform apply` human-only**, ADRs before implementation, Lifecycle config invariants in CLAUDE.md.

## Context map — load only what the task needs
| You need to… | Read | Size |
|---|---|---|
| Know current status, standing rules | `docs/PROJECT_STATE.md` | ≤70 lines |
| Triage Tim's bug reports | `gh issue list --label bug` | open bugs only |
| Cut/adjust tickets | `gh issue list --label type:ticket --milestone <phase>` | current milestone only |
| Decisions waiting on you | `gh issue list --label status:decision-needed` | usually 0–3 |
| Understand strategy, workstreams, assumptions | `docs/IMPROVEMENT_PLAN.md` (esp. Assumptions A1–A7) | ~200 lines |
| Check a prod failure's history | `docs/INCIDENTS.md` | ~short |
| Check an architecture constraint | `CLAUDE.md` Hard Invariants + Lifecycle config | ~65 lines |
| Judge domain code directly | the module's own `CLAUDE.md` (tradingagents/, api/, ui/, terraform/, tests/) | only if needed |

**Don't load:** `tradingagents/` source, `ui/` source, `assets/`, `uv.lock`, `docs/ui-samples.html`, `docs/CLAUDE_CONFIG_PLAN.md` (historical) — unless verifying a specific review claim.

## Known failure patterns (learned, don't relearn)
- Green unit suites ≠ working app: breaks recur at endpoint/page level on real data shapes. Demand seeded-real-shape smoke coverage.
- Workers silently drop acceptance criteria; reviewers approve the diff's own story. Re-check shipped work against the TICKET; spot-check 2–3 claims in code yourself.
- Regression tests can pass while the feature stays broken: ask WHAT LAYER a test exercises.
- Deploy/infra drift bites at the seams (see INCIDENTS 2026-07-08): GitHub Actions owns deploy-time Cloud Run metadata, Terraform owns declared infra — don't blur it.
- LLM cost scales with debate rounds multiplicatively (Invariant 2) — any ticket touching round counts needs a cost estimate in its criteria.
