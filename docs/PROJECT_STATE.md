# TradingAgents — Project State

> Sync file between the program lead (Cowork) and the Claude Code engineering lead.
> Eng lead: update at END of every session. Program lead: read at START of every planning session.
> **New program lead? Read [BOOTSTRAP.md](BOOTSTRAP.md) FIRST — it tells you what to load and what to skip.**
> Per-ticket shipping detail + session log: `docs/archive/HISTORY.md` (create on first archive).
> **Hard cap: keep this file under ~70 lines.**

## Current milestone
**Phase 0 — quick wins** (milestone `P0 — Quick wins`). Bugs #8 and #9 are fixed and deployed; the bug gate is clear. #11 and #10 are in PRs. Remaining dispatch order: #12 terraform output → #13 cost → #14 cost UI → #16 lifecycle smoke → #15 UI gate.

## Phase status (mirrors README status table — keep in sync)
| Phase | Scope | Status |
|---|---|---|
| Shipped | 12-agent pipeline, dashboard, reflection loop, GCP deploy + CI/CD | SHIPPED |
| P0 | Hygiene removals, run cancel, cost capture skeleton, UI lint/test gate | IN PROGRESS — #8, #9 shipped; #10, #11 in PR; #12–#16 open |
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
- PR #21 (#11 hygiene removals): reviewed, CI green, waiting for merge. Breaking: `POST /analyze` returns 404 once deployed.
- PR #22 (#10 cancel button): reviewed, build green, **never exercised in a browser**. #10 is `status:partial` until someone records cancelling a real local run.

## Blockers / DECISION NEEDED
- Tim: merge PR #21 and PR #22. The eng-lead session's merge of #21 was blocked by the permission check, so auto-when-green did not happen.
- #12 and #15 touch protected paths (owner merge). After #11 deploys, `terraform output analyze_curl` points at a removed route until #12 lands.
- CI auto-remediate still pushes to the PR branch when the test job fails; which token it uses is unverified (see #8).
- Deep links to `/runs/<id>` return 404 from the built app (static mount has no SPA fallback), so a refresh on a run page breaks. Not ticketed.
- Verify assumption A6 (Alpaca options approval levels/API support) before any Phase 3+ options ticket.

## Session log (recent only — archive the rest)
- 2026-10-12 (eng lead): shipped #9 run cancel (PR #18) and #8 read-only lint (PR #19, owner-merged; evidence PR #20 closed unmerged); both deployed green. #11 → PR #21, #10 → PR #22. #11 went to `senior-coder` because no domain agent owns `api/`.
- 2026-10-12: state audit; migrated to lifecycle-os v1.0.0-rc.3; Makefile added; legacy BACKLOG/ISSUES archived (both were empty templates, nothing migrated); drift-detection workflow found disabled for inactivity and re-enabled (manual run green); P0 tickets #8–#16 cut.
- 2026-07-12: lifecycle-os v0.2.0 adopted; state docs created (Cowork session).
