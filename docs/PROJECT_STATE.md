# TradingAgents — Project State

> Sync file between the program lead (Cowork) and the Claude Code engineering lead.
> Eng lead: update at END of every session. Program lead: read at START of every planning session.
> **New program lead? Read [BOOTSTRAP.md](BOOTSTRAP.md) FIRST — it tells you what to load and what to skip.**
> Per-ticket shipping detail + session log: `docs/archive/HISTORY.md` (create on first archive).
> **Hard cap: keep this file under ~70 lines.**

## Current milestone
**Phase 0 — quick wins.** Repo was idle 2026-07-08 → 2026-10-12; a code audit on 2026-10-12 found no IMPROVEMENT_PLAN workstream started. Lifecycle-os migrated to v1.0.0-rc.3 (tickets are GitHub issues, `make` targets, PR delivery, auto-merge when green). Dispatch order: hygiene removals → run cancel → cost capture → UI lint/test gate.

## Phase status (mirrors README status table — keep in sync)
| Phase | Scope | Status |
|---|---|---|
| Shipped | 12-agent pipeline, dashboard, reflection loop, GCP deploy + CI/CD | SHIPPED |
| P0 | Hygiene removals, run cancel, cost capture skeleton, UI lint/test gate | TICKETS BEING CUT |
| P1 | Full cost pipeline, parallel analysts, fetch wrapper + snapshot mode, accuracy metrics endpoint | PLANNED |
| P2 | Accuracy dashboard + point-in-time backtest harness, UX slate, observability | PLANNED |
| P3 | Quant ensemble, TradeIdea construction, options; macro screener, settings/policy UI | PLANNED |
| P4 | Policy-gated execution (Alpaca paper → confirm → auto) | GATED — safety ladder, evidence-promoted only |

## Standing instructions (do not drop)
- **Bug gate:** open `bug` issues are step 1 of every eng-lead session (`triage`); open bugs block features; every fix ships a pre-fix-failing regression test.
- **Reopen protocol:** reopened issue → post-mortem of the prior fix's regression tests before any new fix.
- **Reviewer:** every diff checked against the ticket issue's FULL acceptance criteria; `execution-safety-reviewer` additionally on anything in `tradingagents/execution/` (agent file does not exist yet — create it before any execution ticket).
- **Safety ladder:** stage promotions require soak evidence and a program-lead ADR; never scheduled.
- **Infra:** `terraform apply` human-only; deploy metadata belongs to GitHub Actions (see INCIDENTS 2026-07-08). Protected paths (`terraform/**`, `.github/workflows/**`, `tradingagents/execution/**`) are owner-merge even though Merge is auto-when-green.

## In flight
- Housekeeping + lifecycle migration PR (branch `chore/lifecycle-v1-migration`).

## Known defects (to be filed with the P0 tickets)
- `DELETE /api/runs/{id}` on a running run removes the record but the worker thread keeps calling LLMs (`api/main.py`). Fixed by the cancel ticket.

## Blockers / DECISION NEEDED
- Verify assumption A6 (Alpaca options approval levels/API support) before any Phase 3+ options ticket.

## Session log (recent only — archive the rest)
- 2026-10-12: state audit; migrated to lifecycle-os v1.0.0-rc.3; Makefile added; legacy BACKLOG/ISSUES archived (both were empty templates, nothing migrated); drift-detection workflow found disabled for inactivity.
- 2026-07-12: lifecycle-os v0.2.0 adopted; state docs created (Cowork session).
