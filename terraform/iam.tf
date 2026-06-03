data "google_project" "project" {
  project_id = var.project_id
}

resource "google_service_account" "run_sa" {
  account_id   = "tradingagents-run"
  display_name = "TradingAgents Cloud Run"
  project      = var.project_id

  depends_on = [google_project_service.apis]
}

# Full object access on the data bucket (read/write memory log, checkpoints, run logs)
resource "google_storage_bucket_iam_member" "run_sa_storage" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.run_sa.email}"
}

# Secret accessor for each active secret mounted as an env var
resource "google_secret_manager_secret_iam_member" "run_sa_secrets" {
  for_each = toset(var.active_secrets)

  project   = var.project_id
  secret_id = google_secret_manager_secret.api_keys[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

# Cloud Run invoker for the specified user account
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "user:${var.invoker_email}"
}

# Cloud Build service account needs to deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

# Cloud Build needs to act as the Cloud Run service account during deploy
resource "google_service_account_iam_member" "cloudbuild_sa_user" {
  service_account_id = google_service_account.run_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}
