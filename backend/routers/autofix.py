"""Auto-fix router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, async_session_maker
from services.autofix_service import autofix_service

router = APIRouter()


@router.post("/start")
async def start_autofix(
    scan_id: Optional[int] = None,
    skip_unmatched: bool = True,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Start auto-fix process for pending issues."""
    try:
        await autofix_service.start(
            db_factory=async_session_maker,
            scan_id=scan_id,
            skip_unmatched=skip_unmatched,
            min_score=min_score
        )
        return {"success": True, "message": "Auto-fix started"}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


@router.get("/status")
async def get_autofix_status(db: AsyncSession = Depends(get_db)):
    """Get current auto-fix status."""
    progress = autofix_service.progress
    return {
        "running": autofix_service.is_running,
        **progress
    }


@router.post("/cancel")
async def cancel_autofix(db: AsyncSession = Depends(get_db)):
    """Cancel running auto-fix process."""
    await autofix_service.cancel()
    return {"success": True, "message": "Auto-fix cancelled"}


@router.get("/subscribe")
async def subscribe_to_autofix():
    """SSE endpoint for auto-fix progress updates."""
    queue = await autofix_service.subscribe()

    async def event_stream():
        try:
            while True:
                data = await queue.get()
                import json
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            autofix_service.unsubscribe(queue)

    import asyncio
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/preview")
async def preview_autofix(
    scan_id: Optional[int] = None,
    skip_unmatched: bool = True,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Preview what auto-fix would do without applying."""
    # TODO: Calculate preview (Low priority, skipping for now)
    return {
        "total_issues": 0,
        "would_apply": 0,
        "would_skip_unmatched": 0,
        "would_skip_low_score": 0,
        "issues": [],
    }
