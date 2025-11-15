# CLAUDE.md - AI Assistant Guide

FastAPI webhook receiver for Frame.io V4 → logs payloads to GCP Cloud Run → viewable via Cloud Logging.

**Stack:** Python 3.11 • FastAPI 0.109.0 • google-cloud-logging • Docker • GCP Cloud Run • Terraform

**Flow:** `Frame.io → /api/v1/frameio/webhook → stdout → Cloud Logging`

## Structure

**Core files:**
- `app/main.py` - FastAPI app (126 lines)
- `app/logging_config.py` - Logging configuration with Cloud Run detection
- `tests/test_main.py` - Unit tests (90%+ coverage)
- `Dockerfile` - Multi-stage build
- `.github/workflows/` - CI/CD (commitlint, test, deploy)
- `terraform/` - GCP infrastructure as code

## Development

```bash
# Setup
pip install -r requirements-dev.txt

# Run locally
python app/main.py  # http://localhost:8080

# Test
pytest --cov=app --cov-report=term-missing  # Must maintain 90%+ coverage

# Docker
docker build -t cambridge . && docker run -p 8080:8080 cambridge
```

**CI/CD:**
- commitlint (PRs only) → validates all commits in PR
- test (PRs only) → runs pytest with coverage
- deploy (manual) → workflow_dispatch with blue-green deployment to Cloud Run
  - Step 1: Deploy new revision with `--no-traffic` (tagged with commit SHA)
  - Step 2: Validate `/health` endpoint (5 retries, 3s intervals)
  - Step 3: Migrate 100% traffic to new revision
  - Step 4: Tag deployed image with `deployed` tag in Artifact Registry

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
- `POST /api/v1/frameio/webhook` - Receives Frame.io webhooks, logs payload, returns 200

**Frame.io payload:** `{type, resource: {type, id}, account: {id}, workspace: {id}, project: {id}, user: {id}}`

**Docker:** Multi-stage build → non-root user (appuser) → PYTHONUNBUFFERED=1 for Cloud Run

**GCP (via Terraform):**
- Service: `cambridge` (europe-west1, 512Mi, 1 CPU, max 1 instance)
- Artifact Registry for images (tags: `<commit-sha>`, `latest`, `deployed`)
- Service account for GitHub Actions
- Unauthenticated access (required for webhooks)

**Logging Architecture:**
- **Environment Detection:** `app/logging_config.py` checks `K_SERVICE` env var
- **Cloud Run Mode:** Uses `google-cloud-logging` for structured logs with automatic trace correlation
- **Local/Test Mode:** Falls back to standard Python logging to stdout
- **Structured Logging:** Webhooks logged as single JSON object with all fields in `jsonPayload`
- **Benefits:** Request trace grouping in GCP Console, queryable log fields, single-line log entries

## Workflow

**Making changes:**
1. Run tests: `pytest --cov=app --cov-report=term-missing`
2. For features: Add to app/main.py → Add tests → Update README → Commit (`feat:`)
3. For bugs: Write failing test → Fix → Verify → Commit (`fix:`)
4. Before commit: `black app/ tests/` + verify commit format

**Common tasks:**
- Add webhook field: Extract in app/main.py:72-79 → Log at :83-97 → Add tests
- Change Cloud Run config: Edit `.github/workflows/deploy.yml:48-59`
- Add endpoint: app/main.py + tests/test_main.py + README + maintain 90% coverage
- Modify logging: Edit `app/logging_config.py` (K_SERVICE detection for Cloud Run)

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

# Terraform
cd terraform && terraform init && terraform apply
terraform output -raw github_actions_service_account_key | base64 -d > key.json
```

## Deployment

**Branch pattern:** `claude/claude-md-<session-id>` (never push to main)

**Process:** Commit → Tests auto-run → Commitlint validates → Manual deploy via Actions

**Blue-Green Deployment:**
1. **Deploy (no traffic):** New revision deployed with `--no-traffic` flag, tagged with commit SHA
2. **Validate:** Health check on new revision URL (5 attempts, 3s intervals, must return HTTP 200)
3. **Migrate traffic:** If validation passes, 100% traffic switches to new revision
4. **Tag image:** Successfully deployed image tagged with `deployed` in Artifact Registry
5. **Rollback:** If validation fails, deployment aborts (old revision keeps serving traffic)

## Frame.io Integration

**Events:** `file.created`, `file.ready`, `file.upload.completed`, `comment.created`

**Headers:** `User-Agent: Frame.io V4 API`, `Content-Type: application/json`

## Notes

**Cost:** Max 1 instance, scales to zero, 512Mi/1CPU, 2M requests/month free

**Troubleshooting:**
- Tests fail → Check Python 3.11, deps installed
- Deploy fails → Verify GitHub secrets (GCP_PROJECT_ID, GCP_SA_KEY)
- No webhook logs → Check Cloud Run URL, test with curl

---
*Updated: 2025-11-15 | Python 3.11 | FastAPI 0.109.0*
