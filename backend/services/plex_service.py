"""Plex server integration service."""

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PlexLibrary:
    """Represents a Plex library."""
    id: str
    name: str
    type: str  # 'movie', 'show', 'artist', 'photo'
    item_count: int
    uuid: str


@dataclass
class PlexItem:
    """Represents a Plex media item."""
    rating_key: str
    title: str
    year: Optional[int]
    type: str  # 'movie', 'show', 'season', 'episode'
    guid: Optional[str]
    thumb: Optional[str]
    art: Optional[str]
    library_name: str
    added_at: Optional[int]
    
    # For movies
    edition_title: Optional[str] = None
    
    # Extended metadata
    guids: list[str] = None  # External IDs like imdb://, tmdb://, tvdb://
    
    def __post_init__(self):
        if self.guids is None:
            self.guids = []
    
    @property
    def is_matched(self) -> bool:
        """Check if item has a valid metadata match."""
        if not self.guid:
            return False
        return not self.guid.startswith("local://")
    
    @property
    def has_poster(self) -> bool:
        """Check if item has a poster."""
        return bool(self.thumb)
    
    @property
    def has_background(self) -> bool:
        """Check if item has background art."""
        return bool(self.art)
    
    def get_external_id(self, source: str) -> Optional[str]:
        """Get external ID for a specific source (tmdb, imdb, tvdb)."""
        prefix = f"{source}://"
        for guid in self.guids:
            if guid.startswith(prefix):
                return guid[len(prefix):]
        return None


class PlexConnectionError(Exception):
    """Raised when connection to Plex fails."""
    pass


class PlexAuthenticationError(Exception):
    """Raised when Plex authentication fails."""
    pass


class PlexService:
    """Service for interacting with Plex Media Server API."""
    
    def __init__(self, url: str, token: str):
        """Initialize Plex service with server URL and token."""
        self.base_url = url.rstrip("/")
        self.token = token
        self._client: Optional[httpx.AsyncClient] = None
        self._server_name: Optional[str] = None
        self._server_version: Optional[str] = None
    
    @staticmethod
    async def create_pin(client_id: str, product: str = "MetaFix") -> tuple[int, str]:
        """
        Create a new Plex PIN for OAuth.
        
        Returns:
            Tuple of (id, code)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://plex.tv/api/v2/pins",
                headers={
                    "Accept": "application/json",
                },
                params={
                    "strong": "true",
                    "X-Plex-Product": product,
                    "X-Plex-Client-Identifier": client_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["id"], data["code"]

    @staticmethod
    async def check_pin(pin_id: int, code: str, client_id: str) -> Optional[str]:
        """
        Check if a Plex PIN has been authorized.
        
        Returns:
            Auth token if authorized, None otherwise.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://plex.tv/api/v2/pins/{pin_id}",
                headers={
                    "Accept": "application/json",
                },
                params={
                    "code": code,
                    "X-Plex-Client-Identifier": client_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("authToken")

    @staticmethod
    async def get_resources(token: str) -> list[dict]:
        """
        Get list of servers from Plex.tv using auth token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://plex.tv/api/v2/resources",
                headers={
                    "Accept": "application/json",
                    "X-Plex-Token": token,
                },
                params={
                    "includeHttps": "1",
                },
            )
            response.raise_for_status()
            data = response.json()
            
            servers = []
            for resource in data:
                # Check if it provides 'server'
                if "server" in resource.get("provides", ""):
                    servers.append({
                        "name": resource.get("name"),
                        "product": resource.get("product"),
                        "version": resource.get("productVersion"),
                        "connections": resource.get("connections", []),
                    })
            return servers

    @property
    def headers(self) -> dict:
        """Get headers for Plex API requests."""
        return {
            "X-Plex-Token": self.token,
            "Accept": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make a request to Plex API."""
        client = await self._get_client()
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        
        try:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                **kwargs
            )
            
            if response.status_code == 401:
                raise PlexAuthenticationError("Invalid Plex token")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.ConnectError as e:
            raise PlexConnectionError(f"Cannot connect to Plex server: {e}")
        except httpx.TimeoutException:
            raise PlexConnectionError("Connection to Plex server timed out")
        except httpx.HTTPStatusError as e:
            raise PlexConnectionError(f"Plex API error: {e.response.status_code}")
    
    async def test_connection(self) -> tuple[bool, str, Optional[str]]:
        """
        Test connection to Plex server.
        
        Returns:
            Tuple of (success, message, server_name)
        """
        try:
            data = await self._request("GET", "/")
            
            media_container = data.get("MediaContainer", {})
            self._server_name = media_container.get("friendlyName", "Plex Server")
            self._server_version = media_container.get("version")
            
            return True, "Connection successful", self._server_name
            
        except PlexAuthenticationError:
            return False, "Invalid Plex token", None
        except PlexConnectionError as e:
            return False, str(e), None
        except Exception as e:
            logger.exception("Unexpected error testing Plex connection")
            return False, f"Unexpected error: {e}", None
    
    async def get_libraries(self) -> list[PlexLibrary]:
        """Get all libraries from Plex server."""
        data = await self._request("GET", "/library/sections")
        
        logger.info(f"Plex libraries raw response: {data}")
        
        libraries = []
        for section in data.get("MediaContainer", {}).get("Directory", []):
            # Only include video libraries (movies and shows)
            lib_type = section.get("type")
            if lib_type not in ("movie", "show"):
                continue
            
            # Try multiple possible count fields
            item_count = (
                section.get("count") or 
                section.get("size") or 
                section.get("totalSize") or 
                0
            )
            
            logger.info(f"Library '{section.get('title')}': type={lib_type}, count={item_count}, raw_section={section}")
            
            libraries.append(PlexLibrary(
                id=str(section.get("key")),
                name=section.get("title", "Unknown"),
                type=lib_type,
                item_count=item_count,
                uuid=section.get("uuid", ""),
            ))
        
        logger.info(f"Found {len(libraries)} video libraries")
        return libraries
    
    async def get_library_items(
        self,
        library_id: str,
        start: int = 0,
        size: int = 50,
    ) -> tuple[list[PlexItem], int]:
        """
        Get items from a library with pagination.
        
        Returns:
            Tuple of (items, total_count)
        """
        # Get library info first to know the type
        lib_data = await self._request("GET", f"/library/sections/{library_id}")
        lib_info = lib_data.get("MediaContainer", {}).get("Directory", [{}])[0]
        library_name = lib_info.get("title", "Unknown")
        
        # Get items
        data = await self._request(
            "GET",
            f"/library/sections/{library_id}/all",
            params={
                "X-Plex-Container-Start": start,
                "X-Plex-Container-Size": size,
            }
        )
        
        container = data.get("MediaContainer", {})
        total = container.get("totalSize", 0)
        
        items = []
        for item in container.get("Metadata", []):
            # Extract GUIDs
            guids = []
            for guid_obj in item.get("Guid", []):
                guid_id = guid_obj.get("id", "")
                if guid_id:
                    guids.append(guid_id)
            
            items.append(PlexItem(
                rating_key=str(item.get("ratingKey")),
                title=item.get("title", "Unknown"),
                year=item.get("year"),
                type=item.get("type", "movie"),
                guid=item.get("guid"),
                thumb=item.get("thumb"),
                art=item.get("art"),
                library_name=library_name,
                added_at=item.get("addedAt"),
                edition_title=item.get("editionTitle"),
                guids=guids,
            ))
        
        return items, total
    
    async def get_all_library_items(self, library_id: str) -> list[PlexItem]:
        """Get all items from a library (handles pagination)."""
        all_items = []
        start = 0
        size = 100
        
        while True:
            items, total = await self.get_library_items(library_id, start, size)
            all_items.extend(items)
            
            if start + len(items) >= total:
                break
            
            start += size
        
        return all_items
    
    async def get_item_metadata(self, rating_key: str) -> Optional[PlexItem]:
        """Get detailed metadata for a specific item."""
        try:
            data = await self._request("GET", f"/library/metadata/{rating_key}")
            
            container = data.get("MediaContainer", {})
            items = container.get("Metadata", [])
            
            if not items:
                return None
            
            item = items[0]
            
            # Extract GUIDs
            guids = []
            for guid_obj in item.get("Guid", []):
                guid_id = guid_obj.get("id", "")
                if guid_id:
                    guids.append(guid_id)
            
            return PlexItem(
                rating_key=str(item.get("ratingKey")),
                title=item.get("title", "Unknown"),
                year=item.get("year"),
                type=item.get("type", "movie"),
                guid=item.get("guid"),
                thumb=item.get("thumb"),
                art=item.get("art"),
                library_name=container.get("librarySectionTitle", "Unknown"),
                added_at=item.get("addedAt"),
                edition_title=item.get("editionTitle"),
                guids=guids,
            )
            
        except Exception as e:
            logger.warning(f"Failed to get metadata for {rating_key}: {e}")
            return None
    
    async def get_poster_url(self, rating_key: str, thumb_path: str) -> str:
        """Get full URL for a poster image."""
        if thumb_path.startswith("http"):
            return thumb_path
        return f"{self.base_url}{thumb_path}?X-Plex-Token={self.token}"
    
    async def upload_poster(self, rating_key: str, image_url: str) -> bool:
        """Upload a poster to Plex from URL."""
        try:
            await self._request(
                "POST",
                f"/library/metadata/{rating_key}/posters",
                params={"url": image_url}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upload poster for {rating_key}: {e}")
            return False
    
    async def upload_background(self, rating_key: str, image_url: str) -> bool:
        """Upload background art to Plex from URL."""
        try:
            await self._request(
                "POST",
                f"/library/metadata/{rating_key}/arts",
                params={"url": image_url}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upload background for {rating_key}: {e}")
            return False
    
    async def lock_poster(self, rating_key: str) -> bool:
        """Lock the poster field to prevent Plex from changing it."""
        try:
            await self._request(
                "PUT",
                f"/library/metadata/{rating_key}",
                params={"thumb.locked": "1"}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to lock poster for {rating_key}: {e}")
            return False
    
    async def lock_background(self, rating_key: str) -> bool:
        """Lock the background field to prevent Plex from changing it."""
        try:
            await self._request(
                "PUT",
                f"/library/metadata/{rating_key}",
                params={"art.locked": "1"}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to lock background for {rating_key}: {e}")
            return False
    
    async def set_edition(self, rating_key: str, edition_title: str) -> bool:
        """Set the edition title for a movie."""
        try:
            await self._request(
                "PUT",
                f"/library/metadata/{rating_key}",
                params={"editionTitle.value": edition_title}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set edition for {rating_key}: {e}")
            return False
    
    async def get_available_posters(self, rating_key: str) -> list[dict]:
        """Get available posters from Plex's built-in sources."""
        try:
            data = await self._request("GET", f"/library/metadata/{rating_key}/posters")
            
            posters = []
            for item in data.get("MediaContainer", {}).get("Metadata", []):
                posters.append({
                    "url": item.get("key"),
                    "thumb": item.get("thumb"),
                    "provider": item.get("provider", "plex"),
                    "selected": item.get("selected", False),
                })
            
            return posters
            
        except Exception as e:
            logger.warning(f"Failed to get posters for {rating_key}: {e}")
            return []
    
    async def get_available_backgrounds(self, rating_key: str) -> list[dict]:
        """Get available background art from Plex's built-in sources."""
        try:
            data = await self._request("GET", f"/library/metadata/{rating_key}/arts")
            
            backgrounds = []
            for item in data.get("MediaContainer", {}).get("Metadata", []):
                backgrounds.append({
                    "url": item.get("key"),
                    "thumb": item.get("thumb"),
                    "provider": item.get("provider", "plex"),
                    "selected": item.get("selected", False),
                })
            
            return backgrounds
            
        except Exception as e:
            logger.warning(f"Failed to get backgrounds for {rating_key}: {e}")
            return []
