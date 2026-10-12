# terraform/ + CI/CD — GCP Infrastructure

**Rule: Claude may run `terraform plan`. `terraform apply` and `gcloud run deploy` are human-only.**

## Infrastructure

One `terraform apply` provisions: Cloud Run, GCS bucket (FUSE-mounted as `~/.tradingagents`), Secret Manager, Artifact Registry, and Workload Identity Federation for GitHub Actions. API is IAM-authenticated (no public access).

**Docker image:** `api/Dockerfile` is a 3-stage build — Node 20 builds the React UI, `ghcr.io/astral-sh/uv` installs Python deps, slim runtime serves the full stack from one container. Stage `test` is the CI test container.

**Secrets workflow:** stubs created by `terraform apply`, then:
```bash
echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```
Add the name to `active_secrets` in `terraform.tfvars`, re-apply.

## CI/CD (`.github/workflows/`)

```
PR (ci.yml):        lint (ruff, read-only) + security (bandit) → build test image (includes UI build) → test → auto-remediate (only if test itself fails)
main (deploy.yml):  test → build prod image → push to Artifact Registry → gcloud run deploy (WIF, no SA keys)
terraform (terraform.yml): PR = plan as comment · main = apply
```

`cloudbuild.yaml` is deprecated — GitHub Actions is the only CI/CD path.

### CI notes (`ci.yml`)

Actual job chain: `lint` + `security` → Phase 1 gate → build test image → `test` → `auto-remediate`.

- **Lint is read-only — CI never pushes lint fixes.** On failure the job prints the commands to run locally: `uv run --extra dev ruff check --fix tradingagents/ api/ cli/ tests/`, then `uv run --extra dev ruff format tradingagents/ api/ cli/ tests/`, then `make lint`. Commit and push the result yourself. The job checks out the PR merge ref with `persist-credentials: false` and `contents: read`.
- **CI does still push to the PR branch in exactly one case: the `test` job itself failed.** `auto-remediate` then runs Claude Code (`contents: write`), which may commit a fix to the branch. It does not run when lint, security or the image build fails and `test` is merely skipped.
- **Keep `auto-remediate` gated on `needs.test.result == 'failure'`, never on bare `failure()`.** At job level `failure()` is true when *any* ancestor job failed, so a bare `failure()` would start remediation (and a push) on every lint or build failure — observed on run 28891867144, where the build failed, Tests was skipped, and auto-remediate still ran.
- **After an auto-remediate push, check that the new head commit has checks.** If the push was made with `GITHUB_TOKEN` it triggers no workflow and the head commit has none; re-run CI by pushing a commit yourself (an empty one is enough) before merging. Also read the remediation commit message for skip markers (next rule).
- **Never put a skip-CI marker in a commit that can reach a PR** (`[skip ci]`, `[ci skip]`, `[no ci]`, `[skip actions]`, `[actions skip]`, or a `skip-checks: true` trailer). Squash-merge copies every commit message into the squash commit body, and GitHub then skips all push workflows on `main` — no Deploy. This is what happened on PR #7 (issue #8). Before squash-merging, read the commit body GitHub proposes.
- **Pushes made with `GITHUB_TOKEN` do not trigger workflows.** A workflow that pushes to a PR branch leaves the new head commit with no checks. Do not add another job that pushes unless it also solves that, and do not solve it with a PAT (new long-lived credential).
- **ruff version comes from `uv.lock`** (the lint job reads the first `ruff` package block at run time and rejects anything that is not a plain `X.Y.Z`), so CI and `make lint` always agree. Bump ruff by updating the lock, not the workflow.
- **Run ruff in `run:` steps with explicit paths.** `astral-sh/ruff-action` appends its `src` input (default: whole workspace) after `args`, so paths given in `args` do not limit what it touches. Markdown is additionally excluded via `[tool.ruff.format] exclude` in `pyproject.toml`.
- `terraform.yml` applies on any push to `main` that touches `terraform/**` — including docs-only edits to this file. `deploy.yml` ignores a push only when *every* changed file is under `terraform/**`.

## Required GitHub Actions variables (Settings → Secrets and variables → Actions)

| Variable | Workflow | Description |
|---|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | deploy, terraform | WIF provider (from `terraform output workload_identity_provider`) |
| `GCP_DEPLOY_SA` | deploy | Deploy SA email (from `terraform output github_deploy_sa`) |
| `GCP_REGION` | deploy | GCP region (e.g. `us-central1`) |
| `GCP_IMAGE_REPO` | deploy | Artifact Registry path |
| `GCP_CLOUD_RUN_SERVICE` | deploy | Cloud Run service name |
| `GCP_TERRAFORM_SA` | terraform | Terraform SA email (from `terraform output github_terraform_sa`) |
| `GCP_TF_STATE_BUCKET` | terraform | GCS bucket for Terraform state |
| `TF_VAR_PROJECT_ID` / `TF_VAR_REGION` / `TF_VAR_INVOKER_EMAIL` / `TF_VAR_ACTIVE_SECRETS` | terraform | Terraform input variables |
| `ANTHROPIC_API_KEY` | ci | AI code review job (non-blocking if missing) |

Run `terraform apply` once first — the `workload_identity_*` outputs supply the WIF values.
