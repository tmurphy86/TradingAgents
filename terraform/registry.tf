resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "tradingagents"
  description   = "TradingAgents Docker images"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-recent-30"
    action = "KEEP"
    most_recent_versions {
      keep_count = 30 # was 10 — comfortably exceeds deploy cadence between rollbacks
    }
  }

  depends_on = [google_project_service.apis]
}
