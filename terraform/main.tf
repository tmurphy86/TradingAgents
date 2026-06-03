terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Uncomment to store state in GCS (recommended once the bucket exists)
  # backend "gcs" {
  #   bucket = "<your-project-id>-tf-state"
  #   prefix = "tradingagents/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
