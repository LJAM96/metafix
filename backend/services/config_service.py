"""Configuration storage service."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Config
from services.encryption import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


# Config keys
PLEX_URL = "plex_url"
PLEX_TOKEN = "plex_token"
PLEX_SERVER_NAME = "plex_server_name"
PROVIDER_PRIORITY = "provider_priority"
FANART_API_KEY = "fanart_api_key"
MEDIUX_API_KEY = "mediux_api_key"
TMDB_API_KEY = "tmdb_api_key"
TVDB_API_KEY = "tvdb_api_key"


class ConfigService:
    """Service for managing application configuration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value."""
        result = await self.db.execute(
            select(Config).where(Config.key == key)
        )
        config = result.scalar_one_or_none()
        
        if config is None:
            return default
        
        # Decrypt if encrypted
        if config.encrypted:
            return decrypt_value(config.value)
        
        return config.value
    
    async def set(self, key: str, value: str, encrypted: bool = False) -> None:
        """Set a configuration value."""
        # Check if exists
        result = await self.db.execute(
            select(Config).where(Config.key == key)
        )
        config = result.scalar_one_or_none()
        
        # Encrypt if needed
        stored_value = encrypt_value(value) if encrypted else value
        
        if config:
            config.value = stored_value
            config.encrypted = encrypted
        else:
            config = Config(
                key=key,
                value=stored_value,
                encrypted=encrypted,
            )
            self.db.add(config)
        
        await self.db.flush()
    
    async def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        result = await self.db.execute(
            select(Config).where(Config.key == key)
        )
        config = result.scalar_one_or_none()
        
        if config:
            await self.db.delete(config)
            await self.db.flush()
            return True
        
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if a configuration key exists."""
        result = await self.db.execute(
            select(Config).where(Config.key == key)
        )
        return result.scalar_one_or_none() is not None
    
    # Plex configuration helpers
    async def get_plex_config(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get Plex configuration (url, token, server_name)."""
        url = await self.get(PLEX_URL)
        token = await self.get(PLEX_TOKEN)
        server_name = await self.get(PLEX_SERVER_NAME)
        return url, token, server_name
    
    async def set_plex_config(self, url: str, token: str, server_name: str) -> None:
        """Save Plex configuration."""
        await self.set(PLEX_URL, url, encrypted=False)
        await self.set(PLEX_TOKEN, token, encrypted=True)  # Token is encrypted
        await self.set(PLEX_SERVER_NAME, server_name, encrypted=False)
    
    async def is_plex_configured(self) -> bool:
        """Check if Plex is configured."""
        url = await self.get(PLEX_URL)
        token = await self.get(PLEX_TOKEN)
        return bool(url and token)
    
    # Provider API keys helpers
    async def get_provider_keys(self) -> dict:
        """Get all provider API keys (without actual values for security)."""
        return {
            "fanart": bool(await self.get(FANART_API_KEY)),
            "mediux": bool(await self.get(MEDIUX_API_KEY)),
            "tmdb": bool(await self.get(TMDB_API_KEY)),
            "tvdb": bool(await self.get(TVDB_API_KEY)),
        }
    
    async def get_provider_key(self, provider: str) -> Optional[str]:
        """Get a specific provider API key."""
        key_map = {
            "fanart": FANART_API_KEY,
            "mediux": MEDIUX_API_KEY,
            "tmdb": TMDB_API_KEY,
            "tvdb": TVDB_API_KEY,
        }
        config_key = key_map.get(provider)
        if config_key:
            return await self.get(config_key)
        return None
    
    async def set_provider_key(self, provider: str, api_key: str) -> None:
        """Set a provider API key."""
        key_map = {
            "fanart": FANART_API_KEY,
            "mediux": MEDIUX_API_KEY,
            "tmdb": TMDB_API_KEY,
            "tvdb": TVDB_API_KEY,
        }
        config_key = key_map.get(provider)
        if config_key:
            await self.set(config_key, api_key, encrypted=True)
    
    async def get_provider_priority(self) -> list[str]:
        """Get provider priority order."""
        import json
        priority_json = await self.get(PROVIDER_PRIORITY)
        if priority_json:
            try:
                return json.loads(priority_json)
            except json.JSONDecodeError:
                pass
        return ["fanart", "mediux", "tmdb", "tvdb", "plex"]
    
    async def set_provider_priority(self, priority: list[str]) -> None:
        """Set provider priority order."""
        import json
        await self.set(PROVIDER_PRIORITY, json.dumps(priority), encrypted=False)
