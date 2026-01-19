import json
import logging
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import EditionBackup, EditionConfig
from services.config_service import ConfigService
from services.plex_service import PlexService
from services.edition.modules.base import BaseEditionModule
from services.edition.modules.video import (
    ResolutionModule, DynamicRangeModule, VideoCodecModule, BitrateModule, FrameRateModule
)
from services.edition.modules.audio import AudioCodecModule, AudioChannelsModule
from services.edition.modules.content import (
    CutModule, ReleaseModule, SourceModule, ShortFilmModule, SpecialFeaturesModule
)
from services.edition.modules.metadata import (
    ContentRatingModule, DurationModule, RatingModule, DirectorModule, 
    WriterModule, GenreModule, CountryModule, StudioModule, LanguageModule, SizeModule
)

logger = logging.getLogger(__name__)

class EditionManager:
    """Service to manage edition metadata generation and application."""

    MODULE_REGISTRY: Dict[str, Type[BaseEditionModule]] = {
        "Resolution": ResolutionModule,
        "DynamicRange": DynamicRangeModule,
        "VideoCodec": VideoCodecModule,
        "Bitrate": BitrateModule,
        "FrameRate": FrameRateModule,
        "AudioCodec": AudioCodecModule,
        "AudioChannels": AudioChannelsModule,
        "Cut": CutModule,
        "Release": ReleaseModule,
        "Source": SourceModule,
        "ShortFilm": ShortFilmModule,
        "SpecialFeatures": SpecialFeaturesModule,
        "ContentRating": ContentRatingModule,
        "Duration": DurationModule,
        "Rating": RatingModule,
        "Director": DirectorModule,
        "Writer": WriterModule,
        "Genre": GenreModule,
        "Country": CountryModule,
        "Studio": StudioModule,
        "Language": LanguageModule,
        "Size": SizeModule,
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_service = ConfigService(db)
        self._plex_service: Optional[PlexService] = None

    async def _get_plex_service(self) -> PlexService:
        if not self._plex_service:
            url, token, _ = await self.config_service.get_plex_config()
            if not url or not token:
                raise ValueError("Plex not configured")
            self._plex_service = PlexService(url, token)
        return self._plex_service

    async def get_config(self) -> Dict[str, Any]:
        """Get edition configuration."""
        result = await self.db.execute(select(EditionConfig).where(EditionConfig.id == 1))
        config = result.scalar_one_or_none()
        
        all_modules = list(self.MODULE_REGISTRY.keys())
        default_enabled = ["Resolution", "DynamicRange", "AudioCodec", "AudioChannels", "Cut", "Release"]
        
        if not config:
            return {
                "enabled_modules": default_enabled,
                "module_order": all_modules,
                "settings": {
                    "separator": " . ",
                    "excluded_languages": ["English"]
                }
            }
            
        saved_order = json.loads(config.module_order)
        # Ensure all available modules are in the list
        for m in all_modules:
            if m not in saved_order:
                saved_order.append(m)
                
        return {
            "enabled_modules": json.loads(config.enabled_modules),
            "module_order": saved_order,
            "settings": json.loads(config.settings)
        }

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update edition configuration."""
        result = await self.db.execute(select(EditionConfig).where(EditionConfig.id == 1))
        config = result.scalar_one_or_none()
        
        if not config:
            config = EditionConfig(id=1)
            self.db.add(config)
            
        config.enabled_modules = json.dumps(new_config.get("enabled_modules", []))
        config.module_order = json.dumps(new_config.get("module_order", []))
        config.settings = json.dumps(new_config.get("settings", {}))
        
        await self.db.flush()

    async def generate_edition(self, rating_key: str) -> Optional[str]:
        """Generate edition string for a Plex item."""
        plex = await self._get_plex_service()
        
        # Get full metadata directly using internal client method to get raw JSON
        # PlexService.get_item_metadata returns PlexItem object which is limited.
        # We need raw response. Accessing private method _request or adding a public one.
        # Ideally we add a public method `get_raw_metadata` to PlexService.
        # For now, I'll use the private one assuming I can access it or extend it.
        # Python allows access.
        
        try:
            data = await plex._request("GET", f"/library/metadata/{rating_key}")
            container = data.get("MediaContainer", {})
            items = container.get("Metadata", [])
            if not items:
                return None
            metadata = items[0]
        except Exception as e:
            logger.error(f"Failed to fetch metadata for {rating_key}: {e}")
            return None

        config = await self.get_config()
        enabled_modules = set(config["enabled_modules"])
        module_order = config["module_order"]
        settings = config["settings"]
        separator = settings.get("separator", " . ")
        
        parts = []
        
        # Iterate in order
        for module_name in module_order:
            if module_name not in enabled_modules:
                continue
                
            module_class = self.MODULE_REGISTRY.get(module_name)
            if not module_class:
                continue
                
            try:
                module = module_class(settings)
                value = module.extract(metadata)
                if value:
                    parts.append(value)
            except Exception as e:
                logger.warning(f"Module {module_name} failed for {rating_key}: {e}")
                
        if not parts:
            return None
            
        return separator.join(parts)

    async def apply_edition(self, rating_key: str, edition_string: str) -> bool:
        """Apply edition string to Plex item."""
        plex = await self._get_plex_service()
        
        # Backup first
        await self.backup_edition(rating_key)
        
        return await plex.set_edition(rating_key, edition_string)

    async def backup_edition(self, rating_key: str) -> None:
        """Backup current edition title."""
        # Check if already backed up
        result = await self.db.execute(
            select(EditionBackup).where(EditionBackup.plex_rating_key == rating_key)
        )
        if result.scalar_one_or_none():
            return

        plex = await self._get_plex_service()
        item = await plex.get_item_metadata(rating_key)
        
        if not item:
            return
            
        backup = EditionBackup(
            plex_rating_key=rating_key,
            title=item.title,
            original_edition=item.edition_title
        )
        self.db.add(backup)
        await self.db.flush()

    async def restore_edition(self, rating_key: str) -> bool:
        """Restore edition from backup."""
        result = await self.db.execute(
            select(EditionBackup).where(EditionBackup.plex_rating_key == rating_key)
        )
        backup = result.scalar_one_or_none()
        
        if not backup:
            return False
            
        plex = await self._get_plex_service()
        # Restore (edition_title can be None, set_edition handles it? Plex API expects empty string to clear)
        target_edition = backup.original_edition or ""
        return await plex.set_edition(rating_key, target_edition)
