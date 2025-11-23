# 1. Artifact Registry Repository
import {
  to = google_artifact_registry_repository.docker_repo
  id = "projects/${var.project_id}/locations/${var.region}/repositories/${var.artifact_registry_repo_name}"
}

# 2. Pub/Sub Topic
import {
  to = google_pubsub_topic.frameio_webhooks
  id = "projects/${var.project_id}/topics/${var.pubsub_topic_name}"
}

# 3. Cloud Run Service Account
import {
  to = google_service_account.cloud_run
  id = "projects/${var.project_id}/serviceAccounts/${var.cloud_run_sa_name}@${var.project_id}.iam.gserviceaccount.com"
}

# 4. GitHub Actions Service Account
import {
  to = google_service_account.github_actions
  id = "projects/${var.project_id}/serviceAccounts/${var.github_actions_sa_name}@${var.project_id}.iam.gserviceaccount.com"
}

# 5. Pub/Sub Subscription (Debug)
import {
  to = google_pubsub_subscription.frameio_webhooks_debug_sub
  # Format: projects/{{project}}/subscriptions/{{subscription_name}}
  # Based on your code: name = "${var.pubsub_topic_name}-debug-sub"
  id = "projects/${var.project_id}/subscriptions/${var.pubsub_topic_name}-debug-sub"
}
