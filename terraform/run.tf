locals {
  image_repo = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/app"
  image      = "${local.image_repo}:${var.image_tag}"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "tradingagents"
  location = var.region
  project  = var.project_id

  deletion_protection = false

  template {
    service_account = google_service_account.run_sa.email
    timeout         = "${var.cloud_run_timeout_seconds}s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    # Mount the GCS data bucket at the path the app uses for all persistence
    volumes {
      name = "tradingagents-data"
      gcs {
        bucket    = google_storage_bucket.data.name
        read_only = false
      }
    }

    containers {
      image = local.image

      resources {
        limits = {
          memory = var.cloud_run_memory
          cpu    = var.cloud_run_cpu
        }
        # Release CPU when container is not actively serving a request
        cpu_idle = true
      }

      volume_mounts {
        name       = "tradingagents-data"
        mount_path = "/home/appuser/.tradingagents"
      }

      # Inject each active secret as an environment variable
      dynamic "env" {
        for_each = toset(var.active_secrets)
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      env {
        name  = "PYTHONUNBUFFERED"
        value = "1"
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 10
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_storage_bucket_iam_member.run_sa_storage,
    google_secret_manager_secret_iam_member.run_sa_secrets,
  ]
}
