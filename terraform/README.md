# Terraform Configuration for Frame.io Webhook GCP Setup

This Terraform configuration automates the GCP infrastructure setup for the Frame.io webhook receiver.

## What This Creates

- **Enables GCP APIs:**
  - Cloud Run API
  - Cloud Build API
  - Container Registry API
  - Artifact Registry API
  - IAM API

- **Service Account:**
  - Creates `github-actions` service account
  - Grants necessary IAM roles:
    - `roles/run.admin` - Deploy to Cloud Run
    - `roles/storage.admin` - Push images to GCR
    - `roles/iam.serviceAccountUser` - Act as service accounts
  - Generates service account key for GitHub Actions

## Prerequisites

1. **GCP Project:**
   - Existing GCP project with billing enabled
   - Project ID ready

2. **Terraform:**
   - Terraform >= 1.0 installed
   - Install from: https://www.terraform.io/downloads

3. **GCP Authentication:**
   - `gcloud` CLI installed and authenticated
   - Or use service account credentials

## Quick Start

### Step 1: Authenticate with GCP

```bash
gcloud auth application-default login
```

### Step 2: Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
project_id = "your-actual-project-id"
region     = "us-central1"
```

### Step 3: Initialize Terraform

```bash
terraform init
```

### Step 4: Plan and Apply

```bash
# Review what will be created
terraform plan

# Create the infrastructure
terraform apply
```

Type `yes` when prompted.

### Step 5: Get Service Account Key for GitHub

```bash
# Save the key to a file
terraform output -raw github_actions_service_account_key | base64 -d > key.json

# Display the key content (to copy to GitHub Secrets)
cat key.json
```

### Step 6: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets → Actions and add:

- **`GCP_PROJECT_ID`**: Your GCP project ID (from `terraform.tfvars`)
- **`GCP_SA_KEY`**: Contents of `key.json` (entire JSON file)

**IMPORTANT:** Delete `key.json` after adding to GitHub:
```bash
rm key.json
```

## Terraform Commands

### View Outputs

```bash
# All outputs
terraform output

# Specific output
terraform output github_actions_service_account_email

# Get service account key (sensitive)
terraform output -raw github_actions_service_account_key | base64 -d
```

### Update Infrastructure

```bash
# After modifying .tf files
terraform plan
terraform apply
```

### Destroy Infrastructure

```bash
# WARNING: This will delete all created resources
terraform destroy
```

## Optional: Manage Cloud Run Service with Terraform

By default, the Cloud Run service is deployed via GitHub Actions. If you want Terraform to manage it:

1. Edit `main.tf`
2. Uncomment the `google_cloud_run_service` resource
3. Uncomment the `google_cloud_run_service_iam_member` resource
4. Uncomment the `service_url` output in `outputs.tf`
5. Run `terraform apply`

## File Structure

```
terraform/
├── main.tf                      # Main Terraform configuration
├── variables.tf                 # Input variables
├── outputs.tf                   # Output values
├── terraform.tfvars.example     # Example variables file
├── terraform.tfvars             # Your actual variables (gitignored)
└── README.md                    # This file
```

## Security Best Practices

1. **Never commit sensitive files:**
   - `terraform.tfvars` - Contains your project ID
   - `key.json` - Contains service account credentials
   - `terraform.tfstate` - May contain sensitive data
   - `.terraform/` - Provider plugins

2. **Use remote state** (for team environments):
   ```hcl
   terraform {
     backend "gcs" {
       bucket = "your-terraform-state-bucket"
       prefix = "frameio-webhook"
     }
   }
   ```

3. **Rotate service account keys** periodically

4. **Use least privilege** - Only grant necessary permissions

## Troubleshooting

### "API not enabled" errors

Wait a few moments after running `terraform apply`. API enablement can take 1-2 minutes to propagate.

### "Permission denied" errors

Ensure your GCP account has the necessary permissions:
- `roles/serviceusage.serviceUsageAdmin` - Enable APIs
- `roles/iam.serviceAccountAdmin` - Create service accounts
- `roles/resourcemanager.projectIamAdmin` - Grant IAM roles

### State file conflicts

If working in a team, use remote state storage (GCS backend) to avoid conflicts.

## Cost

The resources created by this Terraform configuration have minimal cost:
- Service account: **Free**
- API enablement: **Free**
- Storage for service account keys: **Negligible**

The actual costs come from Cloud Run usage (see main README.md).

## Next Steps

After running Terraform:

1. Configure GitHub Secrets (Step 6 above)
2. Deploy the application using GitHub Actions
3. Configure Frame.io webhook (see main README.md)

## Support

For Terraform-specific issues:
- [Terraform GCP Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCP Cloud Run Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_service)
