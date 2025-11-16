# CLAUDE.md - AI Assistant Guide

FastAPI webhook receiver for Frame.io V4 → logs payloads to GCP Cloud Run → publishes to Pub/Sub → viewable via Cloud Logging.

**Stack:** Python 3.11 • FastAPI 0.109.0 • google-cloud-logging • google-cloud-pubsub • Docker • GCP Cloud Run • Terraform

**Flow:** `Frame.io → /api/v1/frameio/webhook → [Log to stdout + Publish to Pub/Sub] → Cloud Logging`

## Structure

**Core files:**
- `app/main.py` - FastAPI app with webhook handling and Pub/Sub publishing
- `app/pubsub_client.py` - Pub/Sub client wrapper (auto-detects emulator vs production)
- `app/logging_config.py` - Logging configuration with Cloud Run detection
- `tests/test_main.py` - Unit tests for endpoints and Pub/Sub integration
- `tests/test_pubsub_client.py` - Unit tests for Pub/Sub client (90%+ coverage total)
- `Dockerfile` - Multi-stage build
- `.github/workflows/` - CI/CD (commitlint, test, deploy)
- `terraform/` - GCP infrastructure as code (includes Pub/Sub topic/subscription)
- `docker-compose.yml` - Local dev environment with Pub/Sub emulator
- `LOCAL_PUBSUB_TESTING.md` - Guide for testing Pub/Sub locally

## Development

```bash
# Setup
pip install -r requirements-dev.txt
pre-commit install  # Install git hooks for auto-formatting

# Run locally with Pub/Sub emulator (recommended)
docker-compose up  # Starts emulator, sets up topics, and runs app at http://localhost:8080

# Test
pytest --cov=app --cov-report=term-missing  # Must maintain 90%+ coverage

# Docker
docker build -t cambridge . && docker run -p 8080:8080 cambridge
```

**Pre-commit hooks:** Auto-format Python (black) and Terraform files before commit

**CI/CD:**
- commitlint (PRs only) → validates all commits in PR
- test (PRs only) → runs pytest with coverage
- terraform-validate (PRs only) → validates terraform configuration
- deploy (manual) → workflow_dispatch with blue-green deployment to Cloud Run
  - Step 1: Deploy new revision with `--no-traffic` (tagged with short SHA)
  - Step 2: Validate `/health` endpoint (5 retries, 3s intervals)
  - Step 3: Migrate 100% traffic to new revision
  - Step 4: Tag deployed image with `deployed-<timestamp>` tag in Artifact Registry

## Conventions

### Commits & PR Titles (ENFORCED)
**Format:** `type: subject` (max 100 chars, lowercase type)

**Types:** `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`

Examples:
- `feat: add file.ready webhook support`
- `fix: handle missing workspace_id`
- `test: add large payload tests`

**Note:** PR titles must follow the same format as commit messages

### Code Style
- **Format:** black (88 char line length)
- **Lint:** flake8, mypy
- **FastAPI:** async/await, JSONResponse, type hints, docstrings
- **Logging:**
  - Config: `app/logging_config.py` with `setup_global_logging()`
  - Cloud Run: google-cloud-logging with trace correlation (detected via K_SERVICE env var)
  - Local/Test: Standard Python logging to stdout
  - Structured JSON: Single log entry per webhook (see app/main.py:81-100)
- **Tests:** 90%+ coverage, Test* classes, descriptive names, fixtures

## Architecture

**Endpoints:**
- `GET /` - Health check with service info
- `GET /health` - Simple health check
- `POST /api/v1/frameio/webhook` - Receives Frame.io webhooks, logs payload, publishes to Pub/Sub, returns 200 (includes pubsub_message_id in response if successful)

**Frame.io payload:** `{type, resource: {type, id}, account: {id}, workspace: {id}, project: {id}, user: {id}}`

**Docker:** Multi-stage build → non-root user (appuser) → PYTHONUNBUFFERED=1 for Cloud Run

**GCP (via Terraform):**
- Service: `cambridge` (europe-west1, 512Mi, 1 CPU, max 1 instance)
- Artifact Registry for images (tags: `<short-sha>`, `latest`, `deployed-<timestamp>`)
  - Cleanup policy: keeps 7 most recent versions
- Pub/Sub topic: `frameio-events` (for webhook event distribution)
- Pub/Sub subscription: `frameio-events-sub` (7-day retention, for testing/monitoring)
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
4. Before commit: `black app/ tests/` + verify commit format

**Common tasks:**
- Add webhook field: Extract in app/main.py → Log + Publish to Pub/Sub → Add tests
- Change Cloud Run config: Edit `.github/workflows/deploy.yml:59-78` (env vars, flags, service account)
- Add endpoint: app/main.py + tests/test_main.py + README + maintain 90% coverage
- Modify logging: Edit `app/logging_config.py` (K_SERVICE detection for Cloud Run)
- Modify Pub/Sub: Edit `app/pubsub_client.py` + update tests in tests/test_pubsub_client.py
- Add Pub/Sub consumer: Create new service + subscribe to `frameio-events-sub`

**GitHub Actions best practices:**
- Use `pull_request` trigger only for PR checks (not both `push` and `pull_request`)
- Avoid duplicate workflow runs by choosing one trigger per workflow
- Current setup: commitlint + test run on PRs only, deploy is manual

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
black app/ tests/                               # Format

# Docker
docker build -t cambridge . && docker run -p 8080:8080 cambridge

# Test webhook
curl -X POST http://localhost:8080/api/v1/frameio/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "file.created", "resource": {"id": "test-123", "type": "file"}, "account": {"id": "acc-123"}}'

# GCP logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge"

# View deployed image in Artifact Registry
gcloud artifacts docker tags list europe-west1-docker.pkg.dev/$PROJECT_ID/cambridge-repo/cambridge

# Pub/Sub (local testing with emulator)
docker-compose up                            # Start app + Pub/Sub emulator (auto-creates topics)
python scripts/pull-pubsub-messages.py      # Pull messages from frameio-events-sub

# Pub/Sub (production)
gcloud pubsub subscriptions pull frameio-events-sub --limit=10 --auto-ack
gcloud pubsub topics publish frameio-events --message='{"test": "message"}'

# Terraform
cd terraform && terraform init && terraform apply
terraform output -raw github_actions_service_account_key | base64 -d > key.json
terraform output pubsub_topic_name          # View Pub/Sub topic name
```

## Deployment

**Branch pattern:** `claude/claude-md-<session-id>` (never push to main)

**Process:** Commit → Tests auto-run → Commitlint validates → Manual deploy via Actions

**Blue-Green Deployment:**
1. **Deploy (no traffic):** New revision deployed with `--no-traffic` flag, tagged with short SHA (8 chars)
2. **Validate:** Health check on new revision URL (5 attempts, 3s intervals, must return HTTP 200)
3. **Migrate traffic:** If validation passes, 100% traffic switches to new revision
4. **Tag image:** Successfully deployed image tagged with `deployed-<timestamp>` in Artifact Registry
5. **Rollback:** If validation fails, deployment aborts (old revision keeps serving traffic)

**Environment Variables (Cloud Run):**
- `GCP_PROJECT_ID` - GCP project ID (required)
- `PUBSUB_TOPIC_NAME` - Pub/Sub topic name (required)
- `PUBSUB_EMULATOR_HOST` - Pub/Sub emulator host (local dev only, e.g., `localhost:8085`)
- `K_SERVICE` - Auto-set by Cloud Run (triggers structured logging)

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

---
*Updated: 2025-11-16 | Python 3.11 | FastAPI 0.109.0 | google-cloud-pubsub 2.21.1*
