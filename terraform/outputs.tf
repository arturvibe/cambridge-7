output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "github_actions_service_account_email" {
  description = "Email of the GitHub Actions service account"
  value       = google_service_account.github_actions.email
}

output "github_actions_service_account_key" {
  description = "Service account key for GitHub Actions (base64 encoded)"
  value       = google_service_account_key.github_actions_key.private_key
  sensitive   = true
}

output "github_actions_service_account_key_decoded" {
  description = "Instructions for decoding the service account key"
  value       = "Run: terraform output -raw github_actions_service_account_key | base64 -d > key.json"
}

output "enabled_apis" {
  description = "List of enabled GCP APIs"
  value = [
    google_project_service.cloud_run.service,
    google_project_service.artifact_registry.service,
    google_project_service.iam.service,
    google_project_service.pubsub.service,
    google_project_service.firebase.service,
    google_project_service.identity_toolkit.service,
  ]
}

output "firebase_web_app_id" {
  description = "Firebase Web App ID"
  value       = google_firebase_web_app.cambridge.app_id
}

output "firebase_web_api_key" {
  description = "Firebase Web API Key for authentication"
  value       = data.google_firebase_web_app_config.cambridge.api_key
  sensitive   = true
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.docker_repo.name
}

output "artifact_registry_repository_url" {
  description = "Artifact Registry repository URL for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo_name}"
}

output "docker_image_base_url" {
  description = "Base URL for Docker images (use this in your CI/CD)"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo_name}/${var.service_name}"
}

output "pubsub_topic_name" {
  description = "Name of the Pub/Sub topic for Frame.io webhooks"
  value       = google_pubsub_topic.frameio_webhooks.name
}

output "pubsub_subscription_name" {
  description = "Name of the Pub/Sub subscription for debugging/testing"
  value       = google_pubsub_subscription.frameio_webhooks_debug_sub.name
}

output "cloud_run_service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run.email
}

# Uncomment if managing Cloud Run service with Terraform
# output "service_url" {
#   description = "URL of the deployed Cloud Run service"
#   value       = google_cloud_run_service.frameio_webhook.status[0].url
# }
