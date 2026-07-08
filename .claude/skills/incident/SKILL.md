---
name: incident
description: Diagnose production or local incidents — failed runs, stuck runs,
  deploy failures, data vendor outages. Use for "run failed", "dashboard hung",
  "deploy broke", "everything is erroring".
---
# Incident Runbook

Triage order:
1. Scope: one run, one ticker, or everything? Local or Cloud Run?
2. Run records: `~/.tradingagents/runs/<id>.json` — status, error field, which
   agent step died. Records stuck in "running" are healed to "error" on server
   restart (lifespan handler).
3. Full state: `~/.tradingagents/logs/<TICKER>/TradingAgentsStrategy_logs/`.
4. Cloud Run: `gcloud run services logs read <service> --region <region>` —
   look for the run_id.
5. Vendor outage pattern: analyst report empty/short while others fine →
   check the data vendor, not the LLM. Rate limits on Alpha Vantage free tier
   are the usual suspect.
6. LLM provider pattern: all runs fail at the same node → check API key,
   model catalog entry, capability flags.
7. Checkpoint recovery: rerun with `--checkpoint`; clear poisoned state with
   `--clear-checkpoints` or delete `~/.tradingagents/cache/checkpoints/<TICKER>.db`.
8. Deploy incident: previous Cloud Run revision still serves; rollback via
   `gcloud run services update-traffic` (human-only).

Afterwards: append a dated post-mortem note (cause, fix, prevention) to
docs/INCIDENTS.md (create if missing).
