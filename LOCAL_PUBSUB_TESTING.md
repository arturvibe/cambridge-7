# Local Pub/Sub Testing Guide

This guide explains how to test the Pub/Sub integration locally using the Google Cloud Pub/Sub emulator.

## Quick Start with Docker Compose

The easiest way to test locally is using Docker Compose, which automatically starts both the Pub/Sub emulator and the application:

```bash
# Start services (emulator + application)
docker-compose up

# In another terminal, send a test webhook
curl -X POST http://localhost:8080/api/v1/frameio/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "file.created", "resource": {"id": "test-123", "type": "file"}, "account": {"id": "acc-123"}}'

# Pull and view messages from Pub/Sub
python scripts/pull-pubsub-messages.py
```

## Manual Setup (Without Docker Compose)

### 1. Start the Pub/Sub Emulator

```bash
# Using gcloud CLI
gcloud beta emulators pubsub start --host-port=localhost:8085 --project=cambridge-local
```

### 2. Setup Topic and Subscription

In a new terminal:

```bash
# Export emulator host
export PUBSUB_EMULATOR_HOST=localhost:8085
export GCP_PROJECT_ID=cambridge-local
export PUBSUB_TOPIC_NAME=frameio-webhooks

# Run setup script
./scripts/setup-pubsub-emulator.sh
```

### 3. Run the Application

In another terminal:

```bash
# Set environment variables
export PUBSUB_EMULATOR_HOST=localhost:8085
export GCP_PROJECT_ID=cambridge-local
export PUBSUB_TOPIC_NAME=frameio-webhooks
export PUBSUB_ENABLED=true

# Run application
python app/main.py
```

### 4. Test the Webhook

```bash
# Send a test webhook
curl -X POST http://localhost:8080/api/v1/frameio/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "file.created",
    "resource": {"id": "test-123", "type": "file"},
    "account": {"id": "acc-123"},
    "workspace": {"id": "ws-456"},
    "project": {"id": "proj-789"},
    "user": {"id": "user-xyz"}
  }'
```

### 5. View Messages

```bash
# Pull messages from the subscription
export PUBSUB_EMULATOR_HOST=localhost:8085
python scripts/pull-pubsub-messages.py
```

## Running Tests

Tests automatically mock Pub/Sub, so no emulator is needed:

```bash
# Run all tests
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_main.py -v
```

## Environment Variables

Create a `.env` file (see `.env.example`) with these variables:

```bash
# GCP Project ID (use "cambridge-local" for emulator)
GCP_PROJECT_ID=cambridge-local

# Pub/Sub topic name
PUBSUB_TOPIC_NAME=frameio-webhooks

# Enable/disable Pub/Sub publishing
PUBSUB_ENABLED=true

# Emulator host (leave unset for production)
PUBSUB_EMULATOR_HOST=localhost:8085
```

## Disabling Pub/Sub

To test without Pub/Sub:

```bash
export PUBSUB_ENABLED=false
python app/main.py
```

## Troubleshooting

### Emulator not starting

- Ensure gcloud CLI is installed: `gcloud version`
- Install beta components: `gcloud components install beta`

### Messages not appearing

- Check emulator is running: `curl http://localhost:8085`
- Verify topic exists: Check setup script output
- Check application logs for errors

### Permission errors

- When using emulator, ensure `PUBSUB_EMULATOR_HOST` is set
- For production, verify service account has `roles/pubsub.publisher` role

## Production Deployment

In production (Cloud Run), the application automatically:
- Detects it's not using an emulator (no `PUBSUB_EMULATOR_HOST`)
- Uses the Cloud Run service account for authentication
- Publishes to the real Pub/Sub topic

Required environment variables in Cloud Run:
```bash
GCP_PROJECT_ID=your-project-id
PUBSUB_TOPIC_NAME=frameio-webhooks
PUBSUB_ENABLED=true
```

## Monitoring Messages in Production

```bash
# View messages in GCP
gcloud pubsub subscriptions pull frameio-webhooks-sub --limit=10 --auto-ack

# Stream logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cambridge"
```
