from abc import ABC, abstractmethod
from typing import Any, Optional, Dict

class BaseEditionModule(ABC):
    """Base class for edition detection modules."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract edition information from Plex item metadata.
        
        Args:
            item_metadata: The full JSON dictionary of the Plex item metadata 
                           (from /library/metadata/{id}).
                           
        Returns:
            Extracted string or None.
        """
        pass

    def _get_main_media(self, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Helper to get the main Media object (usually the largest bitrate/resolution)."""
        media = metadata.get("Media", [])
        if not media:
            return None
        # Return first media for now, usually best quality is first or we sort
        # Plex usually puts best quality first? Or we can sort by bitrate/resolution.
        # Let's assume index 0 for simplicity, or sort by bitrate.
        return sorted(media, key=lambda x: int(x.get("bitrate", 0)), reverse=True)[0]

    def _get_main_part(self, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Helper to get the main Part object from main Media."""
        media = self._get_main_media(metadata)
        if not media:
            return None
        parts = media.get("Part", [])
        if not parts:
            return None
        return parts[0]
