# Terraform Configuration

GCP infrastructure for the Cambridge webhook receiver.

## Resources Created

**APIs:** Cloud Run, Artifact Registry, IAM, Pub/Sub, Firebase, Identity Toolkit

**Infrastructure:**
- Artifact Registry repository (Docker images, 7 version retention)
- Pub/Sub topic (`frameio-events`) and debug subscription
- Firebase project and Web App (for magic link auth)

**Service Accounts:**
- `github-actions` - CI/CD deployment (run.admin, artifactregistry.writer, iam.serviceAccountUser)
- `cambridge-cloud-run` - Cloud Run service (pubsub.publisher, firebaseauth.admin)

## Quick Start

```bash
# 1. Authenticate
gcloud auth application-default login

# 2. Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id

# 3. Apply
terraform init
terraform plan
terraform apply
```

## Outputs

```bash
# Service account key for GitHub Actions
terraform output -raw github_actions_service_account_key | base64 -d > key.json

# Firebase Web API key for Cloud Run
terraform output -raw firebase_web_api_key
```

## GitHub Secrets

Add these secrets to your repository:

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | Contents of `key.json` |
| `FIREBASE_WEB_API_KEY` | Output of `terraform output -raw firebase_web_api_key` |

**Delete `key.json` after copying to GitHub.**

## Files

```
terraform/
├── main.tf          # Resources
├── variables.tf     # Input variables
├── outputs.tf       # Output values
├── imports.tf       # Import existing resources
└── terraform.tfvars # Your config (gitignored)
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_id` | (required) | GCP Project ID |
| `region` | `europe-west1` | GCP region |
| `service_name` | `cambridge` | Cloud Run service name |
| `pubsub_topic_name` | `frameio-events` | Pub/Sub topic name |
| `cloud_run_domain` | (required) | Cloud Run domain for Firebase auth |

## Commands

```bash
terraform plan              # Preview changes
terraform apply             # Apply changes
terraform output            # View outputs
terraform destroy           # Remove all resources
```
