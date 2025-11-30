# AGENTS.md - AI Assistant Guide

FastAPI webhook receiver for Frame.io V4 → logs payloads to GCP Cloud Run → publishes to Pub/Sub → viewable via Cloud Logging.

**Stack:** Python 3.11 • FastAPI 0.109.0 • Pydantic v2 • google-cloud-logging • google-cloud-pubsub • firebase-admin • Docker • GCP Cloud Run • Terraform

**Flow:** `Frame.io → /api/v1/frameio/webhook → [Validate → Log → Publish to Pub/Sub] → Cloud Logging`

## Architecture

**Hexagonal Architecture (Ports & Adapters):**
```
┌─────────────────────────────────────────┐
│ Driving Adapters (app/api/)             │
│ - frameio.py: Webhook endpoint (dumb)   │
│ - magic.py: Auth endpoints (dumb)       │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Core Domain (app/core/)                 │
│ - domain.py: FrameIOEvent model         │
│ - services.py: Business logic (smart)   │
│ - ports.py: EventPublisher interface    │
│ - exceptions.py: Domain exceptions      │
├─────────────────────────────────────────┤
│ Auth Module (app/auth/)                 │
│ - config.py: Firebase configuration     │
│ - services.py: Auth business logic      │
│ - dependencies.py: Session validation   │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Driven Adapters (app/infrastructure/)   │
│ - pubsub_publisher.py: Pub/Sub impl     │
└─────────────────────────────────────────┘
```

**Separation of Concerns:**
- **Adapters** (API/Infrastructure): HTTP ↔ Python translation, serialization
- **Core Domain**: Pure business logic, domain models, ports (interfaces)
- **Exception Handling**: Centralized in `app/main.py` (no try-except in adapters!)

## Structure

**Core files:**
- `app/main.py` - FastAPI app wiring, dependency injection, centralized exception handlers, /dashboard endpoint
- `app/api/frameio.py` - Frame.io webhook endpoint (dumb adapter, delegates to service)
- `app/api/magic.py` - Magic link auth endpoints (dumb adapter, /auth/magic/send, /auth/magic/callback)
- `app/core/domain.py` - FrameIOEvent domain model (Pydantic v2)
- `app/core/services.py` - Business logic (logging, publishing, validation)
- `app/core/ports.py` - EventPublisher port (interface)
- `app/core/exceptions.py` - Domain exceptions (PublisherError, InvalidWebhookError)
- `app/auth/config.py` - Firebase Admin SDK configuration and initialization
- `app/auth/services.py` - Auth services (MagicLinkService, TokenExchangeService, SessionCookieService)
- `app/auth/dependencies.py` - FastAPI dependencies for session cookie validation
- `app/oauth/config.py` - OAuth2 provider registry (authlib configuration)
- `app/oauth/router.py` - OAuth2 endpoints (/oauth/{provider}/connect, /oauth/{provider}/callback)
- `app/oauth/dependencies.py` - OAuth FastAPI dependencies
- `app/users/models.py` - User and OAuthToken domain models
- `app/users/repository.py` - UserRepository interface + InMemoryUserRepository
- `app/integrations/google/` - Google service integration (Photos, Drive - future)
- `app/integrations/adobe/` - Adobe service integration (Frame.io, Creative Cloud - future)
- `app/infrastructure/pubsub_publisher.py` - Pub/Sub implementation
- `app/logging_config.py` - Logging configuration with Cloud Run detection
- `tests/test_webhook.py` - Webhook endpoint tests
- `tests/test_auth.py` - Magic link authentication tests
- `tests/test_pubsub_integration.py` - Pub/Sub integration tests
- `tests/test_pubsub_publisher.py` - Publisher unit tests (90%+ coverage)
- `tests/test_health.py` - Health endpoint tests
- `tests/test_security.py` - Security and edge case tests
- `tests/test_lifecycle.py` - Application lifecycle tests
- `Dockerfile` - Multi-stage build
- `.github/workflows/` - CI/CD (test, deploy)
- `terraform/` - GCP infrastructure as code (includes Pub/Sub topic/subscription)
- `docker-compose.yml` - Local dev environment with Pub/Sub emulator

## Development

```bash
# Setup
pip install -r requirements-dev.txt
pre-commit install  # Install git hooks for auto-formatting

# Run locally with Pub/Sub emulator (recommended)
docker-compose up  # Starts emulator, sets up topics, and runs app at http://localhost:8080

## Testing

This project has two test suites: unit tests and end-to-end (E2E) tests.

### Unit Tests

Unit tests mock external services and do not require any running dependencies. They can be run directly after installing dependencies:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all unit tests (ignores E2E tests)
pytest --cov=app --cov-report=term-missing --ignore=tests/e2e/
```

### End-to-End (E2E) Tests

E2E tests run against real emulators (Firebase Auth and Firestore) and require Docker. They are designed to be run from your local machine, connecting to the emulator services managed by Docker Compose.

**1. Start the Emulators:**

Start both Firebase Auth and Firestore emulators in the background.

```bash
docker-compose up -d firebase-emulator firestore-emulator
```

Wait a few moments for them to become healthy. You can check their status with `docker-compose ps`.

**2. Run the E2E Tests:**

Once the emulators are running, run the E2E tests with the required environment variables. These variables tell the tests how to connect to the emulators.

```bash
source .venv/bin/activate

export FIREBASE_AUTH_EMULATOR_HOST="localhost:9099"
export FIRESTORE_EMULATOR_HOST="localhost:8086"
export GOOGLE_CLOUD_PROJECT="cambridge-local"
export GCP_PROJECT_ID="cambridge-local"
export FIREBASE_WEB_API_KEY="fake-api-key"
export BASE_URL="http://localhost:8080"
export SESSION_SECRET_KEY="test-secret"
export TOKEN_ENCRYPTION_KEY="3xpo7t61pLEqmOiHEZs4qIvrPjieKmO1Pg5OSdwDRAI="

pytest tests/e2e/
```

**Note:** E2E tests will be automatically skipped if the required emulators are not available. This allows the test suite to run in CI/CD environments without Docker.

**3. Stop the Emulators:**

When you are finished running the tests, stop the emulators.

```bash
docker-compose down
```

## Docker

Build and run the production container:
```bash
docker build -t cambridge . && docker run -p 8080:8080 cambridge
```
```

### Pre-commit Hooks

To run the pre-commit hooks on all files, follow these steps:

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    ```

2.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements-dev.txt
    ```

4.  **Run pre-commit:**
    ```bash
    pre-commit run --all-files
    ```

**CI/CD:**
- test (PRs only) → runs pytest with coverage
- terraform-validate (PRs only) → validates terraform configuration
- deploy (manual) → workflow_dispatch with blue-green deployment to Cloud Run
  - Step 1: Deploy new revision with `--no-traffic` (tagged with short SHA)
  - Step 2: Validate `/health` endpoint (5 retries, 3s intervals)
  - Step 3: Migrate 100% traffic to new revision
  - Step 4: Tag deployed image with `deployed-<timestamp>` tag in Artifact Registry

## Conventions

### Code Style
- **Format:** black (88 char line length)
- **Lint:** flake8, mypy
- **FastAPI:**
  - async/await, JSONResponse, type hints, docstrings
  - Pydantic v2 models with `ConfigDict` (not deprecated `class Config`)
  - Modern `lifespan` context manager (not deprecated `on_event`)
  - Centralized exception handlers (no try-except in endpoints!)
- **Architecture:**
  - Dumb adapters: Just translate HTTP ↔ Python, delegate to service
  - Smart services: All business logic (logging, validation, publishing)
  - Domain objects: Pass FrameIOEvent to infrastructure (not dicts!)
  - Serialization: Infrastructure concern (adapters handle JSON conversion)
- **Logging:**
  - Config: `app/logging_config.py` with `setup_global_logging()`
  - Cloud Run: google-cloud-logging with trace correlation (detected via K_SERVICE env var)
  - Local/Test: Standard Python logging to stdout
  - Structured JSON: Single log entry with `json.dumps()` (see app/core/services.py:60-78, app/api/magic.py:108-114)
- **Environment:** No default values for required env vars - app should fail fast at startup if missing
- **Tests:** 90%+ coverage, Test* classes, descriptive names, fixtures, test contracts not implementation

**Endpoints:**
- `GET /` - Health check with service info
- `GET /health` - Simple health check
- `POST /api/v1/frameio/webhook` - Receives Frame.io webhooks, validates, logs, publishes to Pub/Sub
- `POST /auth/magic/send` - Generate magic link for email authentication (logged as JSON)
- `GET /auth/magic/callback` - Firebase callback, exchanges oobCode for session cookie, redirects to /dashboard
- `GET /dashboard` - Protected endpoint, requires valid session cookie
- `GET /oauth/{provider}/connect` - Start OAuth2 flow, redirects to provider (requires auth)
- `GET /oauth/{provider}/callback` - OAuth2 callback, stores tokens, redirects to dashboard
- `GET /oauth/connections` - List connected OAuth services for current user
- `DELETE /oauth/{provider}` - Disconnect OAuth service

**HTTP Status Codes:**
- `200 OK` - Event successfully published, returns `{"message_id": "..."}`
- `422 Unprocessable Entity` - Invalid JSON or missing required fields (client error, do not retry)
- `500 Internal Server Error` - Pub/Sub publishing failed (server error, Frame.io retries)

**Frame.io payload:** `{type, resource: {type, id}, account: {id}, workspace: {id}, project: {id}, user: {id}}`

**Error Handling:**
- Centralized in `app/main.py` using `@app.exception_handler()`
- `PublisherError` → 500 (Pub/Sub failures, Frame.io retries)
- `RequestValidationError` → 422 (Invalid payload, Frame.io does not retry)
- No try-except in endpoints or adapters!

**Docker:** Multi-stage build → non-root user (appuser) → PYTHONUNBUFFERED=1 for Cloud Run

**GCP (via Terraform):**
- Service: `cambridge` (europe-west1, 512Mi, 1 CPU, max 1 instance)
- Artifact Registry for images (tags: `<short-sha>`, `latest`, `deployed-<timestamp>`)
  - Cleanup policy: keeps 7 most recent versions
- Pub/Sub topic: `frameio-events` (for webhook event distribution)
- Pub/Sub subscription: `frameio-events-debug-sub` (7-day retention, for testing/debugging)
- Service accounts:
  - GitHub Actions (CI/CD deployment)
  - Cloud Run (Pub/Sub publisher role)
- Unauthenticated access (required for webhooks)
- Enabled APIs: Cloud Run, Artifact Registry, IAM, Pub/Sub

**Logging Architecture:**
- **Environment Detection:** `app/logging_config.py` checks `K_SERVICE` env var
- **Cloud Run Mode:** Uses `google-cloud-logging` for structured logs with automatic trace correlation
- **Local/Test Mode:** Falls back to standard Python logging to stdout
- **Structured Logging:** Webhooks logged as single JSON object with all fields in `jsonPayload`
- **Benefits:** Request trace grouping in GCP Console, queryable log fields, single-line log entries

**Pub/Sub Architecture:**
- **Client:** `app/pubsub_client.py` (auto-detects emulator via `PUBSUB_EMULATOR_HOST`)
- **Publishing:** Webhook payloads published to `frameio-events` topic with attributes (event_type, resource_type, resource_id)
- **Error Handling:** Pub/Sub failures don't affect webhook response (logged but not returned as errors)
- **Local Development:** `docker-compose up` automatically starts emulator and creates topic/subscription
- **Production:** Uses Cloud Run service account with `roles/pubsub.publisher`

## Workflow

**Making changes:**
1. Run tests: `pytest --cov=app --cov-report=term-missing`
2. For features: Add to app/main.py → Add tests → Update README → Commit (`feat:`)
3. For bugs: Write failing test → Fix → Verify → Commit (`fix:`)
4. Before commit: You MUST run `pre-commit run --all-files` and fix any errors.

**Common tasks:**
- Add webhook field: Extract in app/main.py → Log + Publish to Pub/Sub → Add tests
- Change Cloud Run config: Edit `.github/workflows/deploy.yml:59-78` (env vars, flags, service account)
- Add endpoint: app/main.py + tests/test_main.py + README + maintain 90% coverage
- Modify logging: Edit `app/logging_config.py` (K_SERVICE detection for Cloud Run)
- Modify Pub/Sub: Edit `app/pubsub_client.py` + update tests in tests/test_pubsub_client.py
- Add Pub/Sub consumer: Create new service + subscribe to `frameio-events` topic (or use `frameio-events-debug-sub` for testing)

**GitHub Actions best practices:**
- Use `pull_request` trigger only for PR checks (not both `push` and `pull_request`)
- Avoid duplicate workflow runs by choosing one trigger per workflow
- Current setup: test run on PRs only, deploy is manual

**Security notes:**
- Unauthenticated access (required for webhooks)
- No signature verification (Frame.io provides signing secrets if needed)
- Non-root container user
- Max 1 instance (cost control)

## Quick Reference

```bash
# Development
python app/main.py                              # Run locally
pytest --cov=app --cov-report=term-missing      # Test
pre-commit run --all-files                      # Format & Lint

# Docker
docker build -t cambridge . && docker run -p 8080:8080 cambridge

# Test webhook
curl -X POST http://localhost:8080/api/v1/frameio/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "file.created", "resource": {"id": "test-123", "type": "file"}, "account": {"id": "acc-123"}}'

# GCP logs
# Note: This command requires a recent version of the gcloud CLI.
gcloud beta run services logs tail cambridge --project cambridge-7 --region europe-west1

# View deployed image in Artifact Registry
gcloud artifacts docker tags list europe-west1-docker.pkg.dev/$PROJECT_ID/cambridge-repo/cambridge

# Pub/Sub (local testing with emulator)
docker-compose up                            # Start app + Pub/Sub emulator (auto-creates topics)
python scripts/pull-pubsub-messages.py      # Pull messages from frameio-events-debug-sub

# Pub/Sub (production)
gcloud pubsub subscriptions pull frameio-events-debug-sub --limit=10 --auto-ack
gcloud pubsub topics publish frameio-events --message='{"test": "message"}'

# Terraform
cd terraform && terraform init && terraform apply
terraform output -raw github_actions_service_account_key | base64 -d > key.json
terraform output pubsub_topic_name          # View Pub/Sub topic name

# Magic Link Authentication (with docker-compose)
curl -X POST http://localhost:8080/auth/magic/send \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
# Copy magic link from logs, paste in browser → /dashboard
```

## Deployment

**Branch pattern:** `agent/agents-md-<session-id>` (never push to main)

**Process:** Commit → Tests auto-run → Manual deploy via Actions

**Blue-Green Deployment:**
1. **Deploy (no traffic):** New revision deployed with `--no-traffic` flag, tagged with short SHA (8 chars)
2. **Validate:** Health check on new revision URL (5 attempts, 3s intervals, must return HTTP 200)
3. **Migrate traffic:** If validation passes, 100% traffic switches to new revision
4. **Tag image:** Successfully deployed image tagged with `deployed-<timestamp>` in Artifact Registry
5. **Rollback:** If validation fails, deployment aborts (old revision keeps serving traffic)

**Environment Variables (Cloud Run):**
- `GCP_PROJECT_ID` - GCP project ID (required)
- `PUBSUB_TOPIC_NAME` - Pub/Sub topic name (required)
- `PUBSUB_EMULATOR_HOST` - Pub/Sub emulator host (local dev only)
- `FIREBASE_AUTH_EMULATOR_HOST` - Firebase Auth emulator host (local dev only)
- `FIREBASE_WEB_API_KEY` - Firebase Web API key (required for magic link auth)
- `BASE_URL` - Auto-derived from Cloud Run service URL during deployment
- `K_SERVICE` - Auto-set by Cloud Run (triggers structured logging)
- `SESSION_SECRET_KEY` - Secret key for session middleware (required for OAuth state)
- `GOOGLE_CLIENT_ID` - Google OAuth2 client ID (optional, enables Google integration)
- `GOOGLE_CLIENT_SECRET` - Google OAuth2 client secret (optional)
- `ADOBE_CLIENT_ID` - Adobe OAuth2 client ID (optional, enables Adobe integration)
- `ADOBE_CLIENT_SECRET` - Adobe OAuth2 client secret (optional)

## Frame.io Integration

**Events:** `file.created`, `file.ready`, `file.upload.completed`, `comment.created`

**Headers:** `User-Agent: Frame.io V4 API`, `Content-Type: application/json`

## Notes

**Cost:** Max 1 instance, scales to zero, 512Mi/1CPU, 2M requests/month free

**Troubleshooting:**
- Tests fail → Check Python 3.11, deps installed (pip install -r requirements-dev.txt)
- Deploy fails → Verify GitHub secrets (GCP_PROJECT_ID, GCP_SA_KEY)
- No webhook logs → Check Cloud Run URL, test with curl
- Pub/Sub not publishing → Check GCP_PROJECT_ID env var, verify service account has pubsub.publisher role
- Pub/Sub emulator not working → Ensure PUBSUB_EMULATOR_HOST is set, topic/subscription created (run setup script)
- Messages not in Pub/Sub → Check application logs for publishing errors, verify topic exists

## Magic Link Authentication

**Flow:** `POST /auth/magic/send → Firebase generates link → User clicks → /auth/magic/callback → Session cookie → /dashboard`

**Local Development:** `docker-compose up` starts Firebase Auth Emulator (port 9099, UI at 4000)

**Production:** Set `FIREBASE_WEB_API_KEY`, `BASE_URL`, add callback domain to Firebase authorized domains

## OAuth2 Service Integrations

**Architecture:** Magic Link establishes user identity (Firebase UID) → OAuth2 connects external services → Tokens stored per user/provider

**Flow:**
```
User authenticated via Magic Link
  → GET /oauth/google/connect (requires session cookie)
  → Redirect to Google OAuth consent
  → Google redirects to /oauth/google/callback
  → Tokens stored in UserRepository (keyed by Firebase UID + provider)
  → Redirect to /dashboard?connected=google
```

**Supported Providers:**
- `google` - Google APIs (Photos, Drive, etc.) - configure via `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `adobe` - Adobe APIs (Frame.io, Creative Cloud) - configure via `ADOBE_CLIENT_ID`, `ADOBE_CLIENT_SECRET`

**Key Components:**
- `app/oauth/config.py` - Authlib OAuth registry, provider configuration
- `app/oauth/router.py` - OAuth endpoints (connect, callback, list, disconnect)
- `app/users/models.py` - User and OAuthToken domain models
- `app/users/repository.py` - UserRepository interface (InMemory impl, Firestore future)
- `app/integrations/{provider}/` - Provider-specific API integrations

**Adding a New Provider:**
1. Add credentials to `app/oauth/config.py` (register with authlib)
2. Add provider to `SUPPORTED_PROVIDERS` list
3. Create integration module at `app/integrations/{provider}/`

**Token Storage:** Currently in-memory (InMemoryUserRepository). Replace with Firestore for production persistence.

---
*Updated: 2025-11-23 | Python 3.11 | FastAPI 0.109.0 | google-cloud-pubsub 2.21.1 | firebase-admin 6.4.0 | authlib 1.3.0*
