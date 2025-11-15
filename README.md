# Frame.io Webhook Receiver for GCP Cloud Run

A FastAPI application that receives Frame.io webhooks and logs payloads to stdout for easy inspection via GCP Cloud Run logs.

## Features

- FastAPI endpoint at `/api/v1/frameio/webhook` to receive Frame.io webhooks
- Logs complete webhook payloads (headers + body) to stdout
- Docker containerized with Multi-Stage Builds for optimal image size
- Ready to deploy on GCP Cloud Run
- Single-click CD via GitHub Actions
- Health check endpoints for monitoring

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

### 1. GCP Setup

1. **Create or select a GCP project:**
   ```bash
   gcloud projects create your-project-id
   gcloud config set project your-project-id
   ```

2. **Enable required APIs:**
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

3. **Create a service account for GitHub Actions:**
   ```bash
   gcloud iam service-accounts create github-actions \
       --display-name="GitHub Actions"
   ```

4. **Grant necessary permissions:**
   ```bash
   gcloud projects add-iam-policy-binding your-project-id \
       --member="serviceAccount:github-actions@your-project-id.iam.gserviceaccount.com" \
       --role="roles/run.admin"

   gcloud projects add-iam-policy-binding your-project-id \
       --member="serviceAccount:github-actions@your-project-id.iam.gserviceaccount.com" \
       --role="roles/storage.admin"

   gcloud projects add-iam-policy-binding your-project-id \
       --member="serviceAccount:github-actions@your-project-id.iam.gserviceaccount.com" \
       --role="roles/iam.serviceAccountUser"
   ```

5. **Create and download service account key:**
   ```bash
   gcloud iam service-accounts keys create key.json \
       --iam-account=github-actions@your-project-id.iam.gserviceaccount.com
   ```

### 2. GitHub Setup

1. **Add GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `GCP_PROJECT_ID`: Your GCP project ID
     - `GCP_SA_KEY`: Contents of the `key.json` file (entire JSON)

2. **Configure the workflow (if needed):**
   - Edit `.github/workflows/deploy.yml` if you want to change:
     - Region (default: `us-central1`)
     - Service name (default: `frameio-webhook`)
     - Memory/CPU allocations

### 3. Deploy

#### Option 1: Single-Click Deploy (GitHub Actions)

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "Deploy to Cloud Run" workflow
4. Click "Run workflow" → "Run workflow"
5. Wait for deployment to complete
6. The service URL will be displayed in the workflow logs

#### Option 2: Manual Deploy with gcloud

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Or deploy directly
gcloud run deploy frameio-webhook \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

#### Option 3: Local Docker Build and Deploy

```bash
# Build the image
docker build -t gcr.io/your-project-id/frameio-webhook:latest .

# Push to GCR
docker push gcr.io/your-project-id/frameio-webhook:latest

# Deploy to Cloud Run
gcloud run deploy frameio-webhook \
    --image gcr.io/your-project-id/frameio-webhook:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

## Configure Frame.io Webhook

1. Get your Cloud Run service URL:
   ```bash
   gcloud run services describe frameio-webhook \
       --platform managed \
       --region us-central1 \
       --format 'value(status.url)'
   ```

2. In Frame.io:
   - Go to your project settings
   - Navigate to Webhooks
   - Add a new webhook with URL: `https://your-service-url.run.app/api/v1/frameio/webhook`
   - Select events you want to receive (e.g., "asset.created" for new files)

## Viewing Logs and Webhook Payloads

### Method 1: GCP Console (Web UI)

1. Go to [GCP Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Run** → Select `frameio-webhook` service
3. Click on **LOGS** tab
4. You'll see webhook payloads logged in this format:
   ```
   ================================================================================
   FRAME.IO WEBHOOK RECEIVED
   ================================================================================
   Timestamp: 2024-01-15T10:30:45.123456
   Client IP: xxx.xxx.xxx.xxx
   --------------------------------------------------------------------------------
   HEADERS:
   {
     "content-type": "application/json",
     ...
   }
   --------------------------------------------------------------------------------
   PAYLOAD:
   {
     "event": "asset.created",
     "data": {...}
   }
   ================================================================================
   ```

### Method 2: gcloud CLI

**View recent logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=frameio-webhook" \
    --limit 50 \
    --format=json
```

**Stream logs in real-time:**
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=frameio-webhook"
```

**Filter for webhook-specific logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=frameio-webhook AND textPayload=~'FRAME.IO WEBHOOK RECEIVED'" \
    --limit 10 \
    --format=json
```

**View logs from the last hour:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=frameio-webhook" \
    --freshness=1h
```

### Method 3: Cloud Logging Explorer (Advanced)

1. Go to [Cloud Logging](https://console.cloud.google.com/logs)
2. Use the query builder with this query:
   ```
   resource.type="cloud_run_revision"
   resource.labels.service_name="frameio-webhook"
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
gcloud logging sinks create frameio-webhooks-sink \
    bigquery.googleapis.com/projects/your-project-id/datasets/webhook_logs \
    --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="frameio-webhook"'
```

## Testing

### Test the health endpoint:
```bash
curl https://your-service-url.run.app/health
```

### Test the webhook endpoint locally:
```bash
# Run locally
docker build -t frameio-webhook .
docker run -p 8080:8080 frameio-webhook

# Send test webhook
curl -X POST http://localhost:8080/api/v1/frameio/webhook \
    -H "Content-Type: application/json" \
    -d '{"event": "asset.created", "test": true}'
```

### Test the deployed webhook:
```bash
curl -X POST https://your-service-url.run.app/api/v1/frameio/webhook \
    -H "Content-Type: application/json" \
    -d '{"event": "asset.created", "test": true}'
```

## Monitoring

### View Service Status:
```bash
gcloud run services describe frameio-webhook \
    --platform managed \
    --region us-central1
```

### Check Metrics:
- Go to Cloud Run → frameio-webhook → METRICS
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
│       └── deploy.yml          # GitHub Actions CD workflow
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Multi-stage Docker build
├── .dockerignore               # Docker build exclusions
├── cloudbuild.yaml             # GCP Cloud Build config
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

- The service is deployed with `--allow-unauthenticated` for webhook reception
- Consider implementing webhook signature verification for production use
- Review and restrict service account permissions as needed
- Use Secret Manager for sensitive configuration
- Implement rate limiting if needed

## Cost Optimization

- Cloud Run charges only for actual request processing time
- First 2 million requests per month are free
- 512Mi memory and 1 CPU should handle most webhook workloads
- Max instances set to 10 to prevent runaway costs

## License

MIT

## Support

For issues or questions:
- Check GCP Cloud Run documentation
- Review Frame.io webhook documentation
- Check application logs in Cloud Logging