# Incidents

## 2026-07-08 — Terraform Apply failed on Cloud Run image drift

- **Cause:** The `Terraform Apply` workflow attempted an in-place update of the Cloud Run service only to remove GitHub Actions drift (`client`, `client_version`, template labels, and scaling metadata). Cloud Run revalidated the live container image during that update, but the service was pointing at `app:previous`, and that rollback tag did not exist in Artifact Registry.
- **Fix:** Updated `/home/runner/work/TradingAgents/TradingAgents/terraform/run.tf` to ignore deploy-owned Cloud Run drift in addition to the image field, so Terraform no longer performs no-op service updates just to scrub GitHub Actions metadata.
- **Prevention:** Keep GitHub Actions as the source of truth for deploy-time Cloud Run metadata and let Terraform manage only the infrastructure settings declared in code; this avoids triggering Cloud Run updates that depend on transient rollback tags.
