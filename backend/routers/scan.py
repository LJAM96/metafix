"""Scan management router."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_maker, get_db
from models.database import Scan
from models.schemas import (
    ScanConfig,
    ScanStartRequest,
    ScanStatus,
    ScanStatusResponse,
    ScanType,
)
from services.scan_manager import ScanAlreadyRunningError, scan_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start")
async def start_scan(
    request: ScanStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start a new scan."""
    config = request.config.model_dump()
    
    try:
        scan_id = await scan_manager.start_scan(db, config)
        
        # Start scan in background
        background_tasks.add_task(
            scan_manager.run_scan,
            async_session_maker,
            scan_id,
            config,
        )
        
        return {
            "scan_id": scan_id,
            "status": "running",
            "message": "Scan started",
        }
        
    except ScanAlreadyRunningError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Failed to start scan")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start scan: {e}",
        )


@router.get("/status")
async def get_scan_status(db: AsyncSession = Depends(get_db)):
    """Get current scan status."""
    progress = scan_manager.get_progress()
    
    if progress["scan_id"]:
        # Get additional info from database
        result = await db.execute(
            select(Scan).where(Scan.id == progress["scan_id"])
        )
        scan = result.scalar_one_or_none()
        
        if scan:
            return ScanStatusResponse(
                id=scan.id,
                scan_type=ScanType(scan.scan_type),
                status=ScanStatus(scan.status),
                total_items=scan.total_items,
                processed_items=scan.processed_items,
                issues_found=scan.issues_found,
                editions_updated=scan.editions_updated,
                current_library=scan.current_library,
                current_item=scan.current_item,
                started_at=scan.started_at,
                paused_at=scan.paused_at,
                completed_at=scan.completed_at,
                progress_percent=(
                    (scan.processed_items / scan.total_items * 100)
                    if scan.total_items > 0 else 0
                ),
            )
    
    # No active scan - return last completed scan or empty
    result = await db.execute(
        select(Scan)
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    scan = result.scalar_one_or_none()
    
    if scan:
        return ScanStatusResponse(
            id=scan.id,
            scan_type=ScanType(scan.scan_type),
            status=ScanStatus(scan.status),
            total_items=scan.total_items,
            processed_items=scan.processed_items,
            issues_found=scan.issues_found,
            editions_updated=scan.editions_updated,
            current_library=scan.current_library,
            current_item=scan.current_item,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            progress_percent=100 if scan.status == "completed" else 0,
        )
    
    # No scans at all
    return ScanStatusResponse(
        id=0,
        scan_type=ScanType.ARTWORK,
        status=ScanStatus.PENDING,
        total_items=0,
        processed_items=0,
        issues_found=0,
        editions_updated=0,
    )


@router.post("/pause")
async def pause_scan(db: AsyncSession = Depends(get_db)):
    """Pause the current scan."""
    success = await scan_manager.pause_scan(db)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="No scan is currently running",
        )
    
    return {"success": True, "message": "Scan paused"}


@router.post("/resume")
async def resume_scan(db: AsyncSession = Depends(get_db)):
    """Resume a paused scan."""
    success = await scan_manager.resume_scan(db)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="No scan is currently paused",
        )
    
    return {"success": True, "message": "Scan resumed"}


@router.post("/cancel")
async def cancel_scan(db: AsyncSession = Depends(get_db)):
    """Cancel the current scan."""
    success = await scan_manager.cancel_scan(db)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="No scan is currently running",
        )
    
    return {"success": True, "message": "Scan cancelled"}


@router.get("/subscribe")
async def subscribe_to_scan():
    """SSE endpoint for scan progress updates."""
    
    async def event_stream():
        queue = await scan_manager.subscribe()
        
        try:
            while True:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    
                    # Stop streaming if scan completed/cancelled/failed
                    if event.get("type") in ("scan_completed", "scan_cancelled", "scan_failed"):
                        break
                        
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                    
        except asyncio.CancelledError:
            pass
        finally:
            scan_manager.unsubscribe(queue)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def get_scan_history(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get scan history."""
    offset = (page - 1) * page_size
    
    # Get total count
    count_result = await db.execute(select(Scan))
    total = len(count_result.scalars().all())
    
    # Get paginated results
    result = await db.execute(
        select(Scan)
        .order_by(Scan.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    scans = result.scalars().all()
    
    return {
        "scans": [
            {
                "id": scan.id,
                "scan_type": scan.scan_type,
                "status": scan.status,
                "total_items": scan.total_items,
                "processed_items": scan.processed_items,
                "issues_found": scan.issues_found,
                "editions_updated": scan.editions_updated,
                "triggered_by": scan.triggered_by,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            }
            for scan in scans
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/interrupted")
async def check_interrupted_scan(db: AsyncSession = Depends(get_db)):
    """Check for interrupted scans from previous server run."""
    interrupted = await scan_manager.check_interrupted_scan(db)
    
    return {
        "has_interrupted": interrupted is not None,
        "scan": interrupted,
    }


@router.post("/interrupted/discard")
async def discard_interrupted_scan(db: AsyncSession = Depends(get_db)):
    """Discard an interrupted scan."""
    interrupted = await scan_manager.check_interrupted_scan(db)
    
    if not interrupted:
        raise HTTPException(
            status_code=404,
            detail="No interrupted scan found",
        )
    
    # Mark as cancelled
    from sqlalchemy import update
    from models.database import Scan
    from datetime import datetime
    
    await db.execute(
        update(Scan)
        .where(Scan.id == interrupted["id"])
        .values(status="cancelled", completed_at=datetime.utcnow())
    )
    await db.commit()
    
    return {"success": True, "message": "Interrupted scan discarded"}
