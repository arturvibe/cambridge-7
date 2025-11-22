"""
Port definitions (interfaces) for the core domain.

Ports define the contracts between the core domain and external systems.
Infrastructure adapters implement these ports.
"""

from typing import Optional, Protocol

from app.core.domain import FrameIOEvent


class EventPublisher(Protocol):
    """
    Port (interface) for publishing events.

    This is implemented by infrastructure adapters (e.g., GooglePubSubPublisher).
    The core domain depends on this interface, not on concrete implementations.

    The domain layer works with domain objects (FrameIOEvent). The infrastructure
    adapter is responsible for serialization.
    """

    async def publish(self, event: FrameIOEvent) -> Optional[str]:
        """
        Publish a domain event asynchronously.

        Args:
            event: The domain event to publish

        Returns:
            Message ID if successful, None otherwise
        """
        ...

    def close(self) -> None:
        """Close the publisher and cleanup resources."""
        ...
