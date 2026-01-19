"""Issues management router."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.database import Issue, Suggestion, Scan
from models.schemas import (
    IssueAcceptRequest,
    IssueListResponse,
    IssueResponse,
    IssueStatus,
    IssueType,
    SuggestionResponse,
)
# We might need PlexService to apply artwork
from services.config_service import ConfigService
from services.plex_service import PlexService

router = APIRouter()


@router.get("", response_model=IssueListResponse)
async def get_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[IssueStatus] = None,
    issue_type: Optional[IssueType] = None,
    library: Optional[str] = None,
    search: Optional[str] = None,
    scan_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of issues with optional filters."""
    query = select(Issue).options(selectinload(Issue.suggestions))
    
    if status:
        query = query.where(Issue.status == status)
    if issue_type:
        query = query.where(Issue.issue_type == issue_type)
    if library:
        query = query.where(Issue.library_name == library)
    if scan_id:
        query = query.where(Issue.scan_id == scan_id)
    if search:
        query = query.where(Issue.title.ilike(f"%{search}%"))
        
    # Order by creation desc
    query = query.order_by(desc(Issue.created_at))
    
    # Count total
    # This is inefficient for large tables, but SQLite is okay for reasonable size
    # A separate count query is better.
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()
    
    # Pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    issues = result.scalars().all()
    
    return IssueListResponse(
        total=total,
        page=page,
        page_size=page_size,
        issues=issues,
    )


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific issue with its suggestions."""
    query = select(Issue).where(Issue.id == issue_id).options(selectinload(Issue.suggestions))
    result = await db.execute(query)
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    return issue


@router.post("/{issue_id}/accept")
async def accept_suggestion(
    issue_id: int,
    request: IssueAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept a suggestion and apply artwork to Plex."""
    # Fetch issue
    query = select(Issue).where(Issue.id == issue_id).options(selectinload(Issue.suggestions))
    result = await db.execute(query)
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    # Fetch suggestion
    suggestion = next((s for s in issue.suggestions if s.id == request.suggestion_id), None)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
        
    # Initialize Plex Service
    config_service = ConfigService(db)
    plex_url, plex_token, _ = await config_service.get_plex_config()
    if not plex_url or not plex_token:
        raise HTTPException(status_code=500, detail="Plex not configured")
        
    plex = PlexService(plex_url, plex_token)
    
    try:
        success = False
        # Determine action based on artwork type
        if suggestion.artwork_type == "poster":
            success = await plex.upload_poster(issue.plex_rating_key, suggestion.image_url)
            if success:
                # Lock poster
                await plex.lock_poster(issue.plex_rating_key)
        
        elif suggestion.artwork_type == "background":
            success = await plex.upload_background(issue.plex_rating_key, suggestion.image_url)
            if success:
                await plex.lock_background(issue.plex_rating_key)
                
        # TODO: Handle logo (Plex doesn't have native logo support in standard API same way, usually mostly extras or just art?)
        # Actually Plex metadata agent handles it, but setting it via API might require different endpoint or it's not standard.
        # Often logos are handled by themes or specific clients.
        # We'll skip logo application for now or treat as background if desired? No.
        # Checking scan_manager, logos are detected but applying might be tricky.
        # Assuming for now we only apply posters/backgrounds.
        
        if success:
            issue.status = "applied"
            suggestion.is_selected = True
            await db.commit()
            return {"success": True, "message": "Artwork applied"}
        else:
            raise HTTPException(status_code=500, detail="Failed to apply artwork to Plex")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await plex.close()


@router.post("/{issue_id}/skip")
async def skip_issue(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Skip/reject an issue."""
    query = select(Issue).where(Issue.id == issue_id)
    result = await db.execute(query)
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    issue.status = "rejected" # or skipped
    await db.commit()
    
    return {"success": True, "message": "Issue skipped"}


@router.post("/{issue_id}/refresh")
async def refresh_suggestions(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Refresh artwork suggestions for an issue."""
    # This requires running ArtworkService for a single item
    # We can instantiate ArtworkService and call get_artwork
    from services.artwork_service import ArtworkService
    from models.schemas import ArtworkType, MediaType
    import json
    
    query = select(Issue).where(Issue.id == issue_id)
    result = await db.execute(query)
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    service = ArtworkService(db)
    
    # Parse external IDs
    external_ids = json.loads(issue.external_ids) if issue.external_ids else {}
    if not external_ids and issue.plex_guid:
        # Try to parse from guid if needed, but usually scanner did this
        pass
        
    if not external_ids:
        return {"success": False, "message": "No external IDs to search with"}
    
    # Determine type
    media_type = MediaType.MOVIE if issue.media_type == "movie" else MediaType.SHOW
    # If episode/season, we might need parent IDs?
    
    # Determine artwork type needed
    # issue_type: no_poster, no_background, no_logo, placeholder_poster...
    target_type = None
    if "poster" in issue.issue_type:
        target_type = ArtworkType.POSTER
    elif "background" in issue.issue_type:
        target_type = ArtworkType.BACKGROUND
    elif "logo" in issue.issue_type:
        target_type = ArtworkType.LOGO
        
    if not target_type:
        return {"success": False, "message": "Unknown artwork type needed"}
        
    results = await service.get_artwork(media_type, external_ids, [target_type])
    
    # Update suggestions in DB
    # First delete old pending suggestions? Or keep them?
    # Let's replace.
    
    # Clear existing suggestions
    # Note: If we had "accepted" ones we might want to keep? But issue is likely pending if we refresh.
    await db.execute(
        select(Suggestion).where(Suggestion.issue_id == issue_id)
    )
    # Actually we need to delete.
    # issue.suggestions = [] logic works with ORM?
    # Or db.delete
    
    # For simplicity, just append new ones? Or avoid duplicates?
    # I'll just clear and re-add for now to be fresh.
    
    # Need to be careful with async ORM delete of collection
    # Safe way:
    # delete from suggestions where issue_id = id
    from sqlalchemy import delete
    await db.execute(delete(Suggestion).where(Suggestion.issue_id == issue_id))
    
    count = 0
    for res in results:
        sugg = Suggestion(
            issue_id=issue_id,
            source=res.source.value,
            artwork_type=res.artwork_type.value,
            image_url=res.image_url,
            thumbnail_url=res.thumbnail_url,
            language=res.language,
            score=res.score,
            set_name=res.set_name,
            creator_name=res.creator_name,
        )
        db.add(sugg)
        count += 1
        
    await db.commit()
    
    return {"success": True, "count": count}


@router.get("/stats")
async def get_issue_stats(db: AsyncSession = Depends(get_db)):
    """Get issue statistics."""
    
    # Total
    total = await db.scalar(select(func.count(Issue.id)))
    
    # By status
    pending = await db.scalar(select(func.count(Issue.id)).where(Issue.status == "pending"))
    applied = await db.scalar(select(func.count(Issue.id)).where(Issue.status == "applied"))
    skipped = await db.scalar(select(func.count(Issue.id)).where(Issue.status == "rejected"))
    
    # By type
    # Group by issue_type
    type_result = await db.execute(select(Issue.issue_type, func.count(Issue.id)).group_by(Issue.issue_type))
    by_type = {row[0]: row[1] for row in type_result}
    
    # By library
    lib_result = await db.execute(select(Issue.library_name, func.count(Issue.id)).group_by(Issue.library_name))
    by_library = {row[0]: row[1] for row in lib_result}
    
    return {
        "total": total,
        "pending": pending,
        "applied": applied,
        "skipped": skipped,
        "by_type": by_type,
        "by_library": by_library,
    }
