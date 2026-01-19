"""Plex connection and library management router."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.schemas import (
    PlexConnectRequest,
    PlexConnectResponse,
    PlexLibrariesResponse,
    PlexLibrary,
)
from services.config_service import ConfigService
from services.plex_service import PlexService, PlexConnectionError, PlexAuthenticationError

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_plex_service(db: AsyncSession = Depends(get_db)) -> Optional[PlexService]:
    """Get configured PlexService or None if not configured."""
    config = ConfigService(db)
    url, token, _ = await config.get_plex_config()
    
    if not url or not token:
        return None
    
    return PlexService(url, token)


@router.post("/auth/pin")
async def create_plex_pin(
    client_id: str = Body(..., embed=True),
):
    """Create a Plex PIN for OAuth."""
    logger.info(f"Creating Plex PIN for client_id: {client_id}")
    try:
        pin_id, code = await PlexService.create_pin(client_id)
        
        # Construct auth URL
        auth_url = (
            f"https://app.plex.tv/auth#?clientID={client_id}"
            f"&code={code}"
            "&context%5Bdevice%5D%5Bproduct%5D=MetaFix"
            "&context%5Bdevice%5D%5Bplatform%5D=Web"
            "&context%5Bdevice%5D%5Bdevice%5D=MetaFix"
        )
        
        logger.info(f"PIN created successfully: id={pin_id}, code={code}")
        return {
            "id": pin_id,
            "code": code,
            "auth_url": auth_url,
        }
    except Exception as e:
        logger.exception("Failed to create Plex PIN")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/pin/{pin_id}")
async def check_plex_pin(
    pin_id: int,
    code: str,
    client_id: str,
):
    """Check if Plex PIN is authorized."""
    try:
        token = await PlexService.check_pin(pin_id, code, client_id)
        
        return {
            "authorized": bool(token),
            "auth_token": token,
        }
    except Exception as e:
        logger.exception("Failed to check Plex PIN")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources")
async def get_plex_resources(
    token: str = Body(..., embed=True),
):
    """Get list of servers associated with Plex account."""
    try:
        servers = await PlexService.get_resources(token)
        return {"servers": servers}
    except Exception as e:
        logger.exception("Failed to fetch Plex resources")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect", response_model=PlexConnectResponse)
async def connect_to_plex(
    request: PlexConnectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Test connection to Plex server and save credentials."""
    # Normalize URL
    url = request.url.rstrip("/")
    
    # Test connection
    plex = PlexService(url, request.token)
    
    try:
        success, message, server_name = await plex.test_connection()
        
        if not success:
            return PlexConnectResponse(
                success=False,
                message=message,
                server_name=None,
            )
        
        # Save configuration
        config = ConfigService(db)
        await config.set_plex_config(url, request.token, server_name or "Plex Server")
        await db.commit()
        
        logger.info(f"Successfully connected to Plex server: {server_name}")
        
        return PlexConnectResponse(
            success=True,
            message="Connection successful",
            server_name=server_name,
        )
        
    except Exception as e:
        logger.exception("Error connecting to Plex")
        return PlexConnectResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            server_name=None,
        )
    finally:
        await plex.close()


@router.get("/status")
async def get_plex_status(db: AsyncSession = Depends(get_db)):
    """Get current Plex connection status."""
    config = ConfigService(db)
    url, token, server_name = await config.get_plex_config()
    
    if not url or not token:
        return {
            "connected": False,
            "server_name": None,
            "server_url": None,
        }
    
    # Test if still connected
    plex = PlexService(url, token)
    try:
        success, _, current_name = await plex.test_connection()
        
        return {
            "connected": success,
            "server_name": current_name or server_name,
            "server_url": url,
        }
    except Exception:
        return {
            "connected": False,
            "server_name": server_name,
            "server_url": url,
            "error": "Connection test failed",
        }
    finally:
        await plex.close()


@router.get("/libraries", response_model=PlexLibrariesResponse)
async def get_libraries(
    plex: Optional[PlexService] = Depends(get_plex_service),
):
    """Get list of Plex libraries."""
    if not plex:
        raise HTTPException(
            status_code=400,
            detail="Plex is not configured. Please connect to Plex first.",
        )
    
    try:
        libraries = await plex.get_libraries()
        
        return PlexLibrariesResponse(
            libraries=[
                PlexLibrary(
                    id=lib.id,
                    name=lib.name,
                    type=lib.type,
                    item_count=lib.item_count,
                )
                for lib in libraries
            ]
        )
    except PlexAuthenticationError:
        raise HTTPException(status_code=401, detail="Plex authentication failed")
    except PlexConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await plex.close()


@router.get("/libraries/{library_id}/items")
async def get_library_items(
    library_id: str,
    page: int = 1,
    page_size: int = 50,
    plex: Optional[PlexService] = Depends(get_plex_service),
):
    """Get items from a specific library with pagination."""
    if not plex:
        raise HTTPException(
            status_code=400,
            detail="Plex is not configured",
        )
    
    try:
        start = (page - 1) * page_size
        items, total = await plex.get_library_items(library_id, start, page_size)
        
        return {
            "items": [
                {
                    "rating_key": item.rating_key,
                    "title": item.title,
                    "year": item.year,
                    "type": item.type,
                    "has_poster": item.has_poster,
                    "has_background": item.has_background,
                    "is_matched": item.is_matched,
                    "thumb": item.thumb,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    except PlexAuthenticationError:
        raise HTTPException(status_code=401, detail="Plex authentication failed")
    except PlexConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await plex.close()


@router.get("/item/{rating_key}")
async def get_item_detail(
    rating_key: str,
    plex: Optional[PlexService] = Depends(get_plex_service),
):
    """Get detailed metadata for a specific Plex item."""
    if not plex:
        raise HTTPException(status_code=400, detail="Plex is not configured")
    
    try:
        item = await plex.get_item_metadata(rating_key)
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {
            "rating_key": item.rating_key,
            "title": item.title,
            "year": item.year,
            "type": item.type,
            "guid": item.guid,
            "has_poster": item.has_poster,
            "has_background": item.has_background,
            "is_matched": item.is_matched,
            "thumb": item.thumb,
            "art": item.art,
            "edition_title": item.edition_title,
            "external_ids": {
                "tmdb": item.get_external_id("tmdb"),
                "imdb": item.get_external_id("imdb"),
                "tvdb": item.get_external_id("tvdb"),
            },
        }
    except PlexAuthenticationError:
        raise HTTPException(status_code=401, detail="Plex authentication failed")
    except PlexConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await plex.close()


@router.delete("/disconnect")
async def disconnect_plex(db: AsyncSession = Depends(get_db)):
    """Disconnect from Plex and remove stored credentials."""
    config = ConfigService(db)
    
    await config.delete("plex_url")
    await config.delete("plex_token")
    await config.delete("plex_server_name")
    await db.commit()
    
    logger.info("Disconnected from Plex server")
    
    return {"success": True, "message": "Disconnected from Plex"}
