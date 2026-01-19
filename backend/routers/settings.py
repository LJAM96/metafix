"""Application settings router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.schemas import Provider, ProviderSettingsRequest, ProviderTestResponse
from services.config_service import ConfigService
from services.artwork_service import ArtworkService

router = APIRouter()


@router.get("/providers")
async def get_provider_settings(db: AsyncSession = Depends(get_db)):
    """Get provider API key configuration status."""
    config_service = ConfigService(db)
    keys = await config_service.get_provider_keys()
    priority = await config_service.get_provider_priority()
    
    return {
        "fanart": {"configured": keys["fanart"]},
        "mediux": {"configured": keys["mediux"]},
        "tmdb": {"configured": keys["tmdb"]},
        "tvdb": {"configured": keys["tvdb"]},
        "provider_priority": priority,
    }


@router.put("/providers")
async def update_provider_settings(
    request: ProviderSettingsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update provider API keys and priority."""
    config_service = ConfigService(db)
    
    if request.fanart_api_key is not None:
        await config_service.set_provider_key("fanart", request.fanart_api_key)
        
    if request.mediux_api_key is not None:
        await config_service.set_provider_key("mediux", request.mediux_api_key)
        
    if request.tmdb_api_key is not None:
        await config_service.set_provider_key("tmdb", request.tmdb_api_key)
        
    if request.tvdb_api_key is not None:
        await config_service.set_provider_key("tvdb", request.tvdb_api_key)
        
    if request.provider_priority:
        # Convert enum list to string list
        priority = [p.value for p in request.provider_priority]
        await config_service.set_provider_priority(priority)
        
    return {"success": True, "message": "Settings saved"}


@router.post("/providers/test/{provider}", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider: Provider,
    db: AsyncSession = Depends(get_db),
):
    """Test a provider's API connection."""
    service = ArtworkService(db)
    success = await service.test_provider(provider)
    
    return ProviderTestResponse(
        provider=provider,
        success=success,
        message="Connection successful" if success else "Connection failed (check API key)",
    )


@router.get("/plex")
async def get_plex_settings(db: AsyncSession = Depends(get_db)):
    """Get Plex connection settings (without token)."""
    config_service = ConfigService(db)
    url, _, server_name = await config_service.get_plex_config()
    configured = await config_service.is_plex_configured()
    
    return {
        "configured": configured,
        "server_url": url,
        "server_name": server_name,
    }


@router.get("/general")
async def get_general_settings(db: AsyncSession = Depends(get_db)):
    """Get general application settings."""
    # TODO: Implement generic settings storage if needed beyond ConfigService keys
    return {
        "scan_checkpoint_interval": 100,
        "scan_batch_size": 20,
        "artwork_lock_after_apply": True,
        "edition_backup_before_update": True,
    }


@router.put("/general")
async def update_general_settings(
    settings: dict,
    db: AsyncSession = Depends(get_db),
):
    """Update general application settings."""
    # TODO: Save generic settings
    return {"success": True, "message": "Settings saved"}


@router.get("/export")
async def export_settings(db: AsyncSession = Depends(get_db)):
    """Export all settings as JSON."""
    # TODO: Export (excluding sensitive data)
    return {
        "version": "1.0.0",
        "exported_at": None,
        "settings": {},
    }


@router.post("/import")
async def import_settings(
    settings: dict,
    db: AsyncSession = Depends(get_db),
):
    """Import settings from JSON."""
    # TODO: Import settings
    return {"success": True, "message": "Settings imported"}


@router.post("/reset")
async def reset_settings(db: AsyncSession = Depends(get_db)):
    """Reset all settings to defaults."""
    # TODO: Reset to defaults
    return {"success": True, "message": "Settings reset to defaults"}
