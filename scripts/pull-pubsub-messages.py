#!/usr/bin/env python3
"""
Script to pull and display messages from Pub/Sub (emulator or production).
Useful for testing and debugging webhook message flow.
"""

import json
import os
import sys
from google.cloud import pubsub_v1

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cambridge-local")
SUBSCRIPTION_NAME = os.getenv("PUBSUB_SUBSCRIPTION_NAME", "frameio-events-debug-sub")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "10"))

# If using emulator, set PUBSUB_EMULATOR_HOST environment variable
emulator_host = os.getenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
if emulator_host:
    os.environ["PUBSUB_EMULATOR_HOST"] = emulator_host
    print(f"Using Pub/Sub emulator at: {emulator_host}\n")


def pull_messages():
    """Pull messages from the subscription and display them."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

    print(f"Pulling messages from subscription: {subscription_path}")
    print(f"Max messages: {MAX_MESSAGES}\n")

    try:
        # Pull messages
        response = subscriber.pull(
            request={"subscription": subscription_path, "max_messages": MAX_MESSAGES}
        )

        if not response.received_messages:
            print("No messages available.")
            return

        print(f"Received {len(response.received_messages)} message(s):\n")

        ack_ids = []
        for idx, received_message in enumerate(response.received_messages, 1):
            message = received_message.message

            # Parse message data
            try:
                data = json.loads(message.data.decode("utf-8"))
                data_str = json.dumps(data, indent=2)
            except:
                data_str = message.data.decode("utf-8")

            # Display message
            print(f"{'=' * 80}")
            print(f"Message {idx}:")
            print(f"{'=' * 80}")
            print(f"Message ID: {message.message_id}")
            print(f"Publish Time: {message.publish_time}")
            print(f"\nAttributes:")
            for key, value in message.attributes.items():
                print(f"  {key}: {value}")
            print(f"\nData:")
            print(data_str)
            print(f"{'=' * 80}\n")

            ack_ids.append(received_message.ack_id)

        # Acknowledge messages
        if ack_ids:
            subscriber.acknowledge(
                request={"subscription": subscription_path, "ack_ids": ack_ids}
            )
            print(f"Acknowledged {len(ack_ids)} message(s).")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    pull_messages()
