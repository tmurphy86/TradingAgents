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
PR (ci.yml):        build test container → lint (ruff) → security (bandit) → test → ui-build → AI code review (non-blocking)
main (deploy.yml):  test → build prod image → push to Artifact Registry → gcloud run deploy (WIF, no SA keys)
terraform (terraform.yml): PR = plan as comment · main = apply
```

`cloudbuild.yaml` is deprecated — GitHub Actions is the only CI/CD path.

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
