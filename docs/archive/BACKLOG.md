# TradingAgents — Backlog

> Written/prioritized by the program lead (Cowork). Consumed top-down by the Claude Code eng lead via the lifecycle-os `orchestrate` skill.
> Tickets are cut from [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) workstreams. Ticket rules: one module focus, executable acceptance criteria, explicit out-of-scope.
> **BUG GATE: while any ticket in `## BUGS` is open, feature tickets must not be dispatched.** Bugs come from docs/ISSUES.md. Every fix ships a regression test that fails on pre-fix code.
> Assign to domain subagents (graph-engineer, data-engineer, ui-engineer, infra-engineer) per CLAUDE.md Lifecycle config; anything touching `tradingagents/execution/` also gets `execution-safety-reviewer`.

## BUGS

_(none open)_

## P1 — Trust & Ops (cost tracking, cancellation, parallel analysts)

_(Program lead: cut tickets here from IMPROVEMENT_PLAN Phase 1 workstreams. Format below.)_

### TA-101: {ticket title}
**Assign:** {domain subagent}  **Depends:** —
**Goal:** {one sentence, outcome not activity}
**Files:** {explicit list — workers may touch ONLY these}
**Acceptance criteria:**
- [ ] {executable/verifiable criterion}
- [ ] {tests named here — note WHAT LAYER they exercise}
**Out of scope:** {explicit}
**Test:** `{exact command, e.g. docker compose run --rm test or python -m pytest tests/ -m "unit or smoke" -q}`
