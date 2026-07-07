output "cloud_run_url" {
  description = "Base URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.api.uri
}

output "artifact_registry_repo" {
  description = "Full Artifact Registry path for tagging Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "data_bucket" {
  description = "GCS bucket name that mounts as ~/.tradingagents inside Cloud Run"
  value       = google_storage_bucket.data.name
}

output "service_account_email" {
  description = "Service account used by the Cloud Run container"
  value       = google_service_account.run_sa.email
}

output "workload_identity_provider" {
  description = "WIF provider resource name — paste into GCP_WORKLOAD_IDENTITY_PROVIDER GitHub variable"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deploy_sa" {
  description = "Deploy service account email — paste into GCP_DEPLOY_SA GitHub variable"
  value       = google_service_account.github_deploy.email
}

output "github_terraform_sa" {
  description = "Terraform service account email — paste into GCP_TERRAFORM_SA GitHub variable"
  value       = google_service_account.github_terraform.email
}

output "analyze_curl" {
  description = "Example authenticated curl command to trigger an analysis"
  value       = <<-EOT
    curl -X POST \
      -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
      -H "Content-Type: application/json" \
      -d '{"ticker":"NVDA","date":"2026-01-15"}' \
      ${google_cloud_run_v2_service.api.uri}/analyze
  EOT
}
