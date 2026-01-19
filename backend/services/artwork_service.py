import asyncio
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import ArtworkType, MediaType, Provider
from services.config_service import ConfigService
from services.providers.base import ArtworkResult, BaseProvider
from services.providers.fanart import FanartProvider
from services.providers.mediux import MediuxProvider
from services.providers.tmdb import TMDBProvider
from services.providers.tvdb import TVDBProvider

logger = logging.getLogger(__name__)


class ArtworkService:
    """Service to aggregate artwork from multiple providers."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_service = ConfigService(db)
        self.providers: dict[Provider, BaseProvider] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize providers with API keys from config."""
        if self._initialized:
            return

        keys = await self.config_service.get_provider_keys()
        
        # We need actual values, get_provider_keys returns bools.
        # So we fetch individual keys.
        
        fanart_key = await self.config_service.get_provider_key("fanart")
        if fanart_key:
            self.providers[Provider.FANART] = FanartProvider(fanart_key)
            
        mediux_key = await self.config_service.get_provider_key("mediux")
        # Mediux technically optional key?
        self.providers[Provider.MEDIUX] = MediuxProvider(mediux_key or "")
        
        tmdb_key = await self.config_service.get_provider_key("tmdb")
        if tmdb_key:
            self.providers[Provider.TMDB] = TMDBProvider(tmdb_key)
            
        tvdb_key = await self.config_service.get_provider_key("tvdb")
        if tvdb_key:
            self.providers[Provider.TVDB] = TVDBProvider(tvdb_key)

        # Plex provider? 
        # self.providers[Provider.PLEX] = PlexProvider(...) 
        # We'd need PlexService instance or similar. 
        # For now skipping Plex built-in provider as it needs connection context.

        self._initialized = True

    async def get_artwork(
        self,
        media_type: MediaType,
        external_ids: dict[str, str],
        artwork_types: List[ArtworkType],
    ) -> List[ArtworkResult]:
        """
        Fetch artwork from all configured providers.
        Results are sorted by provider priority and internal score.
        """
        if not self._initialized:
            await self.initialize()

        # Get priority order
        priority_list_str = await self.config_service.get_provider_priority()
        # Convert string list to Provider enums
        priority_map = {name: i for i, name in enumerate(priority_list_str)}
        
        tasks = []
        active_providers = []
        
        for provider_enum, provider in self.providers.items():
            if provider.is_configured():
                tasks.append(
                    provider.get_artwork(media_type, external_ids, artwork_types)
                )
                active_providers.append(provider_enum)

        if not tasks:
            return []

        # Run in parallel
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results: List[ArtworkResult] = []
        
        for i, result in enumerate(results_list):
            provider_enum = active_providers[i]
            
            if isinstance(result, Exception):
                logger.error(f"Provider {provider_enum} failed: {result}")
                continue
                
            if isinstance(result, list):
                all_results.extend(result)

        # Sort results
        # Primary sort: Provider Priority (lower index = higher priority)
        # Secondary sort: Score (descending)
        
        def sort_key(item: ArtworkResult):
            # Get priority index, default to high number if not in map
            prio = priority_map.get(item.source.value, 999)
            return (prio, -item.score)

        all_results.sort(key=sort_key)
        
        return all_results

    async def test_provider(self, provider_name: Provider) -> bool:
        """Test a specific provider."""
        if not self._initialized:
            await self.initialize()
            
        provider = self.providers.get(provider_name)
        if not provider:
            return False
            
        return await provider.test_connection()
