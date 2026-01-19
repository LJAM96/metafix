import logging
from typing import List, Optional

import httpx

from models.schemas import ArtworkType, MediaType, Provider
from services.providers.base import ArtworkResult, BaseProvider

logger = logging.getLogger(__name__)


class MediuxProvider(BaseProvider):
    """Mediux artwork provider (GraphQL)."""

    BASE_URL = "https://staged.mediux.io/graphql"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def provider_name(self) -> Provider:
        return Provider.MEDIUX

    def is_configured(self) -> bool:
        # Mediux technically might work without API key for public queries?
        # Plan says "Auth: API Key (user-provided)"
        # But commonly Mediux is open. We'll require key if user provided it, or maybe just proceed.
        # Let's enforce key if the plan says so.
        return bool(self.api_key)

    async def get_artwork(
        self,
        media_type: MediaType,
        external_ids: dict[str, str],
        artwork_types: List[ArtworkType],
    ) -> List[ArtworkResult]:
        """Fetch artwork from Mediux."""
        if not self.is_configured():
            return []

        tmdb_id = external_ids.get("tmdb")
        if not tmdb_id:
            return []
            
        # Mediux ID format: "tmdb-123"
        mediux_id = f"tmdb-{tmdb_id}"
        
        query = self._build_query(media_type, artwork_types)
        variables = {"id": mediux_id}
        
        async with httpx.AsyncClient() as client:
            try:
                # Add headers if API key is used
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["x-api-key"] = self.api_key # Verify header name. Often 'Authorization' or 'x-api-key'

                response = await client.post(
                    self.BASE_URL,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    logger.warning(f"Mediux GraphQL errors: {data['errors']}")
                    return []
                    
                return self._parse_response(data, media_type, artwork_types)

            except httpx.HTTPError as e:
                logger.error(f"Mediux request failed: {e}")
                return []
            except Exception as e:
                logger.exception(f"Unexpected error calling Mediux: {e}")
                return []

    def _build_query(self, media_type: MediaType, artwork_types: List[ArtworkType]) -> str:
        """Build GraphQL query."""
        # Simple query fetching sets and files
        
        if media_type == MediaType.SHOW:
            root_field = "shows_by_id"
            set_field = "show_sets"
        else:
            root_field = "movies_by_id"
            set_field = "movie_sets"
        
        # We need to fetch sets.
        return """
        query getArtwork($id: ID!) {
            result: """ + root_field + """(id: $id) {
                id
                title
                sets: """ + set_field + """ {
                    id
                    name: set_title
                    user: user_created {
                        username
                    }
                    files {
                        id
                        type: file_type
                        url: id
                    }
                }
            }
        }
        """
        # Note: 'url: id' because Mediux constructs URL from ID usually: https://api.mediux.io/assets/{id}
        # But let's check if we can get full URL. Usually we get ID and construct it.
        # Plan says: "Assets: GET /assets/{fileId}"

    def _parse_response(
        self, 
        data: dict, 
        media_type: MediaType, 
        artwork_types: List[ArtworkType]
    ) -> List[ArtworkResult]:
        results = []
        
        if not data.get("data") or not data["data"].get("result"):
            return []
            
        result = data["data"]["result"]
        sets = result.get("sets", [])
        
        # Mapping
        type_mapping = {
            "poster": ArtworkType.POSTER,
            "background": ArtworkType.BACKGROUND,
            "title_card": ArtworkType.BACKGROUND, # Maybe?
            "logo": ArtworkType.LOGO,
            "clear_logo": ArtworkType.LOGO
        }
        
        wanted_types = set(artwork_types)
        
        for art_set in sets:
            set_name = art_set.get("name")
            creator = art_set.get("user", {}).get("username")
            files = art_set.get("files", [])
            
            for file in files:
                file_type = file.get("type")
                mapped_type = type_mapping.get(file_type)
                
                if mapped_type and mapped_type in wanted_types:
                    file_id = file.get("id")
                    if not file_id:
                        continue
                        
                    # Construct URL
                    # Plan says GET /assets/{fileId}. 
                    # Usually: https://api.mediux.io/assets/{fileId}
                    # Or staged.mediux.io/assets/{fileId}
                    # Let's use the base domain from BASE_URL
                    base_domain = self.BASE_URL.replace("/graphql", "")
                    image_url = f"{base_domain}/assets/{file_id}"
                    
                    results.append(
                        ArtworkResult(
                            source=Provider.MEDIUX,
                            artwork_type=mapped_type,
                            image_url=image_url,
                            thumbnail_url=f"{image_url}?width=400", # Guessing thumbnail param
                            language="en", # Mediux is mostly English
                            score=0, # No explicit score
                            set_name=set_name,
                            creator_name=creator
                        )
                    )
        
        return results

    async def test_connection(self) -> bool:
        # Simple query to test
        query = """
        query {
            __typename
        }
        """
        async with httpx.AsyncClient() as client:
            try:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["x-api-key"] = self.api_key
                
                response = await client.post(
                    self.BASE_URL,
                    json={"query": query},
                    headers=headers,
                    timeout=5.0
                )
                return response.status_code == 200
            except Exception:
                return False
