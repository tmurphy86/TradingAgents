resource "google_cloudbuild_trigger" "deploy" {
  project  = var.project_id
  name     = "tradingagents-deploy"
  location = var.region

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^main$"
    }
  }

  filename = "cloudbuild.yaml"

  substitutions = {
    _REGION    = var.region
    _REPO_PATH = local.image_repo
    _SERVICE   = google_cloud_run_v2_service.api.name
  }

  depends_on = [google_project_service.apis]
}
