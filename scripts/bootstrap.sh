#!/usr/bin/env bash
# Bootstrap TradingAgents GCP infrastructure from a clean slate.
# Run this once locally before the GitHub Actions CI/CD pipeline takes over.
#
# Prerequisites:
#   gcloud   — https://cloud.google.com/sdk/docs/install
#   terraform >= 1.9 — https://developer.hashicorp.com/terraform/install
#
# Usage:
#   chmod +x scripts/bootstrap.sh
#   ./scripts/bootstrap.sh
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${BLUE}→${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}!${NC} $*"; }
die()     { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TF_DIR="$REPO_ROOT/terraform"

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
header "Checking prerequisites..."

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    die "$1 is not installed. $2"
  fi
  success "$1 found ($(command -v "$1"))"
}

check_cmd gcloud  "Install: https://cloud.google.com/sdk/docs/install"
check_cmd terraform "Install: https://developer.hashicorp.com/terraform/install"

TF_VERSION=$(terraform version -json | python3 -c "import sys,json; print(json.load(sys.stdin)['terraform_version'])" 2>/dev/null || terraform version | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
info "Terraform $TF_VERSION"

if ! gcloud auth print-access-token &>/dev/null; then
  die "Not authenticated to gcloud.\nRun: gcloud auth login && gcloud auth application-default login"
fi
success "gcloud authenticated ($(gcloud config get account 2>/dev/null))"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
header "Configuration"
echo "Press Enter to accept the default shown in [brackets]."
echo ""

ask() {
  local varname="$1" prompt="$2" default="$3"
  local current="${!varname:-}"
  if [[ -n "$current" ]]; then
    info "$varname already set to '$current' (from environment)"
    return
  fi
  if [[ -n "$default" ]]; then
    read -rp "  $prompt [$default]: " val
    printf -v "$varname" '%s' "${val:-$default}"
  else
    while true; do
      read -rp "  $prompt: " val
      [[ -n "$val" ]] && break
      warn "This value is required."
    done
    printf -v "$varname" '%s' "$val"
  fi
}

ask GCP_PROJECT    "GCP project ID"                                    ""
ask GCP_REGION     "GCP region"                                        "us-central1"
ask GITHUB_OWNER   "GitHub repo owner (your username or org)"          ""
ask GITHUB_REPO    "GitHub repo name"                                  "TradingAgents"
ask INVOKER_EMAIL  "Google account email allowed to call Cloud Run"    ""

STATE_BUCKET="${GCP_PROJECT}-tf-state"

echo ""
info "Summary:"
echo "    Project:       $GCP_PROJECT"
echo "    Region:        $GCP_REGION"
echo "    GitHub:        ${GITHUB_OWNER}/${GITHUB_REPO}"
echo "    Invoker:       $INVOKER_EMAIL"
echo "    State bucket:  gs://${STATE_BUCKET}"
echo ""
read -rp "  Proceed? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# ---------------------------------------------------------------------------
# Set active project
# ---------------------------------------------------------------------------
header "Setting GCP project..."
gcloud config set project "$GCP_PROJECT" --quiet
success "Active project: $GCP_PROJECT"

# ---------------------------------------------------------------------------
# Enable APIs needed for the state bucket (minimal set for bootstrap)
# ---------------------------------------------------------------------------
header "Enabling bootstrap APIs..."
gcloud services enable \
  storage.googleapis.com \
  iam.googleapis.com \
  --project="$GCP_PROJECT" \
  --quiet
success "Bootstrap APIs enabled"

# ---------------------------------------------------------------------------
# Create Terraform state bucket
# ---------------------------------------------------------------------------
header "Terraform state bucket..."
if gcloud storage buckets describe "gs://${STATE_BUCKET}" --project="$GCP_PROJECT" &>/dev/null 2>&1; then
  success "gs://${STATE_BUCKET} already exists — skipping creation"
else
  info "Creating gs://${STATE_BUCKET}..."
  gcloud storage buckets create "gs://${STATE_BUCKET}" \
    --project="$GCP_PROJECT" \
    --location="$GCP_REGION" \
    --uniform-bucket-level-access \
    --quiet
  gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning --quiet
  success "State bucket created with versioning enabled"
fi

# ---------------------------------------------------------------------------
# Write terraform.tfvars
# ---------------------------------------------------------------------------
header "Terraform variables..."
TFVARS="$TF_DIR/terraform.tfvars"
if [[ -f "$TFVARS" ]]; then
  warn "terraform/terraform.tfvars already exists — skipping generation"
  warn "Delete it and re-run bootstrap to regenerate."
else
  info "Writing terraform/terraform.tfvars..."
  cat > "$TFVARS" <<TFVARS
project_id    = "$GCP_PROJECT"
region        = "$GCP_REGION"
github_owner  = "$GITHUB_OWNER"
github_repo   = "$GITHUB_REPO"
invoker_email = "$INVOKER_EMAIL"

# After adding secret values via gcloud, list them here to inject into Cloud Run:
#   echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-
active_secrets = [
  # "OPENAI_API_KEY",
  # "ANTHROPIC_API_KEY",
]
TFVARS
  success "terraform/terraform.tfvars written (gitignored)"
fi

# ---------------------------------------------------------------------------
# Write backend.tfvars (gitignored) so subsequent local runs work without flags:
#   terraform init -backend-config=backend.tfvars
# ---------------------------------------------------------------------------
cat > "$TF_DIR/backend.tfvars" <<EOF
bucket = "$STATE_BUCKET"
EOF
success "terraform/backend.tfvars written (gitignored)"

# ---------------------------------------------------------------------------
# Terraform init with GCS backend
# ---------------------------------------------------------------------------
header "Initialising Terraform..."
cd "$TF_DIR"
terraform init \
  -backend-config=backend.tfvars \
  -reconfigure \
  -input=false
success "Terraform initialised (state → gs://${STATE_BUCKET}/tradingagents/state)"

# ---------------------------------------------------------------------------
# Terraform plan
# ---------------------------------------------------------------------------
header "Planning infrastructure..."
terraform plan -out=tfplan -input=false

# ---------------------------------------------------------------------------
# Terraform apply
# ---------------------------------------------------------------------------
echo ""
read -rp "  Apply this plan? [y/N] " apply_confirm
if [[ ! "$apply_confirm" =~ ^[Yy]$ ]]; then
  warn "Apply skipped. Run 'terraform apply tfplan' inside terraform/ when ready."
  exit 0
fi

info "Applying..."
terraform apply -input=false tfplan
rm -f tfplan
success "Infrastructure provisioned"

# ---------------------------------------------------------------------------
# Push GitHub Actions variables and secrets via gh CLI
# ---------------------------------------------------------------------------
header "Configuring GitHub Actions..."

GH_REPO="${GITHUB_OWNER}/${GITHUB_REPO}"

WIF_PROVIDER=$(terraform output -raw workload_identity_provider)
DEPLOY_SA=$(terraform output -raw github_deploy_sa)
TERRAFORM_SA=$(terraform output -raw github_terraform_sa)
IMAGE_REPO=$(terraform output -raw artifact_registry_repo)

set_vars() {
  local repo="$1"
  # Terraform input variables — each maps to a TF_VAR_* env var in the workflow.
  # active_secrets starts empty; update with:
  #   gh variable set TF_VAR_ACTIVE_SECRETS --body '["OPENAI_API_KEY"]' --repo OWNER/REPO
  gh variable set TF_VAR_PROJECT_ID     --body "$GCP_PROJECT"   --repo "$repo"
  gh variable set TF_VAR_REGION         --body "$GCP_REGION"    --repo "$repo"
  gh variable set TF_VAR_INVOKER_EMAIL  --body "$INVOKER_EMAIL" --repo "$repo"
  gh variable set TF_VAR_ACTIVE_SECRETS --body "[]"             --repo "$repo"
  # Terraform outputs — used by deploy and terraform workflows for GCP auth
  gh variable set GCP_TF_STATE_BUCKET            --body "$STATE_BUCKET"  --repo "$repo"
  gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIF_PROVIDER"  --repo "$repo"
  gh variable set GCP_DEPLOY_SA                  --body "$DEPLOY_SA"     --repo "$repo"
  gh variable set GCP_TERRAFORM_SA               --body "$TERRAFORM_SA"  --repo "$repo"
  gh variable set GCP_IMAGE_REPO                 --body "$IMAGE_REPO"    --repo "$repo"
}

if ! command -v gh &>/dev/null; then
  warn "gh CLI not found — skipping automated GitHub setup."
  warn "Install from https://cli.github.com then run the following manually:"
  echo ""
  echo "  gh variable set TF_VAR_PROJECT_ID              --body \"$GCP_PROJECT\"   --repo $GH_REPO"
  echo "  gh variable set TF_VAR_REGION                  --body \"$GCP_REGION\"    --repo $GH_REPO"
  echo "  gh variable set TF_VAR_INVOKER_EMAIL           --body \"$INVOKER_EMAIL\" --repo $GH_REPO"
  echo "  gh variable set TF_VAR_ACTIVE_SECRETS          --body \"[]\"             --repo $GH_REPO"
  echo "  gh variable set GCP_TF_STATE_BUCKET            --body \"$STATE_BUCKET\"  --repo $GH_REPO"
  echo "  gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body \"$WIF_PROVIDER\"  --repo $GH_REPO"
  echo "  gh variable set GCP_DEPLOY_SA                  --body \"$DEPLOY_SA\"     --repo $GH_REPO"
  echo "  gh variable set GCP_TERRAFORM_SA               --body \"$TERRAFORM_SA\"  --repo $GH_REPO"
  echo "  gh variable set GCP_IMAGE_REPO                 --body \"$IMAGE_REPO\"    --repo $GH_REPO"
elif ! gh auth status &>/dev/null; then
  warn "gh CLI is not authenticated. Run: gh auth login"
  warn "Then re-run this script or set the variables manually (see above)."
else
  info "Setting GitHub Actions variables on $GH_REPO..."
  set_vars "$GH_REPO"
  success "All variables set"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}================================================================${NC}"
echo -e "${BOLD}  Bootstrap complete!${NC}"
echo -e "${BOLD}================================================================${NC}"
echo ""
echo -e "${BOLD}One remaining manual step:${NC}"
echo ""
echo "  Add ANTHROPIC_API_KEY to GitHub Actions secrets (used by the AI code-review job):"
echo "  gh secret set ANTHROPIC_API_KEY --repo $GH_REPO"
echo ""
echo -e "${BOLD}To add LLM/data API keys later:${NC}"
echo ""
echo "  1. Add the key value to GCP Secret Manager:"
echo "     echo -n 'sk-...' | gcloud secrets versions add OPENAI_API_KEY --data-file=-"
echo ""
echo "  2. Update the TF_VAR_ACTIVE_SECRETS GitHub variable to include the key name:"
echo "     gh variable set TF_VAR_ACTIVE_SECRETS --body '[\"OPENAI_API_KEY\"]' --repo $GH_REPO"
echo ""
echo "  3. Push to main — the terraform workflow will apply the change automatically."
echo ""
