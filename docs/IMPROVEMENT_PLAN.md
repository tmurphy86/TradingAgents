# TradingAgents — Improvement Plan & Delegation Playbook

Lead-orchestrator analysis of the current app, broken into parallel workstreams for specialized agents. Date: 2026-07-07.

---

## 1. Explicit Assumptions (inputs not provided)

| # | Assumption | Impact if wrong |
|---|---|---|
| A1 | Primary user is Tim (single developer/operator); dashboard is IAM-gated on Cloud Run with no other users yet. | Multi-user auth moves from "don't build yet" to Phase 1. |
| A2 | Business goal is decision-support quality and personal research, not monetization. | Would add billing, tenancy, SLA workstreams. |
| A3 | No hard latency SLO; runs taking minutes is acceptable, but LLM cost matters. | Would reprioritize parallelization above cost tracking. |
| A4 | ~~The app informs trades; it does not execute them.~~ **Revised (owner direction, 2026-07-07):** execution is in scope, gated by thresholds and a staged safety ladder (paper → confirm → auto). Personal account only, not a service for others. | If this becomes multi-user, regulatory obligations (RIA/broker-dealer rules) change everything — stop and reassess. |
| A6 | Broker: Alpaca assumed for execution (paper-trading API, equities + options). Verify current options approval levels and API support before Agent H starts. | Swap adapter (IBKR, Tradier); adapter interface isolates the choice. |
| A7 | Options scope starts with defined-risk strategies only (covered calls, cash-secured puts, verticals). No naked short options. | Undefined-risk strategies require margin modeling the platform doesn't have. |
| A5 | Capacity ≈ one developer + coding agents; roadmap sized for ~6–8 weeks of part-time effort. | Phases compress/stretch accordingly. |

## 2. Current-State Assessment

**Strengths (verified in repo):** 12-agent LangGraph pipeline with clear separation (`graph/`, `agents/`, `llm_clients/`, `dataflows/`); 5 LLM providers behind a factory with capability flags; full-stack web dashboard with SSE streaming; 270 tests across unit/smoke/regression/integration markers; containerized CI/CD (GitHub Actions → Artifact Registry → Cloud Run via WIF); Terraform-managed infra; a reflection loop (`Reflector` + `TradingMemoryLog`) that already scores past decisions against realized returns.

**Gaps:**

1. **Trust is unmeasured.** The core product question — "are these BUY/HOLD/SELL calls any good?" — has no answer. Reflection data exists in `memory/trading_memory.md` but is never aggregated or shown in the UI. No backtest harness.
2. **Cost is invisible.** A run makes ~14+ LLM calls across two model tiers; no per-run token/cost accounting anywhere.
3. **Runs can't be cancelled.** `api/main.py` has no stop endpoint; a bad run burns money until it finishes. Orphan healing only runs at startup.
4. **Sequential analyst execution.** The four analysts have no data dependencies on each other but run serially — roughly 4× the wall-clock needed for that phase.
5. **UI is thin on insight.** No run comparison, no reflection/accuracy view, no cost display, no batch launch from a watchlist. Zero frontend tests (9 TS files, no test runner in `ui/`).
6. **Hygiene debt.** Deprecated `create_social_media_analyst` alias; `llm_clients/TODO.md` item #1 (`validate_model()` never called) still open; root-level `main.py`/`test.py`/`overview.md` of unclear status; `requirements.txt` coexists with `pyproject.toml` + `uv.lock`; legacy `/analyze` endpoint duplicates `/api/runs`.
7. **Data layer fragility.** yfinance/alpha_vantage calls lack a shared cache/rate-limit/retry layer; a vendor hiccup mid-run fails silently into a weak report rather than failing loudly.

## 3. Workstreams (one per specialized agent)

Priority scale: P0 = do first, P1 = next, P2 = opportunistic.

### Agent A — Evaluation & Trust (P0, foundational)
- **Mission:** Make decision quality measurable. This is the highest-impact work: every other feature is decoration if the signals can't be trusted.
- **Scope:** `tradingagents/graph/reflection.py`, `agents/utils/memory.py`, new `eval/` module, API + UI read paths.
- **Tasks:** (1) Aggregate `TradingMemoryLog` entries into per-ticker and overall accuracy metrics (hit rate, avg return per signal class, vs buy-and-hold baseline). (2) Add `GET /api/metrics` endpoint. (3) Build a historical backtest harness: run the pipeline on past dates with data snapshots, score against known outcomes. (4) Surface an "Accuracy" page in the UI.
- **Deliverables:** `eval/backtest.py`, metrics endpoint, UI accuracy page, baseline report on ≥20 historical runs.
- **Dependencies:** None to start; UI page lands after Agent C's component groundwork (soft).
- **Risk:** Look-ahead bias in backtests — data snapshots must be point-in-time. Flag any vendor field that can't be time-scoped.

### Agent B — Cost, Control & Performance (P0)
- **Mission:** Every run reports what it cost; every run can be stopped; the analyst phase runs in parallel.
- **Scope:** `trading_graph.py`, `llm_clients/base_client.py` + subclasses, `graph/setup.py`, `api/main.py`, run records.
- **Tasks:** (1) Token/cost capture in `BaseLLMClient` per call, aggregated into the run record and a new `cost_update` SSE event. (2) `POST /api/runs/{id}/cancel` with cooperative cancellation checked between graph nodes. (3) Parallelize the four analysts via LangGraph fan-out/fan-in — preserving `create_msg_delete()` semantics and `_emit_state_events()` diffing. (4) Per-provider pricing table in `model_catalog.py`.
- **Deliverables:** Cost visible in UI per run; working cancel button; analyst phase wall-clock ↓ ≥50%.
- **Dependencies:** None. Coordinate SSE event additions with Agent C.
- **Risk:** Fan-out interacts with message clearing and state diffing — regression tests required before merge (`docker compose run --rm test`).

### Agent C — Dashboard UX (P1)
- **Mission:** Turn the dashboard from a run viewer into a decision workspace.
- **Scope:** `ui/src/`, `api/main.py` read endpoints only.
- **Tasks:** (1) Run comparison view (two runs side-by-side, same ticker over time). (2) Render cost + duration per agent step on `RunPage`. (3) Watchlist batch launch ("run all") with a queue indicator. (4) Add Vitest + tests for `api.ts`, SSE handling, and `PIPELINE` mapping; wire into `ci.yml` next to `ui-build`. (5) Empty/error/loading states audit.
- **Deliverables:** Comparison page, cost display, batch launch, ≥70% coverage on `ui/src/api.ts` and stream logic.
- **Dependencies:** Cost display blocked by Agent B task 1; accuracy page consumes Agent A's endpoint.
- **Risk:** Low. Keep the UI single-purpose; no state library unless pain is demonstrated.

### Agent D — Platform Hygiene & Simplification (P0 quick wins, small)
- **Mission:** Delete and consolidate before anyone adds. Smallest workstream, first to finish.
- **Scope:** repo-wide, no feature changes.
- **Tasks:** (1) Remove deprecated `create_social_media_analyst` alias + `social_media_analyst.py` (major-version note in CHANGELOG). (2) Close `llm_clients/TODO.md` #1: call `validate_model()` in the factory with a warning. (3) Remove legacy `POST /analyze` after confirming nothing calls it (grep CI, scripts, README). (4) Audit root `main.py`, `test.py`, `overview.md`, `requirements.txt` — delete or fold into `pyproject.toml`/docs. (5) Delete `cloudbuild.yaml` remnants and stale references.
- **Deliverables:** One removal PR + CHANGELOG entries; net-negative line count.
- **Dependencies:** None. Merges first to reduce conflict surface for A–C.
- **Risk:** Minimal; regression suite is the gate.

### Agent E — Data Layer Resilience (P1)
- **Mission:** Analyst reports never silently degrade; vendor calls are cached, retried, and rate-limited.
- **Scope:** `tradingagents/dataflows/` only.
- **Tasks:** (1) Shared fetch wrapper: retry with backoff, rate-limit awareness (alpha_vantage free tier), on-disk cache keyed by (vendor, ticker, date, endpoint). (2) Data-quality gate: if a required feed returns empty/stale data, mark the run degraded and emit a warning event rather than proceeding silently. (3) Point-in-time snapshot mode to support Agent A's backtests. (4) Keep ticker path-traversal validation intact on all new writes.
- **Deliverables:** `dataflows/fetch.py` wrapper adopted by all vendor modules; degraded-run flag in run records and UI badge.
- **Dependencies:** Task 3 blocks Agent A's backtest harness — sequence it first.
- **Risk:** Cache invalidation for intraday data; scope cache to daily-granularity endpoints initially.

### Agent F — Automation (P2, defer until A/B land)
- **Mission:** Scheduled watchlist runs with digest notifications — only valuable once accuracy and cost are visible.
- **Scope:** new `api` scheduler (Cloud Scheduler → Cloud Run endpoint), notification adapter.
- **Tasks:** (1) `POST /api/watchlists/{id}/run-all` (shared with Agent C task 3). (2) Cloud Scheduler Terraform module hitting it on cron. (3) Daily digest (email or Slack webhook) summarizing decisions + cost. 
- **Deliverables:** Terraform-managed schedule; digest with per-run links.
- **Dependencies:** Agents A (metrics in digest), B (cost caps — refuse scheduled run if projected cost exceeds budget), C (batch endpoint).
- **Risk:** Unattended spend. Hard budget guard is a merge requirement, not a nice-to-have.

### Agent G — Signal Enhancement & Trade Construction (P1, starts after Phase 1)
- **Mission:** Upgrade output from a single BUY/HOLD/SELL rating to a ranked set of concrete, risk-defined trades — equities and options — each with value, entry, exits, and sizing.
- **Scope:** `agents/schemas.py`, trader/portfolio-manager prompts, new `tradingagents/quant/` module, `dataflows/` options feeds (with Agent E), UI trade cards.
- **Tasks:**
  1. **Quant signal layer (alternative methodology):** deterministic scores computed from data, not LLM opinion — momentum/trend (extend existing `stockstats_utils.py`), mean-reversion, realized + implied volatility, simple valuation ratios. Feed scores into analyst context *and* keep them as an independent column for ensembling and backtesting.
  2. **Ensemble decision:** combine LLM debate verdict with the quant score into a conviction score (0–100). Disagreement between the two is itself a signal — surface it, don't average it away.
  3. **Multi-trade output:** extend `TraderProposal` → `TradeIdea[]`: instrument (equity/option), direction, thesis, entry zone, stop, targets (scale-out levels), position size (risk-based: % of capital at risk per trade), risk/reward ratio, time horizon, invalidation condition, conviction.
  4. **Options strategy selection:** map directional view × volatility view → defined-risk strategy (bullish+high IV → CSP or bull put spread; bullish+low IV → calls or bull call spread; neutral+high IV → iron condor; holding+neutral → covered call). Requires options-chain + IV data (yfinance chains as v1; better vendor later). Compute max loss/max gain/breakeven per idea.
  5. **Backtest integration:** every TradeIdea is scoreable by Agent A's harness (entry/exit levels make P&L simulation exact, unlike a bare rating).
  6. **Macro regime screener (added 2026-07-07):** weekly deep-think regime read + daily no-LLM indicator refresh (rates, curve, VIX, DXY, breadth); sector hit-likelihood = macro tailwind × trailing per-sector accuracy from Agent A; feeds "suggested runs" and watchlist macro-triggers. Thin-sample sectors display macro-only scores, clearly marked.
- **Deliverables:** `quant/signals.py` + `quant/options_strategies.py` with unit tests; extended schemas; UI trade-idea cards; backtest comparison: ensemble vs LLM-only vs quant-only.
- **Dependencies:** Agent E snapshot mode + options data (blocks task 4); Agent A harness (blocks task 5); Agent B cost tracking (ensemble adds no LLM calls — keep it that way).
- **Risk:** Options data quality from free vendors is poor (stale IV, wide-spread strikes). Mitigate: liquidity filter (min OI/volume, max bid-ask spread) before any strategy is proposed. LLM must never invent prices — all levels come from the quant layer; the LLM chooses and explains, numbers are computed.

### Agent H — Trade Execution & Risk Controls (P2, gated — hardest to earn merge)
- **Mission:** Execute TradeIdeas automatically when they pass explicit thresholds — with a safety ladder that makes unattended live trading the *last* stage reached, not the first.
- **Scope:** new `tradingagents/execution/` (broker adapter, policy engine, order manager), `api/main.py` execution endpoints, Secret Manager for broker keys, UI positions/orders page.
- **Tasks:**
  1. **Broker adapter interface** (`execution/broker.py`): submit/cancel/replace, positions, fills, account state. First implementation: Alpaca paper API. Live keys and paper keys are separate secrets; the active mode is an explicit config value, never inferred.
  2. **Policy engine** (`execution/policy.py`) — a trade executes only if ALL pass: conviction ≥ threshold; Agent A trailing hit-rate for that ticker/strategy ≥ floor; per-trade max risk (% of equity); portfolio limits (max positions, max sector/single-name exposure, max total options premium); daily loss circuit breaker; market hours + earnings-blackout window; data-quality flag clean (Agent E). Every rejection is logged with the failing rule.
  3. **Safety ladder (each stage is a release gate):**
     - Stage 1 — *Paper*: auto-execute in paper account; run ≥4 weeks; reconcile fills vs. expectations.
     - Stage 2 — *Confirm*: live account, but every order requires human approval in the UI (with a timeout → auto-reject).
     - Stage 3 — *Auto*: live auto-execution, only for trade types with proven Stage 1/2 track record, under tightened limits.
  4. **Order lifecycle:** idempotent submission (client order IDs), OCO/bracket orders for stop+target where broker supports, partial-fill handling, end-of-day reconciliation job, append-only audit log of every decision→order→fill chain.
  5. **Kill switch:** one endpoint + UI button that cancels all open orders and halts the policy engine; also triggered automatically by the daily-loss breaker or reconciliation mismatch.
- **Deliverables:** Broker adapter + policy engine with exhaustive unit tests (policy engine at ~100% branch coverage); positions/orders UI; audit log; Stage 1 soak report.
- **Dependencies:** Hard-blocked by Agent G (structured TradeIdeas) and Agent A (accuracy gate is a policy input). Agent B cancel/cost infra reused.
- **Risk:** Highest in the program — bugs cost real money. Mitigations are structural: staged ladder, defined-risk-only options (A7), limits enforced in code *and* mirrored as broker-side account limits where available, no LLM anywhere in the execution path (LLM proposes; deterministic code decides and executes).

### Agent I — Observability & Ops Hardening (P1, small; recommended addition)
- **Mission:** When a run misbehaves — wrong data, weird decision, runaway cost, failed order — you can see why in minutes, not by re-running.
- **Scope:** cross-cutting; structured logging, tracing, alerting. No feature changes.
- **Tasks:** (1) Structured JSON logging with run_id correlation across graph nodes, API, and (later) execution. (2) LLM call tracing — prompt, response, tokens, latency per node (LangSmith or OpenTelemetry + GCS export; pick one, keep it optional via config). (3) Cloud Monitoring alerts: error-rate, cost-per-day budget, Stage ≥2 execution anomalies → email/Slack. (4) Nightly reconciliation + healthcheck job.
- **Deliverables:** Traceable runs end-to-end; alert policies in Terraform; runbook in `docs/`.
- **Dependencies:** None to start; execution alerting lands with Agent H. Becomes a **prerequisite for Agent H Stage 2** — no live orders without alerting.
- **Risk:** Low. Keep vendor lock-in shallow (OTel-compatible).

## 4. Phased Roadmap

**Phase 0 — Quick wins (week 1):** Agent D entirely; Agent B cancel endpoint; Agent B cost capture skeleton. Rationale: cheap, de-risks everything after, immediately stops money leaks.

**Phase 1 — Foundation (weeks 2–4):** Agent B parallelization + full cost pipeline; Agent E fetch wrapper + snapshot mode; Agent A metrics aggregation + endpoint. These three run in parallel — disjoint file scopes, one shared touchpoint (SSE event schema; Agent B owns it, publishes the contract in week 2).

**Phase 2 — Insight & growth (weeks 5–8):** Agent A backtest harness + baseline report; Agent C full UX slate; Agent I observability; Agent F if Phase 2 metrics justify it. Gate: don't start F unless Phase 1 cost-per-run is known and acceptable.

**Phase 3 — Signal upgrade (weeks 9–13):** Agent G quant layer + ensemble + multi-trade schema (weeks 9–11), then options strategies (weeks 12–13, after Agent E delivers chain/IV data). Gate: backtest must show the ensemble beats LLM-only before options work starts — if it doesn't, fix signals before adding instruments.

**Phase 4 — Execution (weeks 14+, gated):** Agent H. Stage 1 paper trading begins only when: Agent G TradeIdeas are backtested, Agent A publishes trailing accuracy, Agent I alerting is live. Stage 2 (live + confirm) after a ≥4-week clean paper soak. Stage 3 (auto) is earned per trade-type, never scheduled — it ships when the soak data says so, not on a calendar.

## 5. Feature Decision Table

| Feature | Decision | Rationale (impact / effort / risk) |
|---|---|---|
| Accuracy metrics + backtesting | **Build (P0)** | Highest impact; medium effort; core trust question |
| Cost tracking per run | **Build (P0)** | High impact; low effort; low risk |
| Run cancellation | **Build (P0)** | Medium impact; low effort; stops runaway spend |
| Parallel analyst execution | **Build (P1)** | High latency win; medium effort; medium risk (state diffing) |
| Data fetch cache/retry/quality gate | **Build (P1)** | High reliability impact; medium effort |
| Run comparison UI | **Build (P1)** | Medium impact; low effort |
| Scheduled runs + digest | **Defer (P2)** | Valuable only after trust+cost land; unattended-spend risk |
| Quant signal layer + ensemble conviction | **Build (P1)** | High impact — makes decisions testable and cheaper; medium effort |
| Macro regime screener (sector hit-likelihood) | **Build (P2)** | Directs run budget at sectors where macro tailwind × system accuracy is highest; weekly deep-think call + daily quant refresh; owner: Agent G task 6 |
| Deep-dive view + AI Explain/Ask over run artifacts | **Build (P2)** | High trust value; cheap-model Q&A over stored reports only (no new fetches, no effect on decisions); owner: Agent C |
| Settings UI (thresholds, LLM defaults, broker connect) | **Build (P1–P2)** | Policy values editable within hard code-enforced bounds, audited with before/after; broker connect surfaces stage gating; owner: Agent C (UI) + Agent H (validation) |
| Watchlist triggers (schedule / macro / event) | **Build (P2)** | Extends Agent F: cron, regime-change, and earnings-window triggers per list, guarded by daily budget + re-run cooldown |
| Multi-trade structured output (entry/exit/size/RR) | **Build (P1)** | High impact; low-medium effort; enables exact backtesting and execution |
| Options strategies (defined-risk only) | **Build (P2)** | Medium-high impact; medium effort; gated on ensemble beating LLM-only |
| Naked/undefined-risk options | **Don't build** | Unbounded loss; margin modeling absent (A7) |
| Trade execution — paper (Stage 1) | **Build (P2)** | Prerequisite for any live execution; low financial risk |
| Trade execution — live confirm (Stage 2) | **Build (gated)** | Only after 4-week clean paper soak + alerting live |
| Trade execution — live auto (Stage 3) | **Build (earned)** | Per-trade-type, evidence-based; never on a calendar date |
| Observability / LLM tracing / alerting | **Build (P1)** | Medium effort; prerequisite for live execution |
| Intraday / high-frequency signals | **Don't build** | Daily-cadence architecture (SSE runs take minutes); wrong tool for HFT |
| Legacy `/analyze` endpoint | **Remove** | Duplicates `/api/runs`; back-compat window via CHANGELOG |
| `create_social_media_analyst` alias | **Remove** | Already deprecated in code |
| Root `main.py` / `test.py` / `requirements.txt` | **Remove/consolidate** | Duplicate entry points and dep manifests confuse tooling |
| More LLM providers | **Don't build** | 5 providers already; marginal value ≈ 0; each adds capability-matrix maintenance |
| Multi-user auth / tenancy | **Don't build yet** | A1; Cloud Run IAM suffices for one operator |
| Mobile / native app | **Don't build** | Dashboard is responsive enough for the audience of one |
| More debate rounds by default | **Don't change** | Cost scales linearly; revisit only with Agent A evidence it helps |

## 6. Measurable Success Criteria

1. **Trust:** Accuracy dashboard live; ≥20 backtested runs scored vs buy-and-hold; hit rate and per-signal return published per ticker.
2. **Cost:** 100% of runs display total cost within ±5% of provider billing; cost per run baseline established, then reduced ≥20% (model-tier tuning informed by Agent A).
3. **Speed:** Analyst phase wall-clock reduced ≥50%; median full run under 4 minutes (assuming A3 baseline ~8–10 min).
4. **Reliability:** Zero silent degraded runs — 100% of vendor failures surface as a degraded badge or explicit error; cancel works within 30s.
5. **Quality gate:** Test count grows with each workstream (≥300 backend tests); UI tests exist and run in CI; net LOC change for Agent D is negative.
6. **Signals (Agent G):** Backtested ensemble beats LLM-only on hit rate *and* risk-adjusted return (Sharpe on simulated trades) over ≥60 scored TradeIdeas; every published idea has computed (not LLM-generated) entry/stop/target/max-loss; options ideas pass liquidity filter 100% of the time.
7. **Execution (Agent H):** Stage 1: ≥4 weeks paper, zero reconciliation mismatches, zero policy-engine false-approves (audited). Stage 2: 100% of live orders human-approved, kill switch tested weekly. All stages: every order traceable to a run_id + passing policy record; daily loss breaker never exceeded.
8. **Observability (Agent I):** Any anomalous run diagnosable from logs/traces alone (no re-run needed) in <15 min; alert on cost/error/execution anomalies fires in <5 min.

## 7. Delegation Briefs (copy-paste to sub-agents)

- **Agent A:** "Read CLAUDE.md, `graph/reflection.py`, `agents/utils/memory.py`. Build accuracy aggregation over the memory log, expose `GET /api/metrics`, then a point-in-time backtest harness in `eval/` using Agent E's snapshot mode. Guard against look-ahead bias. Ship with unit tests; do not touch analyst prompts."
- **Agent B:** "Read CLAUDE.md §Real-Time Streaming. Add per-call token/cost capture in `llm_clients/base_client.py`, aggregate into run records, add a `cost_update` SSE event (publish schema for Agent C). Add `POST /api/runs/{id}/cancel` with cooperative checks between nodes. Then parallelize the four analysts with LangGraph fan-out — `create_msg_delete()` and `_emit_state_events()` must keep working; prove it with regression tests."
- **Agent C:** "Scope: `ui/src/` + read-only API additions. Add Vitest first, then run comparison, per-step cost/duration display (consume Agent B's `cost_update`), watchlist batch launch, and state-audit fixes. No new state library."
- **Agent D:** "Deletion-only PR: deprecated sentiment alias, legacy `/analyze`, root-level stragglers, `llm_clients/TODO.md` #1 fix. Confirm nothing references removed code (grep + full test suite). Net LOC must be negative."
- **Agent E:** "Scope: `tradingagents/dataflows/` only. Build shared fetch wrapper (retry/backoff/rate-limit/disk cache), degraded-run flagging, and point-in-time snapshot mode (Agent A depends on it — deliver snapshot mode first). Preserve ticker sanitization."
- **Agent F:** "Blocked until A+B ship. Cloud Scheduler → batch-run endpoint → daily digest. Hard per-run and per-day budget caps are merge requirements."
- **Agent G:** "Read `agents/schemas.py` (extend `TraderProposal`, don't replace) and `dataflows/stockstats_utils.py`. Build `quant/signals.py` (momentum, mean-reversion, realized/implied vol, valuation — pure functions, unit-tested, no LLM). Ensemble quant score with the debate verdict into conviction 0–100; surface disagreement. Extend schema to `TradeIdea[]` with instrument, entry zone, stop, targets, risk-based size, RR, horizon, invalidation. Then `quant/options_strategies.py`: defined-risk only, liquidity-filtered, max-loss/breakeven computed. Rule: the LLM chooses and explains; every number is computed. Wire ideas into Agent A's backtester."
- **Agent H:** "Blocked by G + A + I(alerting). Build `execution/`: broker adapter (Alpaca paper first; keys in Secret Manager; mode is explicit config), deterministic policy engine (conviction, trailing accuracy, per-trade risk, portfolio limits, daily-loss breaker, market-hours/earnings blackout — log every rejection), staged ladder paper→confirm→auto, idempotent bracket orders, EOD reconciliation, append-only audit log, kill switch. No LLM in the execution path. Policy engine at ~100% branch coverage before Stage 1."
- **Agent I:** "Cross-cutting, no feature changes: structured JSON logs with run_id correlation, per-node LLM tracing (config-optional), Cloud Monitoring alerts (cost/day, error rate, execution anomalies) in Terraform, ops runbook. Ship before Agent H Stage 2."

## 8. Coordination Rules

Agent D merges first. Agent B owns the SSE event schema; A, C, E consume it. Agent G owns the `TradeIdea` schema; H and C consume it. All merges gated on `docker compose run --rm test` green plus lint/security jobs in `ci.yml`. Any cross-scope file edit (e.g., E touching `trading_graph.py`) goes through the orchestrator to avoid conflicts.

**Execution-specific rules:** Agent H PRs require (1) policy-engine branch coverage report attached, (2) a "what happens if this is wrong" section in the PR description, (3) sign-off from the orchestrator (Tim) — no auto-merge ever. Stage promotions (paper→confirm→auto) are decided by soak-report review, not by PR merge. LLM output is never parsed in `execution/`; only validated `TradeIdea` objects cross the boundary.

## 9. Standing Caveats

This system informs and (eventually) executes Tim's personal trades. It is not investment advice, and backtest performance does not guarantee live performance — LLM-driven signals are especially vulnerable to regime change and to training-data contamination in backtests (the model may "remember" what happened after a historical date; Agent A must note this limitation in every backtest report and prefer post-knowledge-cutoff evaluation windows). Position sizing caps and the daily-loss breaker are the real safety net; keep them boring and conservative.
