import logging
import time
from typing import List, Optional

import httpx

from models.schemas import ArtworkType, MediaType, Provider
from services.providers.base import ArtworkResult, BaseProvider

logger = logging.getLogger(__name__)


class TVDBProvider(BaseProvider):
    """TVDB artwork provider (API v4)."""

    BASE_URL = "https://api4.thetvdb.com/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    @property
    def provider_name(self) -> Provider:
        return Provider.TVDB

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_token(self, client: httpx.AsyncClient) -> Optional[str]:
        """Get or refresh JWT token."""
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        try:
            # Login
            response = await client.post(
                f"{self.BASE_URL}/login",
                json={"apikey": self.api_key},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and "token" in data["data"]:
                self._token = data["data"]["token"]
                # Token usually lasts 1 month, but let's be safe and say 24 hours for refresh logic
                self._token_expires_at = now + (24 * 3600) 
                return self._token
                
        except Exception as e:
            logger.error(f"Failed to authenticate with TVDB: {e}")
            
        return None

    async def get_artwork(
        self,
        media_type: MediaType,
        external_ids: dict[str, str],
        artwork_types: List[ArtworkType],
    ) -> List[ArtworkResult]:
        """Fetch artwork from TVDB."""
        if not self.is_configured():
            return []

        # TVDB ID is preferred
        tvdb_id = external_ids.get("tvdb")
        
        # If no TVDB ID, we can't do much easily without search
        if not tvdb_id:
            # Could search by IMDB/TMDB but TVDB v4 search is specific
            return []
            
        endpoint_type = "series" if media_type == MediaType.SHOW else "movies"
        # Note: Season/Episode support would need different logic
        
        if media_type not in [MediaType.MOVIE, MediaType.SHOW]:
            return []

        async with httpx.AsyncClient() as client:
            token = await self._get_token(client)
            if not token:
                return []
                
            headers = {"Authorization": f"Bearer {token}"}
            
            # Use the /artwork/types endpoint or the entity extended record
            # Fetching the entity extended record with artwork is usually best
            url = f"{self.BASE_URL}/{endpoint_type}/{tvdb_id}/extended"
            
            try:
                response = await client.get(
                    url, 
                    headers=headers,
                    params={"meta": "translations"}, # artwork is included in extended? Or separate?
                    # v4: /series/{id}/extended response includes 'artworks' list
                    timeout=10.0
                )
                
                if response.status_code == 404:
                    return []
                    
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data, artwork_types)

            except httpx.HTTPError as e:
                logger.error(f"TVDB request failed: {e}")
                return []
            except Exception as e:
                logger.exception(f"Unexpected error calling TVDB: {e}")
                return []

    def _parse_response(
        self, 
        data: dict, 
        artwork_types: List[ArtworkType]
    ) -> List[ArtworkResult]:
        results = []
        
        if "data" not in data or "artworks" not in data["data"]:
            return []
            
        artworks = data["data"]["artworks"]
        
        # Mapping
        # TVDB types: 1=poster, 2=fanart(background), 3=season poster, ..., 23=logo? 
        # Actually v4 returns 'type' as integer. Need mapping.
        # Common types:
        # 1: Person
        # 2: Comic Cover
        # 3: Poster
        # 4: Background (Fanart)
        # 5: Season Poster
        # 6: Season Banner
        # 7: Season Background
        # 8: Box Art
        # 13: Icon? 
        # 22: Clearlogo
        # 23: Clearart
        
        # Simplified mapping based on observation/docs
        type_map_id = {
            3: ArtworkType.POSTER,     # Series Poster
            4: ArtworkType.BACKGROUND, # Series Background
            22: ArtworkType.LOGO,      # Clearlogo
            23: ArtworkType.LOGO,      # Clearart (also usable as logo often)
        }
        
        # Also need to check movie mapping if different
        
        wanted_types = set(artwork_types)
        
        for item in artworks:
            art_type_id = item.get("type")
            mapped_type = type_map_id.get(art_type_id)
            
            if mapped_type and mapped_type in wanted_types:
                # Calculate score
                score = item.get("score", 0)
                
                image_url = item.get("image")
                if not image_url:
                    continue
                    
                results.append(
                    ArtworkResult(
                        source=Provider.TVDB,
                        artwork_type=mapped_type,
                        image_url=image_url,
                        thumbnail_url=item.get("thumbnail"),
                        language=item.get("language"),
                        score=int(score), # TVDB score is distinct
                        set_name=None,
                        creator_name=None
                    )
                )
        
        return results

    async def test_connection(self) -> bool:
        if not self.is_configured():
            return False
            
        async with httpx.AsyncClient() as client:
            token = await self._get_token(client)
            return bool(token)
