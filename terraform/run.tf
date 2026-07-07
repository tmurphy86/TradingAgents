locals {
  image_repo = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/app"
  # On first apply the real image doesn't exist yet. Use Google's public Cloud Run
  # hello placeholder so the service can be created. Once CI pushes the real image
  # and deploys it via `gcloud run deploy`, the lifecycle rule below ensures
  # Terraform never reverts that image back to this placeholder.
  image = var.image_tag != null ? "${local.image_repo}:${var.image_tag}" : "us-docker.pkg.dev/cloudrun/container/hello:latest"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "tradingagents"
  location = var.region
  project  = var.project_id

  deletion_protection = false

  template {
    service_account = google_service_account.run_sa.email
    timeout         = "${var.cloud_run_timeout_seconds}s"

    # One analysis fully occupies an instance (10–30 min, CPU/memory-heavy),
    # so serialise requests rather than letting the Cloud Run default of 80
    # concurrent requests pile threads onto a single instance and OOM it.
    max_instance_request_concurrency = 1

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

      # Give the heavy module imports time on a cold scale-from-zero start
      # before liveness checks begin.
      startup_probe {
        http_get {
          path = "/health"
        }
        period_seconds    = 5
        failure_threshold = 12
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

  # CI (GitHub Actions) owns the running image via `gcloud run deploy`.
  # Ignore it here so Terraform doesn't revert deploys back to the placeholder.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}
