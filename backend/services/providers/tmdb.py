import logging
from typing import List, Optional

import httpx

from models.schemas import ArtworkType, MediaType, Provider
from services.providers.base import ArtworkResult, BaseProvider

logger = logging.getLogger(__name__)


class TMDBProvider(BaseProvider):
    """TMDB artwork provider."""

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Cache configuration
        self._config_cache = None

    @property
    def provider_name(self) -> Provider:
        return Provider.TMDB

    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def _get_image_base_url(self, client: httpx.AsyncClient) -> str:
        """Fetch and cache TMDB image base URL."""
        if self._config_cache:
            return self._config_cache

        try:
            response = await client.get(
                f"{self.BASE_URL}/configuration",
                params={"api_key": self.api_key}
            )
            response.raise_for_status()
            data = response.json()
            base_url = data.get("images", {}).get("secure_base_url")
            if base_url:
                self._config_cache = base_url
                return base_url
        except Exception as e:
            logger.warning(f"Failed to fetch TMDB configuration: {e}")
        
        # Fallback
        return self.IMAGE_BASE_URL

    async def get_artwork(
        self,
        media_type: MediaType,
        external_ids: dict[str, str],
        artwork_types: List[ArtworkType],
    ) -> List[ArtworkResult]:
        """Fetch artwork from TMDB."""
        if not self.is_configured():
            return []

        tmdb_id = external_ids.get("tmdb")
        # Can lookup by IMDB/TVDB if TMDB ID missing via /find endpoint, but for now assume TMDB ID is present
        # or we might need to implement the lookup.
        # Plex usually has TMDB ID.
        
        if not tmdb_id:
            # Try to find by IMDB ID
            imdb_id = external_ids.get("imdb")
            if imdb_id:
                tmdb_id = await self._find_tmdb_id(imdb_id, "imdb_id")
            
            # If still no ID, try TVDB for shows
            if not tmdb_id and media_type == MediaType.SHOW:
                tvdb_id = external_ids.get("tvdb")
                if tvdb_id:
                    tmdb_id = await self._find_tmdb_id(tvdb_id, "tvdb_id")

        if not tmdb_id:
             logger.debug(f"Missing TMDB ID for lookup: {media_type} {external_ids}")
             return []

        endpoint_type = "movie" if media_type == MediaType.MOVIE else "tv"
        url = f"{self.BASE_URL}/{endpoint_type}/{tmdb_id}/images"

        async with httpx.AsyncClient() as client:
            try:
                base_image_url = await self._get_image_base_url(client)
                
                # Include languages? "include_image_language=en,null" gets English and no-text
                params = {
                    "api_key": self.api_key,
                    "include_image_language": "en,null" 
                }
                
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code == 404:
                    return []
                    
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data, base_image_url, artwork_types)

            except httpx.HTTPError as e:
                logger.error(f"TMDB request failed: {e}")
                return []
            except Exception as e:
                logger.exception(f"Unexpected error calling TMDB: {e}")
                return []

    async def _find_tmdb_id(self, external_id: str, external_source: str) -> Optional[str]:
        """Resolve external ID to TMDB ID."""
        url = f"{self.BASE_URL}/find/{external_id}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    params={"api_key": self.api_key, "external_source": external_source}
                )
                if response.status_code == 200:
                    data = response.json()
                    # Check results
                    if data.get("movie_results"):
                        return str(data["movie_results"][0]["id"])
                    if data.get("tv_results"):
                        return str(data["tv_results"][0]["id"])
            except Exception:
                pass
        return None

    def _parse_response(
        self, 
        data: dict, 
        base_url: str,
        artwork_types: List[ArtworkType]
    ) -> List[ArtworkResult]:
        results = []
        
        # Mapping
        # TMDB keys: posters, backdrops, logos
        type_mapping = {
            ArtworkType.POSTER: "posters",
            ArtworkType.BACKGROUND: "backdrops",
            ArtworkType.LOGO: "logos"
        }

        for art_type in artwork_types:
            key = type_mapping.get(art_type)
            if key and key in data:
                for item in data[key]:
                    file_path = item.get("file_path")
                    if not file_path:
                        continue
                        
                    # Size handling. 'original' is safest for high quality.
                    # Could optimize by picking w1280 or similar.
                    image_url = f"{base_url}original{file_path}"
                    
                    # For thumbnails, use smaller size
                    thumb_url = f"{base_url}w500{file_path}"
                    
                    results.append(
                        ArtworkResult(
                            source=Provider.TMDB,
                            artwork_type=art_type,
                            image_url=image_url,
                            thumbnail_url=thumb_url,
                            language=item.get("iso_639_1"),
                            score=int(item.get("vote_average", 0) * 10), # Scale 0-10 to roughly 0-100 logic or just usage count? 
                            # TMDB vote_average is 0-10.
                            set_name=None,
                            creator_name=None
                        )
                    )
        
        return results

    async def test_connection(self) -> bool:
        """Test API key."""
        if not self.is_configured():
            return False
        
        url = f"{self.BASE_URL}/configuration"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params={"api_key": self.api_key})
                return response.status_code == 200
            except Exception:
                return False
