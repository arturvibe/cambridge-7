# Frame.io Webhook Receiver for GCP Cloud Run

A FastAPI application that receives Frame.io webhooks and logs payloads to stdout for easy inspection via GCP Cloud Run logs.

## Features

- FastAPI endpoint at `/api/v1/frameio/webhook` to receive Frame.io V4 webhooks
- Parses and logs Frame.io-specific payload structure (event type, resource details, account/workspace/project IDs)
- Logs complete webhook payloads (headers + body) to stdout
- Docker containerized with Multi-Stage Builds for optimal image size
- Ready to deploy on GCP Cloud Run
- Single-click CD via GitHub Actions
- Health check endpoints for monitoring
- Comprehensive unit tests with 90% code coverage
- Conventional Commits enforcement via CI

## Architecture

```
Frame.io → Webhook → Cloud Run Service → Logs to stdout → Cloud Logging
```

## Prerequisites

- Google Cloud Platform account
- GCP Project with billing enabled
- GitHub repository
- Frame.io account for configuring webhooks

## Setup

### 1. GCP Setup with Terraform

Terraform automates all GCP infrastructure setup.

1. **Install gcloud CLI:**

   ```bash
   brew install --cask google-cloud-sdk
   ```

   Verify installation:
   ```bash
   gcloud --version
   ```

2. **Install Terraform:**

   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   ```

   Verify installation:
   ```bash
   terraform --version
   ```

3. **Authenticate with GCP:**
   ```bash
   gcloud auth application-default login
   ```

4. **Configure Terraform:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

   Edit `terraform.tfvars`:
   ```hcl
   project_id = "your-gcp-project-id"
   region     = "europe-west1"
   ```

5. **Run Terraform:**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

6. **Get service account key:**
   ```bash
   terraform output -raw github_actions_service_account_key | base64 -d > key.json
   ```

See [terraform/README.md](terraform/README.md) for detailed Terraform documentation.

### 2. GitHub Setup

1. **Add GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `GCP_PROJECT_ID`: Your GCP project ID
     - `GCP_SA_KEY`: Contents of the `key.json` file (entire JSON)

2. **Configure the workflow (if needed):**
   - Edit `.github/workflows/deploy.yml` if you want to change:
     - Region (default: `europe-west1`)
     - Service name (default: `cambridge`)
     - Memory/CPU allocations

### 3. Deploy via GitHub Actions

The deployment uses a **blue-green deployment strategy** for zero-downtime deployments:

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "Deploy to Cloud Run" workflow
4. Click "Run workflow" → "Run workflow"
5. The workflow will:
   - **Step 1:** Deploy new revision with no traffic (tagged as 'blue')
   - **Step 2:** Validate the `/health` endpoint (5 retries, 3s intervals)
   - **Step 3:** If validation passes, migrate 100% traffic to the new revision
   - **Rollback:** If validation fails, deployment aborts (old revision continues serving)
6. The service URL will be displayed in the workflow logs

## Configure Frame.io Webhook

### Step 1: Get your Cloud Run service URL

```bash
gcloud run services describe cambridge \
    --platform managed \
    --region europe-west1 \
    --format 'value(status.url)'
```

Save this URL - you'll need it for Frame.io configuration.

### Step 2: Create webhook in Frame.io

Using the Frame.io API, create a webhook subscription. You'll need:
- OAuth 2.0 access token (from Adobe Developer Console)
- Account ID and Workspace ID

**Example API call using curl:**

```bash
curl -X POST \
  https://api.frame.io/v4/accounts/{account_id}/workspaces/{workspace_id}/webhooks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "Cloud Run Webhook Receiver",
      "url": "https://your-service-url.run.app/api/v1/frameio/webhook",
      "events": [
        "file.created",
        "file.ready",
        "file.upload.completed",
        "comment.created"
      ]
    }
  }'
```

### Step 3: Test the webhook

Send a test webhook or trigger an event in Frame.io (e.g., upload a file) and check the logs to verify it's working.

## Viewing Logs and Webhook Payloads

### Method 1: GCP Console (Web UI)

1. Go to [GCP Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Run** → Select `cambridge` service
3. Click on **LOGS** tab
4. You'll see webhook payloads logged in this format:
   ```
   ================================================================================
   FRAME.IO WEBHOOK RECEIVED
   ================================================================================
   Event Type: file.created
   Resource Type: file
   Resource ID: d3075547-4e64-45f0-ad12-d075660eddd2
   Account ID: 6f70f1bd-7e89-4a7e-b4d3-7e576585a181
   Workspace ID: 378fcbf7-6f88-4224-8139-6a743ed940b2
   Project ID: 7e46e495-4444-4555-8649-bee4d391a997
   User ID: 56556a3f-859f-4b38-b6c6-e8625b5da8a5
   User Agent: Frame.io V4 API
   Timestamp: 2024-01-15T10:30:45.123456
   Client IP: xxx.xxx.xxx.xxx
   --------------------------------------------------------------------------------
   HEADERS:
   {
     "user-agent": "Frame.io V4 API",
     "content-type": "application/json",
     ...
   }
   --------------------------------------------------------------------------------
   FULL PAYLOAD:
   {
     "type": "file.created",
     "resource": {
       "id": "d3075547-4e64-45f0-ad12-d075660eddd2",
       "type": "file"
     },
     "account": {"id": "6f70f1bd-7e89-4a7e-b4d3-7e576585a181"},
     "workspace": {"id": "378fcbf7-6f88-4224-8139-6a743ed940b2"},
     "project": {"id": "7e46e495-4444-4555-8649-bee4d391a997"},
     "user": {"id": "56556a3f-859f-4b38-b6c6-e8625b5da8a5"}
   }
   ================================================================================
   ```

### Method 2: gcloud CLI

**View recent logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge" \
    --limit 50 \
    --format=json
```

**Stream logs in real-time:**
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge"
```

**Filter for webhook-specific logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge AND textPayload=~'FRAME.IO WEBHOOK RECEIVED'" \
    --limit 10 \
    --format=json
```

**View logs from the last hour:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge" \
    --freshness=1h
```

### Method 3: Cloud Logging Explorer (Advanced)

1. Go to [Cloud Logging](https://console.cloud.google.com/logs)
2. Use the query builder with this query:
   ```
   resource.type="cloud_run_revision"
   resource.labels.service_name="cambridge"
   textPayload=~"WEBHOOK"
   ```
3. Adjust time range as needed
4. Export logs if needed (JSON, CSV, etc.)

### Method 4: Using Log Router (For Production)

Set up log sinks to export webhook data to:
- **BigQuery** for analysis
- **Cloud Storage** for archival
- **Pub/Sub** for real-time processing

Example: Export to BigQuery
```bash
gcloud logging sinks create cambridges-sink \
    bigquery.googleapis.com/projects/your-project-id/datasets/webhook_logs \
    --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="cambridge"'
```

## Development

### Running Unit Tests

The application includes a comprehensive test suite with 90% code coverage.

**Install development dependencies:**
```bash
pip install -r requirements-dev.txt
```

**Run all tests:**
```bash
pytest
```

**Run tests with coverage report:**
```bash
pytest --cov=app --cov-report=term-missing
```

**Run tests with HTML coverage report:**
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in your browser
```

**Run specific tests:**
```bash
# Run tests for health endpoints
pytest tests/test_main.py::TestHealthEndpoints

# Run tests for webhook functionality
pytest tests/test_main.py::TestFrameIOWebhook

# Run tests matching a keyword
pytest -k "webhook"
```

### Continuous Integration

Tests run automatically via GitHub Actions on:
- Every push to any branch
- Every pull request
- Manual workflow dispatch

See `.github/workflows/test.yml` for CI configuration and `tests/README.md` for detailed testing documentation.

### Local Development

**Option 1: Run directly with Python**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app/main.py
   ```

3. **The server starts at `http://localhost:8080`**

4. **Test the health endpoint:**
   ```bash
   curl http://localhost:8080/health
   # Expected: {"status":"healthy"}
   ```

5. **Test the webhook endpoint:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/frameio/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "file.created",
       "resource": {
         "id": "test-123",
         "type": "file"
       },
       "account": {"id": "acc-123"},
       "workspace": {"id": "ws-123"},
       "project": {"id": "proj-123"},
       "user": {"id": "user-123"}
     }'
   ```

   Check your terminal - you should see the webhook payload logged to stdout.

**Option 2: Run with Docker**

1. **Build the image:**
   ```bash
   docker build -t cambridge .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8080:8080 cambridge
   ```

3. **Test the endpoints** (same curl commands as above)

## Testing

### Testing Locally

See the "Local Development" section above for how to run and test the application locally.

### Testing the Deployed Service

**Test the health endpoint:**
```bash
curl https://your-service-url.run.app/health
```

**Test the webhook endpoint:**
```bash
curl -X POST https://your-service-url.run.app/api/v1/frameio/webhook \
  -H "Content-Type: application/json" \
  -H "User-Agent: Frame.io V4 API" \
  -d '{
    "type": "file.ready",
    "resource": {
      "id": "test-file-id",
      "type": "file"
    },
    "account": {"id": "test-account-id"},
    "workspace": {"id": "test-workspace-id"},
    "project": {"id": "test-project-id"},
    "user": {"id": "test-user-id"}
  }'
```

Then check the Cloud Run logs to see the webhook payload.

## Monitoring

### View Service Status:
```bash
gcloud run services describe cambridge \
    --platform managed \
    --region europe-west1
```

### Check Metrics:
- Go to Cloud Run → cambridge → METRICS
- View request count, latency, error rate, etc.

### Set up Alerts:
```bash
# Example: Alert on high error rate
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="Frameio Webhook High Error Rate" \
    --condition-display-name="Error rate > 5%" \
    --condition-threshold-value=0.05 \
    --condition-threshold-duration=60s
```

## Project Structure

```
.
├── .github/
│   └── workflows/
│       ├── deploy.yml          # GitHub Actions CD workflow
│       └── test.yml            # GitHub Actions test workflow
├── app/
│   └── main.py                 # FastAPI application
├── tests/
│   ├── __init__.py             # Test package marker
│   ├── test_main.py            # Unit tests for main application
│   └── README.md               # Testing documentation
├── terraform/
│   ├── main.tf                 # Terraform main configuration
│   ├── variables.tf            # Terraform input variables
│   ├── outputs.tf              # Terraform outputs
│   ├── terraform.tfvars.example # Example Terraform variables
│   └── README.md               # Terraform documentation
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development and testing dependencies
├── pytest.ini                   # Pytest configuration
├── Dockerfile                   # Multi-stage Docker build
├── .dockerignore               # Docker build exclusions
├── .gitignore                  # Git ignore rules
├── .commitlintrc.json          # Commitlint configuration
└── README.md                    # This file
```

## Troubleshooting

### Deployment fails:
- Check GitHub Actions logs for detailed error messages
- Verify GCP service account has correct permissions
- Ensure all required GCP APIs are enabled

### Webhooks not appearing in logs:
- Verify Frame.io webhook is configured correctly
- Check Cloud Run service is publicly accessible
- Test endpoint manually with curl
- Check Cloud Run logs for any errors

### Service not starting:
- Check Dockerfile and requirements.txt for errors
- Verify PORT environment variable is handled correctly
- Check Cloud Run logs for startup errors

## Security Considerations

- The service is deployed with `--allow-unauthenticated` for webhook reception (required for Frame.io to send webhooks)
- Review and restrict service account permissions as needed
- Consider implementing webhook signature verification for production use (Frame.io provides signing secrets)
- Consider additional rate limiting for production workloads
- Monitor logs for unexpected webhook sources or patterns

## Cost Optimization

- Cloud Run charges only for actual request processing time
- First 2 million requests per month are free
- 512Mi memory and 1 CPU should handle most webhook workloads
- **Max instances set to 1** to minimize costs (webhooks are processed sequentially)
- Service scales to zero when not receiving webhooks (no idle costs)

## License

MIT

## Support

For issues or questions:
- Check GCP Cloud Run documentation
- Review Frame.io webhook documentation
- Check application logs in Cloud Logging