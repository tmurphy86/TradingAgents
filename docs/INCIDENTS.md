# Incidents

## 2026-07-08 — Terraform Apply failed on Cloud Run image drift

- **Cause:** The `Terraform Apply` workflow attempted an in-place update of the Cloud Run service only to remove GitHub Actions drift (`client`, `client_version`, template labels, and scaling metadata). Cloud Run revalidated the live container image during that update, but the service was pointing at `app:previous`, and that rollback tag did not exist in Artifact Registry.
- **Fix:** Two changes landed in #6 (superseding #5):
  1. Rollback is now **revision-based**: `deploy.yml` captures the currently-serving revision before deploying and, on health-check failure, shifts traffic back with `gcloud run services update-traffic --to-revisions=<prev>=100`. This pulls no image, so rollback can no longer fail on a missing/dangling tag, and Terraform only ever sees real `:SHA` images. The mutable `:previous` tag was removed.
  2. `terraform/run.tf` now ignores deploy-owned Cloud Run drift (`client`, `client_version`, `template[0].labels`) in addition to the image, so Terraform no longer performs no-op service updates just to scrub GitHub Actions metadata. `scaling` is deliberately **not** ignored — `max_instance_count = 1` is a load-bearing guardrail and must stay under Terraform control.
- **Prevention:** Keep GitHub Actions as the source of truth for deploy-time Cloud Run metadata and let Terraform manage the infrastructure settings declared in code; this avoids triggering Cloud Run updates that depend on transient tags. Artifact Registry retention was also raised (`keep_count` 10 → 30) so the cleanup policy can't GC a digest that a live or previous revision still references.
