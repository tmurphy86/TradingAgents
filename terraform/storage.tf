resource "google_storage_bucket" "data" {
  name          = "${var.project_id}-tradingagents-data"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Keep only the 3 most recent versions of each object to bound storage cost
  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}
