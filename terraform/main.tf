terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
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

resource "google_project_service" "pubsub" {
  project = var.project_id
  service = "pubsub.googleapis.com"

  disable_on_destroy = false
}

resource "google_project_service" "firebase" {
  project = var.project_id
  service = "firebase.googleapis.com"

  disable_on_destroy = false
}

resource "google_project_service" "identity_toolkit" {
  project = var.project_id
  service = "identitytoolkit.googleapis.com"

  disable_on_destroy = false
}

# Firebase project (links to existing GCP project)
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id

  depends_on = [google_project_service.firebase]
}

# Firebase Web App (provides Web API Key)
resource "google_firebase_web_app" "cambridge" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Cambridge Auth"

  depends_on = [google_firebase_project.default]
}

# Get Firebase Web App config (contains API key)
data "google_firebase_web_app_config" "cambridge" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.cambridge.app_id
}

# Create Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = var.artifact_registry_repo_name
  description   = "Docker repository for cambridge application"
  format        = "DOCKER"
  project       = var.project_id

  # Cleanup policy: keep 7 most recent versions
  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 7
    }
  }

  cleanup_policies {
    id     = "delete-old-versions"
    action = "DELETE"
    condition {
      tag_state = "ANY"
    }
  }

  depends_on = [google_project_service.artifact_registry]
}

# Pub/Sub topic for Frame.io webhooks
resource "google_pubsub_topic" "frameio_webhooks" {
  name    = var.pubsub_topic_name
  project = var.project_id

  labels = {
    application = "cambridge"
    purpose     = "frameio-webhooks"
  }

  depends_on = [google_project_service.pubsub]
}

# Pub/Sub subscription for testing and debugging
resource "google_pubsub_subscription" "frameio_webhooks_debug_sub" {
  name    = "${var.pubsub_topic_name}-debug-sub"
  topic   = google_pubsub_topic.frameio_webhooks.name
  project = var.project_id

  # Message retention duration (7 days)
  message_retention_duration = "604800s"

  # Acknowledgement deadline (10 seconds)
  ack_deadline_seconds = 10

  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Enable message ordering
  enable_message_ordering = false

  labels = {
    application = "cambridge"
    purpose     = "frameio-webhooks-debug"
  }

  depends_on = [google_pubsub_topic.frameio_webhooks]
}

# Service account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = var.cloud_run_sa_name
  display_name = "Cloud Run Service Account"
  description  = "Service account for Cloud Run (Pub/Sub publisher, Firebase Auth)"
  project      = var.project_id

  depends_on = [google_project_service.iam]
}

# IAM role for Cloud Run service account to publish to Pub/Sub
resource "google_pubsub_topic_iam_member" "cloud_run_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.frameio_webhooks.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"

  depends_on = [google_service_account.cloud_run]
}

# IAM role for Cloud Run service account to use Firebase Auth (magic links)
resource "google_project_iam_member" "cloud_run_firebase_auth" {
  project = var.project_id
  role    = "roles/firebaseauth.admin"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"

  depends_on = [google_service_account.cloud_run]
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
