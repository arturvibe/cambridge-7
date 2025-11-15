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

resource "google_project_service" "cloud_build" {
  project = var.project_id
  service = "cloudbuild.googleapis.com"

  disable_on_destroy = false
}

resource "google_project_service" "container_registry" {
  project = var.project_id
  service = "containerregistry.googleapis.com"

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

resource "google_project_iam_member" "github_actions_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
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
    google_project_iam_member.github_actions_storage_admin,
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
#         image = "gcr.io/${var.project_id}/${var.service_name}:latest"
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
#   depends_on = [google_project_service.cloud_run]
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
