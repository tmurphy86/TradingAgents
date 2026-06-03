# Creates empty secret stubs for all supported providers.
# Populate values separately:
#   echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-
# Then add the secret name to var.active_secrets so it is mounted in Cloud Run.
resource "google_secret_manager_secret" "api_keys" {
  for_each = toset(var.secret_names)

  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
