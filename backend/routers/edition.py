"""Edition manager router."""

import logging
from typing import Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.schemas import EditionSettingsRequest, EditionSettingsResponse
from services.edition_manager import EditionManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Default modules in order
DEFAULT_MODULES = [
    "Resolution",
    "DynamicRange",
    "VideoCodec",
    "AudioCodec",
    "AudioChannels",
    "Bitrate",
    "Size",
    "Cut",
    "Release",
    "Source",
    "ContentRating",
    "Duration",
    "Rating",
    "Director",
    "Genre",
    "Country",
    "Studio",
    "Language",
    "SpecialFeatures",
    "Writer",
    "FrameRate",
    "ShortFilm",
]

DEFAULT_ENABLED = [
    "Resolution",
    "DynamicRange",
    "VideoCodec",
    "AudioCodec",
    "AudioChannels",
    "Cut",
    "Release",
]

@router.get("/modules")
async def get_available_modules():
    """Get list of available edition modules."""
    modules = [
        {"name": "Resolution", "description": "Video resolution (4K, 1080p)", "example": "4K"},
        {"name": "DynamicRange", "description": "HDR format (Dolby Vision, HDR10+)", "example": "Dolby Vision"},
        {"name": "VideoCodec", "description": "Video codec (H.265, AV1)", "example": "H.265"},
        {"name": "AudioCodec", "description": "Audio codec (Dolby TrueHD, DTS-HD MA)", "example": "Dolby TrueHD Atmos"},
        {"name": "AudioChannels", "description": "Audio channels (7.1, 5.1)", "example": "7.1"},
        {"name": "Bitrate", "description": "Video bitrate", "example": "24.5 Mbps"},
        {"name": "FrameRate", "description": "Video frame rate", "example": "24fps"},
        {"name": "Cut", "description": "Movie cut (Director's Cut)", "example": "Director's Cut"},
        {"name": "Release", "description": "Release type (Criterion, IMAX)", "example": "Criterion"},
        {"name": "Source", "description": "Media source (REMUX, WEB-DL)", "example": "REMUX"},
        {"name": "ShortFilm", "description": "Detect short films", "example": "Short Film"},
        {"name": "SpecialFeatures", "description": "Detect special features", "example": "Extras"},
        {"name": "ContentRating", "description": "Age rating", "example": "PG-13"},
        {"name": "Duration", "description": "Runtime", "example": "2h 14m"},
        {"name": "Rating", "description": "Audience rating", "example": "8.4"},
        {"name": "Director", "description": "Director name", "example": "Christopher Nolan"},
        {"name": "Writer", "description": "Writer name", "example": "Quentin Tarantino"},
        {"name": "Genre", "description": "Primary genre", "example": "Sci-Fi"},
        {"name": "Country", "description": "Production country", "example": "United States"},
        {"name": "Studio", "description": "Production studio", "example": "Warner Bros."},
        {"name": "Language", "description": "Audio language", "example": "English"},
        {"name": "Size", "description": "File size", "example": "58.2 GB"},
    ]
    return {"modules": modules}

@router.get("/config", response_model=EditionSettingsResponse)
async def get_edition_config(db: AsyncSession = Depends(get_db)):
    """Get edition configuration."""
    manager = EditionManager(db)
    config = await manager.get_config()
    
    settings = config.get("settings", {})
    
    return EditionSettingsResponse(
        enabled_modules=config.get("enabled_modules", DEFAULT_ENABLED),
        module_order=config.get("module_order", DEFAULT_MODULES),
        separator=settings.get("separator", " . "),
        excluded_languages=settings.get("excluded_languages", ["English"]),
        skip_multiple_audio_tracks=settings.get("skip_multiple_audio_tracks", True),
        rating_source=settings.get("rating_source", "imdb"),
        tmdb_api_key=settings.get("tmdb_api_key")
    )

@router.put("/config")
async def update_edition_config(
    request: EditionSettingsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update edition configuration."""
    manager = EditionManager(db)
    
    new_config = {
        "enabled_modules": request.enabled_modules,
        "module_order": request.module_order,
        "settings": {
            "separator": request.separator,
            "excluded_languages": request.excluded_languages,
            "skip_multiple_audio_tracks": request.skip_multiple_audio_tracks,
            "rating_source": request.rating_source,
            "tmdb_api_key": request.tmdb_api_key,
        }
    }
    
    await manager.update_config(new_config)
    return {
        "enabled_modules": request.enabled_modules,
        "module_order": request.module_order,
        "separator": request.separator,
        "excluded_languages": request.excluded_languages,
        "skip_multiple_audio_tracks": request.skip_multiple_audio_tracks,
        "rating_source": request.rating_source,
    }

@router.post("/preview")
async def preview_edition(
    plex_rating_key: str,
    db: AsyncSession = Depends(get_db),
):
    """Preview edition string for a specific item."""
    manager = EditionManager(db)
    try:
        edition = await manager.generate_edition(plex_rating_key)
        return {
            "plex_rating_key": plex_rating_key,
            "current_edition": None, # Could fetch this if needed
            "new_edition": edition,
            "modules": {} # Could populate detailed breakdown if needed
        }
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backups")
async def get_edition_backups(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get list of edition backups."""
    # TODO: Implement listing from EditionBackup table
    return {
        "backups": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }

@router.post("/backups/{backup_id}/restore")
async def restore_edition_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Restore edition from backup."""
    # This might require lookup by backup ID first to get rating_key
    # For now, placeholder or needs implementation in EditionManager
    return {"success": False, "message": "Not implemented"}
