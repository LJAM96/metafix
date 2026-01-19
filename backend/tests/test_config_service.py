"""Tests for ConfigService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.config_service import ConfigService


class TestConfigService:
    """Tests for ConfigService."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_value(self, test_session: AsyncSession):
        """Can set and retrieve a configuration value."""
        config = ConfigService(test_session)
        
        await config.set("test_key", "test_value")
        await test_session.flush()
        
        result = await config.get("test_key")
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_default(self, test_session: AsyncSession):
        """Getting nonexistent key returns default."""
        config = ConfigService(test_session)
        
        result = await config.get("nonexistent", "default_value")
        assert result == "default_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, test_session: AsyncSession):
        """Getting nonexistent key without default returns None."""
        config = ConfigService(test_session)
        
        result = await config.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_encrypted_value(self, test_session: AsyncSession):
        """Encrypted values are stored encrypted but retrieved decrypted."""
        config = ConfigService(test_session)
        
        await config.set("secret_key", "secret_value", encrypted=True)
        await test_session.flush()
        
        # Retrieved value should be decrypted
        result = await config.get("secret_key")
        assert result == "secret_value"
    
    @pytest.mark.asyncio
    async def test_update_existing_value(self, test_session: AsyncSession):
        """Updating existing key overwrites value."""
        config = ConfigService(test_session)
        
        await config.set("key", "value1")
        await test_session.flush()
        
        await config.set("key", "value2")
        await test_session.flush()
        
        result = await config.get("key")
        assert result == "value2"
    
    @pytest.mark.asyncio
    async def test_delete_value(self, test_session: AsyncSession):
        """Can delete a configuration value."""
        config = ConfigService(test_session)
        
        await config.set("to_delete", "value")
        await test_session.flush()
        
        deleted = await config.delete("to_delete")
        assert deleted is True
        
        result = await config.get("to_delete")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, test_session: AsyncSession):
        """Deleting nonexistent key returns False."""
        config = ConfigService(test_session)
        
        deleted = await config.delete("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing(self, test_session: AsyncSession):
        """Exists returns True for existing key."""
        config = ConfigService(test_session)
        
        await config.set("exists_key", "value")
        await test_session.flush()
        
        assert await config.exists("exists_key") is True
    
    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent(self, test_session: AsyncSession):
        """Exists returns False for nonexistent key."""
        config = ConfigService(test_session)
        
        assert await config.exists("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_plex_config_roundtrip(self, test_session: AsyncSession):
        """Plex configuration can be saved and retrieved."""
        config = ConfigService(test_session)
        
        await config.set_plex_config(
            url="http://localhost:32400",
            token="my-plex-token",
            server_name="My Server"
        )
        await test_session.flush()
        
        url, token, server_name = await config.get_plex_config()
        
        assert url == "http://localhost:32400"
        assert token == "my-plex-token"  # Token should be decrypted
        assert server_name == "My Server"
    
    @pytest.mark.asyncio
    async def test_is_plex_configured(self, test_session: AsyncSession):
        """is_plex_configured returns correct status."""
        config = ConfigService(test_session)
        
        # Initially not configured
        assert await config.is_plex_configured() is False
        
        # After setting config
        await config.set_plex_config("http://localhost:32400", "token", "Server")
        await test_session.flush()
        
        assert await config.is_plex_configured() is True
    
    @pytest.mark.asyncio
    async def test_provider_priority(self, test_session: AsyncSession):
        """Provider priority can be saved and retrieved."""
        config = ConfigService(test_session)
        
        # Default priority
        priority = await config.get_provider_priority()
        assert priority == ["fanart", "mediux", "tmdb", "tvdb", "plex"]
        
        # Set custom priority
        custom_priority = ["tmdb", "fanart", "plex"]
        await config.set_provider_priority(custom_priority)
        await test_session.flush()
        
        priority = await config.get_provider_priority()
        assert priority == custom_priority
