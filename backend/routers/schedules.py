"""Schedule management router."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models.database import Schedule
from models.schemas import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
)
from services.scheduler_service import scheduler_service

router = APIRouter()


@router.get("", response_model=ScheduleListResponse)
async def get_schedules(db: AsyncSession = Depends(get_db)):
    """Get all schedules."""
    result = await db.execute(select(Schedule))
    schedules = result.scalars().all()
    
    return ScheduleListResponse(schedules=[
        ScheduleResponse(
            id=s.id,
            name=s.name,
            enabled=s.enabled,
            cron_expression=s.cron_expression,
            scan_type=s.scan_type,
            auto_commit=s.auto_commit,
            last_run_at=s.last_run_at,
            next_run_at=s.next_run_at,
            created_at=s.created_at,
        ) for s in schedules
    ])


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new schedule."""
    # Convert Pydantic config to dict
    config_dict = request.config.dict()
    
    schedule = Schedule(
        name=request.name,
        enabled=True,
        cron_expression=request.cron_expression,
        scan_type=request.scan_type,
        config=json.dumps(config_dict),
        auto_commit=request.auto_commit,
        auto_commit_options=json.dumps({
            "skip_unmatched": request.auto_commit_skip_unmatched,
            "min_score": request.auto_commit_min_score,
        }),
        created_at=datetime.utcnow(),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    # Add to scheduler
    scheduler_service._add_job(schedule)
    
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        scan_type=schedule.scan_type,
        auto_commit=schedule.auto_commit,
        created_at=schedule.created_at,
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific schedule."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        scan_type=schedule.scan_type,
        auto_commit=schedule.auto_commit,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    request: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a schedule."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    schedule.name = request.name
    schedule.cron_expression = request.cron_expression
    schedule.scan_type = request.scan_type
    schedule.config = json.dumps(request.config.dict())
    schedule.auto_commit = request.auto_commit
    schedule.auto_commit_options = json.dumps({
        "skip_unmatched": request.auto_commit_skip_unmatched,
        "min_score": request.auto_commit_min_score,
    })
    
    await db.commit()
    await db.refresh(schedule)
    
    # Update scheduler
    await scheduler_service.update_job(schedule.id)
    
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        scan_type=schedule.scan_type,
        auto_commit=schedule.auto_commit,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    await db.delete(schedule)
    await db.commit()
    
    # Remove from scheduler
    await scheduler_service.delete_job(schedule_id)
    
    return {"success": True, "message": "Schedule deleted"}


@router.post("/{schedule_id}/enable")
async def enable_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Enable a schedule."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    schedule.enabled = True
    await db.commit()
    
    await scheduler_service.update_job(schedule_id)
    
    return {"success": True, "message": "Schedule enabled"}


@router.post("/{schedule_id}/disable")
async def disable_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Disable a schedule."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    schedule.enabled = False
    await db.commit()
    
    await scheduler_service.update_job(schedule_id)
    
    return {"success": True, "message": "Schedule disabled"}


@router.post("/{schedule_id}/run")
async def run_schedule_now(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Run a schedule immediately."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    # Trigger execution (async)
    import asyncio
    asyncio.create_task(scheduler_service._execute_scan(schedule_id))
    
    return {"success": True, "message": "Scan started"}


@router.get("/presets")
async def get_cron_presets():
    """Get common cron expression presets."""
    return {
        "presets": [
            {"name": "Daily at 3 AM", "cron": "0 3 * * *"},
            {"name": "Daily at midnight", "cron": "0 0 * * *"},
            {"name": "Weekly on Sunday at 2 AM", "cron": "0 2 * * 0"},
            {"name": "Weekly on Saturday at 3 AM", "cron": "0 3 * * 6"},
            {"name": "Monthly on 1st at 3 AM", "cron": "0 3 1 * *"},
            {"name": "Every 6 hours", "cron": "0 */6 * * *"},
            {"name": "Every 12 hours", "cron": "0 */12 * * *"},
        ]
    }
