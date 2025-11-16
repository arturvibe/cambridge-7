#!/bin/bash
# Setup Pub/Sub emulator for local development
# This script creates the topic and subscription in the emulator

set -e

PROJECT_ID="${GCP_PROJECT_ID:-cambridge-local}"
TOPIC_NAME="${PUBSUB_TOPIC_NAME:-frameio-webhooks}"
SUBSCRIPTION_NAME="${TOPIC_NAME}-sub"
EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-localhost:8085}"

echo "Setting up Pub/Sub emulator..."
echo "Project ID: $PROJECT_ID"
echo "Topic: $TOPIC_NAME"
echo "Subscription: $SUBSCRIPTION_NAME"
echo "Emulator host: $EMULATOR_HOST"
echo ""

# Export emulator host for gcloud commands
export PUBSUB_EMULATOR_HOST=$EMULATOR_HOST

# Wait for emulator to be ready
echo "Waiting for emulator to be ready..."
max_attempts=30
attempt=0
until curl -s http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics > /dev/null 2>&1 || [ $attempt -eq $max_attempts ]; do
  attempt=$((attempt + 1))
  echo "Attempt $attempt/$max_attempts..."
  sleep 1
done

if [ $attempt -eq $max_attempts ]; then
  echo "ERROR: Emulator not ready after $max_attempts attempts"
  exit 1
fi

echo "Emulator is ready!"
echo ""

# Create topic
echo "Creating topic: $TOPIC_NAME"
curl -s -X PUT "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics/${TOPIC_NAME}" \
  -H "Content-Type: application/json" \
  -d '{}'

# Create subscription
echo "Creating subscription: $SUBSCRIPTION_NAME"
curl -s -X PUT "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/${SUBSCRIPTION_NAME}" \
  -H "Content-Type: application/json" \
  -d "{\"topic\": \"projects/${PROJECT_ID}/topics/${TOPIC_NAME}\"}"

echo ""
echo "Setup complete!"
echo ""
echo "To test publishing, run:"
echo "  curl -X POST http://localhost:8080/api/v1/frameio/webhook \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"type\": \"file.created\", \"resource\": {\"id\": \"test-123\", \"type\": \"file\"}}'"
echo ""
echo "To view messages, run:"
echo "  python scripts/pull-pubsub-messages.py"
