variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "github_actions_sa_name" {
  description = "Service account name for GitHub Actions"
  type        = string
  default     = "github-actions"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "frameio-webhook"
}
