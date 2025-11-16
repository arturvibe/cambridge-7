"""
Port definitions (interfaces) for the core domain.

Ports define the contracts between the core domain and external systems.
Infrastructure adapters implement these ports.
"""

from typing import Any, Dict, Optional, Protocol


class EventPublisher(Protocol):
    """
    Port (interface) for publishing events.

    This is implemented by infrastructure adapters (e.g., GooglePubSubPublisher).
    The core domain depends on this interface, not on concrete implementations.
    """

    def publish(
        self, message_data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Publish an event message.

        Args:
            message_data: The event data to publish
            attributes: Optional metadata attributes

        Returns:
            Message ID if successful, None otherwise
        """
        ...

    def close(self) -> None:
        """Close the publisher and cleanup resources."""
        ...
