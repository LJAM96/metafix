import logging
from typing import List, Optional

import httpx

from models.schemas import ArtworkType, MediaType, Provider
from services.providers.base import ArtworkResult, BaseProvider

logger = logging.getLogger(__name__)


class FanartProvider(BaseProvider):
    """Fanart.tv artwork provider."""

    BASE_URL = "http://webservice.fanart.tv/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def provider_name(self) -> Provider:
        return Provider.FANART

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_artwork(
        self,
        media_type: MediaType,
        external_ids: dict[str, str],
        artwork_types: List[ArtworkType],
    ) -> List[ArtworkResult]:
        """Fetch artwork from Fanart.tv."""
        if not self.is_configured():
            logger.warning("Fanart.tv is not configured")
            return []

        # Fanart.tv relies heavily on TMDB ID for movies and TVDB ID for shows
        resource_id = None
        endpoint = None

        if media_type == MediaType.MOVIE:
            resource_id = external_ids.get("tmdb") or external_ids.get("imdb")
            endpoint = "movies"
        elif media_type == MediaType.SHOW:
            resource_id = external_ids.get("tvdb")
            endpoint = "tv"
        
        # Fanart doesn't really support season/episode level lookup via this API easily 
        # usually it returns all show art. We'll skip specific season/episode logic for now
        # unless we want to filter the result.

        if not resource_id or not endpoint:
            logger.debug(f"Missing required ID for Fanart.tv lookup: {media_type} {external_ids}")
            return []

        url = f"{self.BASE_URL}/{endpoint}/{resource_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers={"api-key": self.api_key},
                    timeout=10.0
                )
                
                if response.status_code == 404:
                    logger.debug(f"No artwork found on Fanart.tv for {resource_id}")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data, media_type, artwork_types)
                
            except httpx.HTTPError as e:
                logger.error(f"Fanart.tv request failed: {e}")
                return []
            except Exception as e:
                logger.exception(f"Unexpected error calling Fanart.tv: {e}")
                return []

    def _parse_response(
        self, 
        data: dict, 
        media_type: MediaType, 
        artwork_types: List[ArtworkType]
    ) -> List[ArtworkResult]:
        results = []
        
        # Mapping of MetaFix ArtworkType to Fanart.tv JSON keys
        # Priority order for mapping keys
        type_mapping = {
            ArtworkType.LOGO: ["hdmovielogo", "hdtvlogo", "clearlogo"],
            ArtworkType.POSTER: ["movieposter", "tvposter"],
            ArtworkType.BACKGROUND: ["moviebackground", "showbackground"],
        }

        for art_type in artwork_types:
            fanart_keys = type_mapping.get(art_type, [])
            for key in fanart_keys:
                if key in data:
                    for item in data[key]:
                        # Skip if no URL
                        if not item.get("url"):
                            continue
                            
                        # Basic score calculation based on likes/votes if available
                        # Fanart.tv uses "likes" in some endpoints
                        likes = int(item.get("likes", 0))
                        
                        results.append(
                            ArtworkResult(
                                source=Provider.FANART,
                                artwork_type=art_type,
                                image_url=item["url"],
                                thumbnail_url=item.get("url"), # Fanart doesn't give separate thumbs usually
                                language=item.get("lang"),
                                score=likes,
                                set_name=None, # Fanart doesn't group by sets usually
                                creator_name=None 
                            )
                        )
        
        return results

    async def test_connection(self) -> bool:
        """Test the API key with a known item (e.g. The Matrix)."""
        if not self.is_configured():
            return False
            
        # The Matrix TMDB ID: 603
        url = f"{self.BASE_URL}/movies/603"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers={"api-key": self.api_key},
                    timeout=5.0
                )
                return response.status_code == 200
            except Exception:
                return False
