terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "cloud_run" {
  project = var.project_id
  service = "run.googleapis.com"

  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"

  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  project = var.project_id
  service = "iam.googleapis.com"

  disable_on_destroy = false
}

# Create Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = var.artifact_registry_repo_name
  description   = "Docker repository for cambridge application"
  format        = "DOCKER"
  project       = var.project_id

  depends_on = [google_project_service.artifact_registry]

  cleanup_policies {
    id     = "keep-latest-seven"
    action = "KEEP"
    most_recent_versions {
      keep_count = 7
    }
  }

  cleanup_policies {
    id     = "keep-deployed"
    action = "KEEP"
    condition {
      tag_state    = "TAGGED"
      tag_prefixes = ["deployed"]
    }
  }

  cleanup_policies {
    id     = "delete-untagged-and-non-deployed"
    action = "DELETE"
    condition {
      older_than = "0s"
    }
  }
}

# Service account for GitHub Actions
resource "google_service_account" "github_actions" {
  account_id   = var.github_actions_sa_name
  display_name = "GitHub Actions Service Account"
  description  = "Service account used by GitHub Actions to deploy to Cloud Run"
  project      = var.project_id

  depends_on = [google_project_service.iam]
}

# IAM roles for GitHub Actions service account
resource "google_project_iam_member" "github_actions_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"

  depends_on = [google_service_account.github_actions]
}

resource "google_project_iam_member" "github_actions_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"

  depends_on = [google_service_account.github_actions]
}

resource "google_project_iam_member" "github_actions_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"

  depends_on = [google_service_account.github_actions]
}

# Create service account key for GitHub Actions
resource "google_service_account_key" "github_actions_key" {
  service_account_id = google_service_account.github_actions.name

  depends_on = [
    google_project_iam_member.github_actions_run_admin,
    google_project_iam_member.github_actions_artifact_registry_writer,
    google_project_iam_member.github_actions_service_account_user
  ]
}

# Optional: Cloud Run service (can be deployed via GitHub Actions instead)
# Uncomment if you want Terraform to manage the Cloud Run service
# resource "google_cloud_run_service" "frameio_webhook" {
#   name     = var.service_name
#   location = var.region
#   project  = var.project_id
#
#   template {
#     spec {
#       containers {
#         image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo_name}/${var.service_name}:latest"
#
#         ports {
#           container_port = 8080
#         }
#
#         resources {
#           limits = {
#             memory = "512Mi"
#             cpu    = "1"
#           }
#         }
#       }
#
#       container_concurrency = 80
#       timeout_seconds      = 60
#     }
#
#     metadata {
#       annotations = {
#         "autoscaling.knative.dev/maxScale" = "1"
#       }
#     }
#   }
#
#   traffic {
#     percent         = 100
#     latest_revision = true
#   }
#
#   depends_on = [
#     google_project_service.cloud_run,
#     google_artifact_registry_repository.docker_repo
#   ]
# }
#
# # Allow unauthenticated access to Cloud Run service
# resource "google_cloud_run_service_iam_member" "public_access" {
#   service  = google_cloud_run_service.frameio_webhook.name
#   location = google_cloud_run_service.frameio_webhook.location
#   project  = var.project_id
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }
