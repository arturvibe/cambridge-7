variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "europe-west1"
}

variable "github_actions_sa_name" {
  description = "Service account name for GitHub Actions"
  type        = string
  default     = "github-actions"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "cambridge"
}

variable "artifact_registry_repo_name" {
  description = "Artifact Registry repository name for Docker images"
  type        = string
  default     = "cambridge-repo"
}

variable "pubsub_topic_name" {
  description = "Pub/Sub topic name for Frame.io events"
  type        = string
  default     = "frameio-events"
}

variable "cloud_run_sa_name" {
  description = "Service account name for Cloud Run"
  type        = string
  default     = "cambridge-cloud-run"
}

variable "cloud_run_domain" {
  description = "Cloud Run service domain (e.g., cambridge-abc123-ew.a.run.app)"
  type        = string
}
