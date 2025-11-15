# CLAUDE.md - AI Assistant Guide for Cambridge Repository

This document provides comprehensive guidance for AI assistants working on the Cambridge webhook receiver application.

## Project Overview

**Cambridge** is a FastAPI-based webhook receiver for Frame.io V4 webhooks, designed to run on Google Cloud Platform (GCP) Cloud Run. The application receives webhooks from Frame.io, logs the payloads to stdout, and makes them viewable through GCP Cloud Logging.

**Key Features:**
- FastAPI webhook endpoint at `/api/v1/frameio/webhook`
- Structured logging of Frame.io event data (event type, resource details, account/workspace/project IDs)
- Health check endpoints for monitoring
- Docker containerized with multi-stage builds
- Single-click deployment via GitHub Actions
- Comprehensive test suite with 90% code coverage
- Conventional Commits enforcement

**Architecture Flow:**
```
Frame.io → Webhook → Cloud Run Service → Logs to stdout → Cloud Logging
```

## Codebase Structure

```
cambridge-7/
├── .github/
│   └── workflows/
│       ├── commitlint.yml      # Validates commit message format
│       ├── deploy.yml          # Deploys to GCP Cloud Run
│       └── test.yml            # Runs tests on PRs
├── app/
│   └── main.py                 # Main FastAPI application (127 lines)
├── tests/
│   ├── __init__.py             # Test package marker
│   ├── test_main.py            # Unit tests (228 lines, 90%+ coverage)
│   └── README.md               # Testing documentation
├── terraform/
│   ├── main.tf                 # Infrastructure as code
│   ├── variables.tf            # Terraform input variables
│   ├── outputs.tf              # Terraform outputs
│   ├── terraform.tfvars.example # Example configuration
│   └── README.md               # Terraform documentation
├── .commitlintrc.json          # Commit message linting rules
├── .dockerignore               # Docker build exclusions
├── .gitignore                  # Git ignore patterns
├── Dockerfile                  # Multi-stage Docker build
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
└── README.md                   # User-facing documentation
```

## Technology Stack

### Core Technologies
- **Language:** Python 3.11
- **Web Framework:** FastAPI 0.109.0
- **ASGI Server:** Uvicorn 0.27.0 (with standard extras)
- **Data Validation:** Pydantic 2.5.3
- **Cloud Platform:** Google Cloud Platform (Cloud Run)
- **Container:** Docker (multi-stage builds)

### Development Tools
- **Testing:** pytest 7.4.4, pytest-cov 4.1.0, pytest-asyncio 0.23.3
- **HTTP Client (tests):** httpx 0.26.0
- **Code Formatting:** black 24.1.1
- **Linting:** flake8 7.0.0
- **Type Checking:** mypy 1.8.0

### Infrastructure
- **IaC:** Terraform >= 1.0 (Google Provider ~> 5.0)
- **CI/CD:** GitHub Actions
- **Container Registry:** Google Artifact Registry
- **Deployment:** GCP Cloud Run (europe-west1 region by default)

## Development Workflow

### Local Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run the application locally:**
   ```bash
   python app/main.py
   # Server starts at http://localhost:8080
   ```

3. **Run with Docker:**
   ```bash
   docker build -t cambridge .
   docker run -p 8080:8080 cambridge
   ```

### Testing Workflow

**Run all tests:**
```bash
pytest
```

**Run with coverage report:**
```bash
pytest --cov=app --cov-report=term-missing
```

**Run specific test classes:**
```bash
# Health endpoints
pytest tests/test_main.py::TestHealthEndpoints

# Webhook functionality
pytest tests/test_main.py::TestFrameIOWebhook

# Security tests
pytest tests/test_main.py::TestEndpointSecurity
```

**Test configuration:** See `pytest.ini` for pytest settings including:
- Coverage thresholds
- Test discovery patterns
- Output formatting
- Markers (unit, integration, slow)

### CI/CD Pipeline

**Three GitHub Actions workflows:**

1. **commitlint.yml** - Validates commit messages on every push/PR
2. **test.yml** - Runs pytest with coverage on all PRs
3. **deploy.yml** - Manual deployment to Cloud Run (workflow_dispatch)

**Required GitHub Secrets:**
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_SA_KEY` - Service account key JSON (created via Terraform)

## Key Conventions

### Commit Message Format

**IMPORTANT:** All commits must follow Conventional Commits specification.

**Allowed types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, no logic changes)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `build:` - Build system changes
- `ci:` - CI/CD changes
- `chore:` - Other changes (dependencies, configs)
- `revert:` - Reverting previous commits

**Rules:**
- Type must be lowercase
- Type cannot be empty
- Subject cannot be empty
- Header max length: 100 characters

**Examples:**
```bash
feat: add support for file.ready webhook events
fix: handle missing workspace_id in webhook payload
docs: update Frame.io webhook configuration steps
test: add tests for large payload handling
refactor: extract logging logic into separate function
```

### Code Style

**Python conventions:**
- Follow PEP 8 style guide
- Use black for code formatting
- Use flake8 for linting
- Use mypy for type checking
- Maximum line length: 88 characters (black default)

**FastAPI patterns:**
- Use async/await for all endpoints
- Return JSONResponse for explicit status codes
- Include detailed docstrings for all endpoints
- Use type hints for function parameters and returns

**Logging patterns:**
- Use Python's logging module (configured in app/main.py:14-18)
- Log level: INFO for normal operations, ERROR for failures
- Log structured data with clear separators (see app/main.py:82-101)
- Include timestamps, event types, IDs, and full payloads

### Testing Practices

**Test organization:**
- Group related tests in classes with `Test` prefix
- Use descriptive test names: `test_<what_is_being_tested>`
- Add docstrings explaining each test's purpose
- Use fixtures for reusable test data

**Test coverage requirements:**
- Minimum 90% code coverage
- All endpoints must have tests
- Test both success and error cases
- Test edge cases (empty payloads, invalid JSON, large payloads)

**Example test structure:**
```python
class TestNewFeature:
    """Test description."""

    @pytest.fixture
    def sample_data(self):
        """Fixture description."""
        return {"key": "value"}

    def test_feature_success_case(self, sample_data):
        """Test the success case."""
        # Test implementation
```

## Architecture Details

### Application Structure (app/main.py)

**Key components:**

1. **Logging Configuration** (lines 14-19)
   - Configured at module level
   - Format: timestamp, logger name, level, message
   - Level: INFO

2. **FastAPI Application** (lines 21-25)
   - Title: "Frame.io Webhook Receiver"
   - Version: "1.0.0"
   - OpenAPI docs available at `/docs`

3. **Health Endpoints:**
   - `GET /` - Returns status, service name, timestamp
   - `GET /health` - Simple health check for Cloud Run

4. **Webhook Endpoint** (lines 44-119)
   - `POST /api/v1/frameio/webhook`
   - Parses JSON payload
   - Extracts Frame.io V4 structure fields
   - Logs comprehensive webhook data
   - Returns 200 with structured response
   - Handles invalid JSON gracefully

**Frame.io V4 Webhook Structure:**
```json
{
  "type": "event.type",
  "resource": {"type": "...", "id": "..."},
  "account": {"id": "..."},
  "workspace": {"id": "..."},
  "project": {"id": "..."},
  "user": {"id": "..."}
}
```

### Docker Configuration

**Multi-stage build pattern:**

1. **Builder Stage** (Dockerfile:5-16)
   - Base: python:3.11-slim
   - Installs gcc for compiling dependencies
   - Installs packages to /root/.local

2. **Runtime Stage** (Dockerfile:18-50)
   - Base: python:3.11-slim
   - Creates non-root user (appuser, UID 1000)
   - Copies installed packages from builder
   - Runs as non-root for security
   - Sets PYTHONUNBUFFERED=1 for Cloud Run logging
   - Includes health check using /health endpoint

**Environment variables:**
- `PORT` - Port to bind (default: 8080, Cloud Run injects this)
- `PYTHONUNBUFFERED=1` - Required for real-time logging in Cloud Run

### GCP Infrastructure

**Terraform manages:**
- API enablement (Cloud Run, Artifact Registry, IAM)
- Artifact Registry repository for Docker images
- Service account for GitHub Actions
- IAM role bindings (roles/run.admin, roles/artifactregistry.writer, roles/iam.serviceAccountUser)
- Service account key generation

**Cloud Run configuration:**
- Service name: `cambridge`
- Region: `europe-west1` (configurable)
- Memory: 512Mi
- CPU: 1
- Max instances: 1 (cost optimization)
- Timeout: 60 seconds
- Port: 8080
- Authentication: `--allow-unauthenticated` (required for webhooks)

## AI Assistant Guidelines

### When Making Code Changes

1. **Always run tests first:**
   ```bash
   pytest --cov=app --cov-report=term-missing
   ```

2. **For new features:**
   - Add endpoint to app/main.py
   - Add corresponding tests to tests/test_main.py
   - Update README.md if user-facing
   - Ensure commit message follows Conventional Commits

3. **For bug fixes:**
   - Write a failing test first
   - Fix the bug
   - Verify test passes
   - Check coverage didn't decrease

4. **Before committing:**
   - Run tests: `pytest`
   - Check code style: `black app/ tests/`
   - Verify commit message format matches `.commitlintrc.json`

### Understanding Log Output

When viewing webhook logs, look for this structure (app/main.py:82-101):
```
================================================================================
FRAME.IO WEBHOOK RECEIVED
================================================================================
Event Type: <type>
Resource Type: <resource.type>
Resource ID: <resource.id>
Account ID: <account.id>
Workspace ID: <workspace.id>
Project ID: <project.id>
User ID: <user.id>
User Agent: <user-agent header>
Timestamp: <ISO 8601 timestamp>
Client IP: <request IP>
--------------------------------------------------------------------------------
HEADERS: {JSON}
--------------------------------------------------------------------------------
FULL PAYLOAD: {JSON}
================================================================================
```

### Common Modifications

**Adding a new webhook field to log:**
1. Extract field from payload in app/main.py (around line 72-79)
2. Add to logger.info output (around line 82-101)
3. Add to tests/test_main.py in relevant test cases
4. Run tests to verify

**Changing Cloud Run configuration:**
1. Update `.github/workflows/deploy.yml` (lines 48-59)
2. Optionally update terraform/main.tf if using Terraform-managed service
3. Test deployment with workflow_dispatch

**Adding new endpoint:**
1. Add route handler in app/main.py
2. Add test class in tests/test_main.py
3. Update README.md with endpoint documentation
4. Ensure 90%+ coverage maintained

### Security Considerations

**Current security posture:**
- Cloud Run service allows unauthenticated access (required for Frame.io webhooks)
- Application runs as non-root user in container
- No webhook signature verification implemented
- Max instances limited to 1 for cost control

**If implementing webhook verification:**
- Frame.io provides signing secrets
- Add verification in webhook endpoint before processing
- Add environment variable for signing secret
- Update Cloud Run deployment to inject secret
- Add tests for signature verification

### Troubleshooting Guide

**Tests failing:**
- Check Python version (must be 3.11)
- Verify all dependencies installed: `pip install -r requirements-dev.txt`
- Check for import errors or syntax issues
- Review pytest output for specific failures

**Docker build failing:**
- Ensure requirements.txt has no syntax errors
- Check Dockerfile syntax
- Verify base image is accessible
- Check disk space for Docker builds

**Deployment failing:**
- Verify GitHub secrets are set correctly
- Check GCP service account has correct permissions
- Ensure Artifact Registry repository exists
- Review GitHub Actions logs for specific errors

**Webhooks not appearing in logs:**
- Verify Cloud Run service URL is correct
- Check Frame.io webhook configuration
- Test endpoint manually with curl
- Check Cloud Run logs for errors or crashes

## Important Files Reference

### Configuration Files
- `.commitlintrc.json` - Commit message rules
- `pytest.ini` - Pytest and coverage configuration
- `.dockerignore` - Files excluded from Docker builds
- `.gitignore` - Files excluded from git

### Application Code
- `app/main.py` - **ONLY** Python application file (127 lines)
- `tests/test_main.py` - **ONLY** test file (228 lines)

### Infrastructure
- `Dockerfile` - Multi-stage Docker build
- `terraform/main.tf` - GCP infrastructure definition
- `.github/workflows/deploy.yml` - Deployment pipeline
- `.github/workflows/test.yml` - Testing pipeline
- `.github/workflows/commitlint.yml` - Commit validation

### Dependencies
- `requirements.txt` - Production dependencies (4 packages)
- `requirements-dev.txt` - Development dependencies (extends requirements.txt)

## Quick Reference Commands

### Development
```bash
# Run locally
python app/main.py

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=term-missing

# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type check
mypy app/
```

### Docker
```bash
# Build image
docker build -t cambridge .

# Run container
docker run -p 8080:8080 cambridge

# Test health endpoint
curl http://localhost:8080/health
```

### Testing Webhook
```bash
# Test local webhook endpoint
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

### GCP Operations
```bash
# View service logs (requires gcloud CLI)
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge"

# Get service URL
gcloud run services describe cambridge \
  --platform managed \
  --region europe-west1 \
  --format 'value(status.url)'

# Deploy manually (if not using GitHub Actions)
gcloud run deploy cambridge \
  --image europe-west1-docker.pkg.dev/PROJECT_ID/cambridge-repo/cambridge:latest \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

### Terraform
```bash
# Initialize Terraform
cd terraform && terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# Get service account key
terraform output -raw github_actions_service_account_key | base64 -d > key.json
```

## Branch and Deployment Strategy

### Current Branch
This repository uses feature branches following the pattern: `claude/claude-md-<session-id>`

**Important:**
- Always develop on the designated feature branch
- Never push directly to main/master without approval
- Use descriptive commit messages following Conventional Commits
- Deployment is manual via GitHub Actions workflow_dispatch

### Deployment Process
1. Code changes committed to feature branch
2. Tests run automatically via `.github/workflows/test.yml`
3. Commit messages validated via `.github/workflows/commitlint.yml`
4. Manual deployment triggered via Actions → "Deploy to Cloud Run" → Run workflow
5. Deployment pushes to GCP Cloud Run in europe-west1

## Frame.io Integration Notes

**Expected webhook events:**
- `file.created` - New file uploaded
- `file.ready` - File processing complete
- `file.upload.completed` - Upload finished
- `comment.created` - New comment added
- And other Frame.io V4 events

**Webhook headers to expect:**
- `User-Agent: Frame.io V4 API`
- `Content-Type: application/json`

**Payload structure:**
All Frame.io V4 webhooks include:
- `type` - Event type string
- `resource` - Object with type and id
- `account` - Account context
- `workspace` - Workspace context
- `project` - Project context
- `user` - User who triggered event

## Cost Optimization Notes

**Current configuration optimizes for minimal cost:**
- Max instances: 1 (sequential processing)
- Scales to zero when idle
- 512Mi memory / 1 CPU (sufficient for webhook logging)
- First 2 million requests/month free on Cloud Run

**If scaling needed:**
- Increase max-instances in `.github/workflows/deploy.yml:55`
- Consider async processing for heavy workloads
- Monitor costs via GCP Console

## Maintenance Checklist

**When updating dependencies:**
1. Update `requirements.txt` or `requirements-dev.txt`
2. Test locally: `pip install -r requirements-dev.txt && pytest`
3. Rebuild Docker image: `docker build -t cambridge .`
4. Test Docker container: `docker run -p 8080:8080 cambridge`
5. Commit with `build: update <package> to <version>`

**When adding features:**
1. Write tests first (TDD approach)
2. Implement feature in app/main.py
3. Ensure tests pass with 90%+ coverage
4. Update README.md if user-facing
5. Commit with `feat: <description>`

**When fixing bugs:**
1. Add failing test reproducing bug
2. Fix bug in app/main.py
3. Verify test passes
4. Commit with `fix: <description>`

---

**Last Updated:** 2025-11-15
**Application Version:** 1.0.0
**Python Version:** 3.11
**FastAPI Version:** 0.109.0
