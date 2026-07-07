terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # GCS backend — bucket is passed at init time so this file stays committed as-is.
  # Locally:  scripts/bootstrap.sh handles this automatically
  # CI:       terraform init -backend-config="bucket=$GCP_TF_STATE_BUCKET"
  backend "gcs" {
    prefix = "tradingagents/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
