# CLAUDE.md - AI Assistant Guide

FastAPI webhook receiver for Frame.io V4 → logs payloads to GCP Cloud Run → viewable via Cloud Logging.

**Stack:** Python 3.11 • FastAPI 0.109.0 • Docker • GCP Cloud Run • Terraform

**Flow:** `Frame.io → /api/v1/frameio/webhook → stdout → Cloud Logging`

## Structure

**Core files:**
- `app/main.py` - FastAPI app (127 lines, only Python file)
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

**CI/CD:** commitlint (validate commits) → test (pytest on PRs) → deploy (manual to Cloud Run)

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
- **Logging:** INFO level, structured (see app/main.py:82-101)
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
- Artifact Registry for images
- Service account for GitHub Actions
- Unauthenticated access (required for webhooks)

## Workflow

**Making changes:**
1. Run tests: `pytest --cov=app --cov-report=term-missing`
2. For features: Add to app/main.py → Add tests → Update README → Commit (`feat:`)
3. For bugs: Write failing test → Fix → Verify → Commit (`fix:`)
4. Before commit: `black app/ tests/` + verify commit format

**Common tasks:**
- Add webhook field: Extract in app/main.py:72-79 → Log at :82-101 → Add tests
- Change Cloud Run config: Edit `.github/workflows/deploy.yml:48-59`
- Add endpoint: app/main.py + tests/test_main.py + README + maintain 90% coverage

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

# Terraform
cd terraform && terraform init && terraform apply
terraform output -raw github_actions_service_account_key | base64 -d > key.json
```

## Deployment

**Branch pattern:** `claude/claude-md-<session-id>` (never push to main)

**Process:** Commit → Tests auto-run → Commitlint validates → Manual deploy via Actions

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
