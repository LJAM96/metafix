from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel

from models.schemas import ArtworkType, MediaType, Provider


class ArtworkResult(BaseModel):
    source: Provider
    artwork_type: ArtworkType
    image_url: str
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    score: int = 0
    set_name: Optional[str] = None
    creator_name: Optional[str] = None


class BaseProvider(ABC):
    """Base interface for all artwork providers."""

    @property
    @abstractmethod
    def provider_name(self) -> Provider:
        """Return the provider enum value."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is configured (has API keys etc)."""
        pass

    @abstractmethod
    async def get_artwork(
        self,
        media_type: MediaType,
        external_ids: dict[str, str],
        artwork_types: List[ArtworkType],
    ) -> List[ArtworkResult]:
        """
        Fetch artwork for the given media.

        Args:
            media_type: Movie, show, season, or episode
            external_ids: Dictionary of IDs (imdb, tmdb, tvdb, etc.)
            artwork_types: List of artwork types to fetch

        Returns:
            List of ArtworkResult objects
        """
        pass

    async def test_connection(self) -> bool:
        """Test if the provider is reachable and credentials work."""
        return self.is_configured()
