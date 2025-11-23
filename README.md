# Frame.io Webhook Receiver for GCP Cloud Run

A FastAPI application that receives Frame.io webhooks, publishes events to Pub/Sub, and logs payloads for monitoring via Cloud Logging.

## Features

- **Webhook Reception**: FastAPI endpoint at `/api/v1/frameio/webhook` for Frame.io V4 webhooks
- **Event Publishing**: Publishes webhook events to Google Cloud Pub/Sub for downstream processing
- **Structured Logging**: Logs complete webhook payloads with structured JSON for Cloud Logging
- **Hexagonal Architecture**: Clean separation between API, domain logic, and infrastructure
- **Local Development**: Docker Compose setup with Pub/Sub emulator
- **Production Ready**: Deployed on GCP Cloud Run with blue-green deployment
- **Well Tested**: 27 tests with 88% code coverage
- **CI/CD**: GitHub Actions for automated testing and deployment

## Architecture

```
Frame.io → Webhook → Cloud Run Service → Pub/Sub Topic → Subscribers
                              ↓
                        Cloud Logging
```

**Hexagonal Architecture:**
- `app/core/` - Domain models and business logic
- `app/api/` - HTTP endpoints (FastAPI)
- `app/infrastructure/` - Pub/Sub publisher implementation

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
     - `FIREBASE_WEB_API_KEY`: Firebase Web API key (for magic link auth)
     - `SESSION_SECRET_KEY`: Secure random string for session encryption
     - `ADOBE_CLIENT_ID`: Adobe OAuth client ID (for Frame.io integration)
     - `ADOBE_CLIENT_SECRET`: Adobe OAuth client secret

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
   - **Step 1:** Deploy new revision with no traffic (tagged with commit SHA)
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

**Install dependencies and run tests:**
```bash
pip install -r requirements-dev.txt
pytest  # 27 tests, 88% coverage
```

**With coverage report:**
```bash
pytest --cov=app --cov-report=term-missing
```

**Run specific test files:**
```bash
pytest tests/test_webhook.py      # Webhook endpoint tests
pytest tests/test_pubsub_integration.py  # Pub/Sub tests
```

### Continuous Integration

Tests run automatically via GitHub Actions on:
- Every push to any branch
- Every pull request
- Manual workflow dispatch

See `.github/workflows/test.yml` for CI configuration and `tests/README.md` for detailed testing documentation.

### Local Development

**Option 1: Run with Docker Compose (Recommended)**

Runs the app with Pub/Sub and Firebase Auth emulators for full local testing:

```bash
docker-compose up
```

This starts:
- Pub/Sub emulator on port 8085
- Firebase Auth emulator on port 9099 (UI at http://localhost:4000)
- Cambridge app on `http://localhost:8080`
- Auto-creates topic (`frameio-events`) and debug subscription (`frameio-events-debug-sub`)

**Test magic link authentication:**
```bash
curl -X POST http://localhost:8080/auth/magic/send \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
# Copy magic link from logs, paste in browser → redirects to /dashboard
```

**Test the webhook:**
```bash
curl -X POST http://localhost:8080/api/v1/frameio/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "file.created",
    "resource": {"id": "test-123", "type": "file"},
    "account": {"id": "acc-123"},
    "workspace": {"id": "ws-123"},
    "project": {"id": "proj-123"},
    "user": {"id": "user-123"}
  }'
```

**Pull Pub/Sub messages (local):**
```bash
python scripts/pull-pubsub-messages.py
```

**Pull Pub/Sub messages (production):**
```bash
gcloud pubsub subscriptions pull frameio-events-debug-sub --limit=10 --auto-ack
```

**Option 2: Run directly with Python**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export GCP_PROJECT_ID=test-project
   export PUBSUB_TOPIC_NAME=frameio-events
   ```

3. **Run the application:**
   ```bash
   python app/main.py
   ```

**Option 3: Run with Docker**

```bash
docker build -t cambridge .
docker run -p 8080:8080 \
  -e GCP_PROJECT_ID=test-project \
  -e PUBSUB_TOPIC_NAME=frameio-events \
  cambridge
```

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

## Magic Link Authentication

The application includes a self-contained magic link authentication system using Firebase. This allows developers to authenticate entirely through the backend without any frontend code.

### Prerequisites

1. **Firebase Project**: Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. **Enable Email Link Sign-In**:
   - Go to Firebase Console → Authentication → Sign-in method
   - Enable "Email/Password" provider
   - Enable "Email link (passwordless sign-in)"
3. **Firebase Service Account**: Ensure your GCP project has the Firebase Admin SDK service account configured
4. **Authorized Domains**: Add your callback domain to Firebase → Authentication → Settings → Authorized domains

### Required Environment Variables

```bash
# Firebase Web API Key (from Firebase Console → Project Settings → General)
FIREBASE_WEB_API_KEY=your-firebase-web-api-key

# Base URL where the service is running
BASE_URL=http://localhost:8080  # For local development
# BASE_URL=https://your-service.run.app  # For production
```

### Authentication Flow

1. **Generate Magic Link**: Call `POST /auth/magic/send` with your email
2. **Copy Link from Logs**: The magic link appears in server logs
3. **Click Link**: Paste the link in your browser
4. **Automatic Redirect**: You're redirected to `/dashboard` with a session cookie

### API Endpoints

#### POST /auth/magic/send - Generate Magic Link

Request a magic link for email authentication.

```bash
curl -X POST http://localhost:8080/auth/magic/send \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'
```

Response:
```json
{
  "status": "success",
  "message": "Magic link generated - check server logs"
}
```

**Important**: Check the server logs/console for the actual magic link URL.

#### GET /auth/magic/callback - Magic Link Callback

This endpoint is called automatically when the user clicks the magic link. It:
1. Exchanges the Firebase oobCode for an ID token
2. Creates a session cookie
3. Redirects to `/dashboard`

#### GET /dashboard - Protected Resource

A protected endpoint that requires authentication.

```bash
# Without authentication:
curl http://localhost:8080/dashboard
# Returns: 401 Unauthorized

# With session cookie (after magic link authentication):
curl http://localhost:8080/dashboard -b "session=<session-cookie>"
# Returns: {"status": "success", "message": "Welcome, you are authenticated!", ...}
```

### Local Development (Docker Compose)

Docker Compose includes Firebase Auth Emulator - no configuration needed:

```bash
docker-compose up
curl -X POST http://localhost:8080/auth/magic/send \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
# Copy magic link from logs, paste in browser → /dashboard
```

Firebase Emulator UI available at http://localhost:4000

### Production Setup

Set environment variables:
- `FIREBASE_WEB_API_KEY` - From Firebase Console
- `BASE_URL` - Your service URL (e.g., `https://your-service.run.app`)

Add callback domain to Firebase → Authentication → Settings → Authorized domains

## Adobe OAuth (Frame.io Integration)

The application supports Adobe OAuth2 for connecting Frame.io accounts. Once connected, users can use their tokens to interact with the Frame.io V4 API.

### Prerequisites

1. **Adobe Developer Console Project**: Create a project at [Adobe Developer Console](https://developer.adobe.com/console/)
2. **OAuth Server-to-Server or OAuth Web App credentials**:
   - Go to your project → Add API → "Frame.io API"
   - Choose OAuth Web App credentials
   - Configure redirect URI: `https://your-service.run.app/oauth/adobe/callback`

### Required Environment Variables

```bash
# Adobe OAuth2 credentials (from Adobe Developer Console)
ADOBE_CLIENT_ID=your-adobe-client-id
ADOBE_CLIENT_SECRET=your-adobe-client-secret

# Base URL where the service is running
BASE_URL=http://localhost:8080  # For local development
# BASE_URL=https://your-service.run.app  # For production

# Session secret for OAuth state (required)
SESSION_SECRET_KEY=your-secure-random-string
```

### OAuth Scopes

The application requests the following scopes:
- `openid` - OpenID Connect
- `frame.io.read` - Read access to Frame.io
- `frame.io.write` - Write access to Frame.io

### Authentication Flow

1. **Authenticate with Magic Link**: User must first be authenticated via magic link
2. **Connect Adobe Account**: Navigate to `/oauth/adobe/connect`
3. **Adobe Consent**: User is redirected to Adobe to grant permissions
4. **Token Storage**: Tokens are stored and associated with the user
5. **Use Frame.io V4 API**: Use the stored tokens to call Frame.io V4 API

### API Endpoints

#### GET /oauth/adobe/connect - Start OAuth Flow

Initiates the Adobe OAuth2 flow. Requires authenticated session.

```bash
# User must be authenticated first (via magic link)
# Then navigate to this URL in browser:
https://your-service.run.app/oauth/adobe/connect
```

#### GET /oauth/adobe/callback - OAuth Callback

Handles the OAuth callback from Adobe. This endpoint:
1. Exchanges the authorization code for tokens
2. Stores tokens in the user repository
3. Redirects to `/dashboard?connected=adobe`

#### GET /oauth/connections - List Connected Services

Returns list of connected OAuth providers for the current user.

```bash
curl http://localhost:8080/oauth/connections -b "session=<session-cookie>"
```

Response:
```json
{
  "connections": ["adobe"]
}
```

#### DELETE /oauth/adobe - Disconnect Adobe Account

Removes the Adobe OAuth tokens for the current user.

```bash
curl -X DELETE http://localhost:8080/oauth/adobe -b "session=<session-cookie>"
```

### Using Frame.io V4 API

After connecting Adobe, retrieve the stored token and use it with the Frame.io V4 API:

```python
# Example: Get token from repository and call Frame.io V4 API
token = await repository.get_token(user_uid, "adobe")

import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.frame.io/v4/me",
        headers={"Authorization": f"Bearer {token.access_token}"}
    )
    user_info = response.json()
```

### Local Development

For local development with Docker Compose:

```bash
# Set environment variables in docker-compose.yml or .env file
ADOBE_CLIENT_ID=your-adobe-client-id
ADOBE_CLIENT_SECRET=your-adobe-client-secret

docker-compose up
```

Then:
1. Authenticate via magic link: `POST /auth/magic/send`
2. Connect Adobe: Navigate to `http://localhost:8080/oauth/adobe/connect`

**Note**: For local development, you need to configure your Adobe app's redirect URI to `http://localhost:8080/oauth/adobe/callback`.

### Production Setup

1. Set environment variables in Cloud Run:
   - `ADOBE_CLIENT_ID`
   - `ADOBE_CLIENT_SECRET`
   - `BASE_URL` (your Cloud Run service URL)
   - `SESSION_SECRET_KEY` (secure random string)

2. Configure Adobe Developer Console:
   - Add redirect URI: `https://your-service.run.app/oauth/adobe/callback`

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
