"""Artwork scanner service for detecting missing/incorrect artwork."""

import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx
from PIL import Image

from services.plex_service import PlexService, PlexItem

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Types of artwork issues that can be detected."""
    NO_MATCH = "no_match"
    NO_POSTER = "no_poster"
    NO_BACKGROUND = "no_background"
    NO_LOGO = "no_logo"
    PLACEHOLDER_POSTER = "placeholder_poster"
    PLACEHOLDER_BACKGROUND = "placeholder_background"


@dataclass
class ArtworkIssue:
    """Represents a detected artwork issue."""
    issue_type: IssueType
    plex_rating_key: str
    plex_guid: Optional[str]
    title: str
    year: Optional[int]
    media_type: str
    library_name: str
    external_ids: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)


class ArtworkScanner:
    """Scans Plex items for artwork issues."""
    
    # Standard poster aspect ratio is 2:3 (width:height = 0.667)
    POSTER_ASPECT_RATIO = 0.667
    ASPECT_RATIO_TOLERANCE = 0.15
    
    # Background aspect ratio is typically 16:9 (width:height = 1.778)
    BACKGROUND_ASPECT_RATIO = 1.778
    
    def __init__(
        self,
        plex: PlexService,
        check_posters: bool = True,
        check_backgrounds: bool = True,
        check_logos: bool = True,
        check_unmatched: bool = True,
        check_placeholders: bool = True,
    ):
        """
        Initialize artwork scanner.
        
        Args:
            plex: PlexService instance for API calls
            check_posters: Check for missing posters
            check_backgrounds: Check for missing backgrounds
            check_logos: Check for missing logos
            check_unmatched: Check for unmatched items
            check_placeholders: Check for placeholder artwork (wrong aspect ratio)
        """
        self.plex = plex
        self.check_posters = check_posters
        self.check_backgrounds = check_backgrounds
        self.check_logos = check_logos
        self.check_unmatched = check_unmatched
        self.check_placeholders = check_placeholders
        
        # HTTP client for fetching images
        self._client: Optional[httpx.AsyncClient] = None
        
        # Cache for aspect ratio checks to avoid repeated fetches
        self._aspect_ratio_cache: dict[str, float] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def scan_item(self, item: PlexItem) -> list[ArtworkIssue]:
        """
        Scan a single Plex item for artwork issues.
        
        Args:
            item: PlexItem to scan
            
        Returns:
            List of detected ArtworkIssue objects
        """
        issues: list[ArtworkIssue] = []
        
        # Check for unmatched item
        if self.check_unmatched and not item.is_matched:
            issues.append(self._create_issue(item, IssueType.NO_MATCH))
            # If unmatched, we typically can't fix artwork, so return early
            return issues
        
        # Check for missing poster
        if self.check_posters and not item.has_poster:
            issues.append(self._create_issue(item, IssueType.NO_POSTER))
        
        # Check for missing background
        if self.check_backgrounds and not item.has_background:
            issues.append(self._create_issue(item, IssueType.NO_BACKGROUND))
        
        # Check for placeholder poster (wrong aspect ratio)
        if self.check_placeholders and item.has_poster:
            is_placeholder = await self._check_placeholder_poster(item)
            if is_placeholder:
                ratio = self._aspect_ratio_cache.get(item.thumb, 0)
                issues.append(self._create_issue(
                    item,
                    IssueType.PLACEHOLDER_POSTER,
                    details={"detected_aspect_ratio": ratio}
                ))
        
        # Check for placeholder background
        if self.check_placeholders and item.has_background:
            is_placeholder = await self._check_placeholder_background(item)
            if is_placeholder:
                ratio = self._aspect_ratio_cache.get(item.art, 0)
                issues.append(self._create_issue(
                    item,
                    IssueType.PLACEHOLDER_BACKGROUND,
                    details={"detected_aspect_ratio": ratio}
                ))
        
        return issues
    
    def _create_issue(
        self,
        item: PlexItem,
        issue_type: IssueType,
        details: Optional[dict] = None,
    ) -> ArtworkIssue:
        """Create an ArtworkIssue from a PlexItem."""
        external_ids = {}
        
        # Extract external IDs
        tmdb_id = item.get_external_id("tmdb")
        if tmdb_id:
            external_ids["tmdb"] = tmdb_id
        
        imdb_id = item.get_external_id("imdb")
        if imdb_id:
            external_ids["imdb"] = imdb_id
        
        tvdb_id = item.get_external_id("tvdb")
        if tvdb_id:
            external_ids["tvdb"] = tvdb_id
        
        return ArtworkIssue(
            issue_type=issue_type,
            plex_rating_key=item.rating_key,
            plex_guid=item.guid,
            title=item.title,
            year=item.year,
            media_type=item.type,
            library_name=item.library_name,
            external_ids=external_ids,
            details=details or {},
        )
    
    async def _get_image_aspect_ratio(self, image_path: str) -> Optional[float]:
        """
        Fetch image and calculate aspect ratio.
        
        Args:
            image_path: Plex image path (e.g., /library/metadata/123/thumb)
            
        Returns:
            Aspect ratio (width/height) or None if fetch failed
        """
        # Check cache first
        if image_path in self._aspect_ratio_cache:
            return self._aspect_ratio_cache[image_path]
        
        try:
            # Build full URL
            url = await self.plex.get_poster_url("", image_path)
            
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            
            # Load image and get dimensions
            image_data = io.BytesIO(response.content)
            with Image.open(image_data) as img:
                width, height = img.size
                
                if height == 0:
                    return None
                
                ratio = width / height
                self._aspect_ratio_cache[image_path] = ratio
                return ratio
                
        except Exception as e:
            logger.warning(f"Failed to get aspect ratio for {image_path}: {e}")
            return None
    
    async def _check_placeholder_poster(self, item: PlexItem) -> bool:
        """
        Check if poster is a video screenshot (placeholder).
        
        Video screenshots are typically landscape (16:9) while posters
        should be portrait (2:3).
        
        Returns:
            True if poster appears to be a placeholder
        """
        if not item.thumb:
            return False
        
        ratio = await self._get_image_aspect_ratio(item.thumb)
        if ratio is None:
            return False
        
        # Landscape ratio (> 1.0) = video screenshot, not a poster
        if ratio > 1.0:
            return True
        
        # Check if close to standard poster ratio
        min_valid = self.POSTER_ASPECT_RATIO * (1 - self.ASPECT_RATIO_TOLERANCE)
        max_valid = self.POSTER_ASPECT_RATIO * (1 + self.ASPECT_RATIO_TOLERANCE)
        
        # If within valid range, it's a proper poster
        if min_valid <= ratio <= max_valid:
            return False
        
        # Outside valid range but still portrait - might be non-standard but not placeholder
        # Only flag if clearly wrong (very wide or very narrow)
        if ratio > 0.9 or ratio < 0.4:
            return True
        
        return False
    
    async def _check_placeholder_background(self, item: PlexItem) -> bool:
        """
        Check if background is a placeholder or invalid.
        
        Returns:
            True if background appears to be a placeholder
        """
        if not item.art:
            return False
        
        ratio = await self._get_image_aspect_ratio(item.art)
        if ratio is None:
            return False
        
        # Background should be landscape (>1.0)
        # If it's portrait, something is wrong
        if ratio < 1.0:
            return True
        
        # If it's very narrow (like a poster stretched), flag it
        if ratio < 1.2:
            return True
        
        return False
    
    def clear_cache(self):
        """Clear the aspect ratio cache."""
        self._aspect_ratio_cache.clear()
