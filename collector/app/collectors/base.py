from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Listener


class BaseCollector(ABC):
    """Abstract base class for platform collectors."""

    platform: str = "unknown"

    @abstractmethod
    async def collect(self, listener: Listener, session: AsyncSession) -> int:
        """
        Collect posts for a given listener.

        Args:
            listener: The listener configuration
            session: Database session for storing posts

        Returns:
            Number of new posts collected
        """
        pass

    @abstractmethod
    async def is_configured(self) -> bool:
        """Check if the collector has valid credentials configured."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the platform API."""
        pass
