---
name: release
description: Cut a release — test gate, changelog, version bump, merge,
  deploy verification. Use for "release", "ship vX.Y.Z", "prep the changelog".
---
# Release

1. Gate: `docker compose run --rm test` must be green. Never release over red.
2. Update CHANGELOG.md: new `## vX.Y.Z (YYYY-MM-DD)` section — features,
   fixes, breaking changes, credits. Match the existing format.
3. Bump `version` in pyproject.toml.
4. Commit, PR, merge to main. deploy.yml handles: test → build → push to
   Artifact Registry → Cloud Run deploy (WIF). No manual deploy commands.
5. Verify: watch the Actions run; then
   `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <service-url>/health`
6. Tag: `git tag vX.Y.Z && git push --tags`.
7. If deploy fails: Cloud Run keeps serving the previous revision. Diagnose via
   the Actions log; rollback = `gcloud run services update-traffic` to the
   prior revision (human runs this).
