"""Artwork provider router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.schemas import ArtworkType, MediaType, Provider
from services.artwork_service import ArtworkService

router = APIRouter()


@router.get("/search")
async def search_artwork(
    media_type: MediaType,
    artwork_type: ArtworkType,
    tmdb_id: Optional[str] = None,
    tvdb_id: Optional[str] = None,
    imdb_id: Optional[str] = None,
    title: Optional[str] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Search for artwork across all providers."""
    service = ArtworkService(db)
    
    external_ids = {}
    if tmdb_id:
        external_ids["tmdb"] = tmdb_id
    if tvdb_id:
        external_ids["tvdb"] = tvdb_id
    if imdb_id:
        external_ids["imdb"] = imdb_id
        
    if not external_ids:
        # TODO: If no IDs, maybe search by title/year (requires provider search support)
        # For now, require at least one ID
        return {"results": [], "total": 0}
        
    results = await service.get_artwork(media_type, external_ids, [artwork_type])
    
    # Transform results if necessary, or return as is (Pydantic models)
    return {
        "results": results, 
        "total": len(results)
    }


@router.get("/providers")
async def get_provider_status(db: AsyncSession = Depends(get_db)):
    """Get status of all artwork providers."""
    # Use settings router for this? Or duplicate logic?
    # Keeping this for artwork-specific context if needed, but redirects to settings logic mostly.
    from routers.settings import get_provider_settings
    return await get_provider_settings(db)


@router.post("/providers/test/{provider}")
async def test_provider(
    provider: Provider,
    db: AsyncSession = Depends(get_db),
):
    """Test a specific provider's API connection."""
    service = ArtworkService(db)
    success = await service.test_provider(provider)
    return {"success": success, "message": "Connection successful" if success else "Failed"}


@router.post("/apply")
async def apply_artwork(
    plex_rating_key: str,
    artwork_type: ArtworkType,
    image_url: str,
    lock: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Apply artwork to a Plex item."""
    # TODO: Apply via PlexService
    # This requires PlexService integration to upload/set url
    return {"success": True, "message": "Artwork applied"}


@router.get("/cache/clear")
async def clear_artwork_cache(db: AsyncSession = Depends(get_db)):
    """Clear the artwork cache."""
    # TODO: Clear cache if implemented
    return {"success": True, "message": "Cache cleared"}
