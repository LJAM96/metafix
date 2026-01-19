import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_maker
from models.database import Schedule, Scan
from services.scan_manager import scan_manager
from services.autofix_service import autofix_service

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service to manage scheduled scans."""
    
    _instance: Optional["SchedulerService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.scheduler = AsyncIOScheduler()
        self._started = False
        
    async def start(self):
        """Start the scheduler and load jobs."""
        if self._started:
            return
            
        self.scheduler.start()
        self._started = True
        logger.info("Scheduler started")
        
        # Load jobs from DB
        async with async_session_maker() as db:
            result = await db.execute(select(Schedule).where(Schedule.enabled == True))
            schedules = result.scalars().all()
            
            for schedule in schedules:
                self._add_job(schedule)
                
    def _add_job(self, schedule: Schedule):
        """Register a job with APScheduler."""
        try:
            trigger = CronTrigger.from_crontab(schedule.cron_expression)
            
            self.scheduler.add_job(
                self._execute_scan,
                trigger,
                id=str(schedule.id),
                name=schedule.name,
                replace_existing=True,
                args=[schedule.id]
            )
            logger.info(f"Added scheduled job: {schedule.name} ({schedule.cron_expression})")
        except Exception as e:
            logger.error(f"Failed to add job {schedule.id}: {e}")

    def _remove_job(self, schedule_id: int):
        """Remove a job from APScheduler."""
        try:
            self.scheduler.remove_job(str(schedule_id))
            logger.info(f"Removed job: {schedule_id}")
        except Exception:
            pass # Job might not exist

    async def update_job(self, schedule_id: int):
        """Update a job definition (called after DB update)."""
        async with async_session_maker() as db:
            schedule = await db.get(Schedule, schedule_id)
            if not schedule:
                self._remove_job(schedule_id)
                return
                
            if schedule.enabled:
                self._add_job(schedule)
            else:
                self._remove_job(schedule_id)

    async def delete_job(self, schedule_id: int):
        """Delete a job."""
        self._remove_job(schedule_id)

    async def _execute_scan(self, schedule_id: int):
        """Execute the scheduled scan."""
        logger.info(f"Executing scheduled scan {schedule_id}")
        
        async with async_session_maker() as db:
            schedule = await db.get(Schedule, schedule_id)
            if not schedule:
                return
                
            # Update last run
            schedule.last_run_at = datetime.utcnow()
            await db.commit()
            
            import json
            config = json.loads(schedule.config)
            config["triggered_by"] = f"schedule_{schedule_id}"
            
            try:
                # Start scan
                # Note: This is async but _execute_scan is awaited by APScheduler
                # We want to wait for scan to finish if we want auto-commit?
                # ScanManager runs in background task usually.
                # But here we want to coordinate.
                
                # However, scan_manager.start_scan returns scan_id and runs in background.
                # We can't easily wait unless we subscribe or poll.
                # Simplest approach: Just start scan. Auto-commit can be a separate mechanism or
                # we pass auto-commit config to scan manager?
                # Or we spawn a monitoring task here.
                
                scan_id = await scan_manager.start_scan(db, config)
                
                if schedule.auto_commit:
                    # Spawn task to wait and commit
                    import asyncio
                    asyncio.create_task(self._monitor_and_commit(scan_id, schedule.auto_commit_options))
                    
            except Exception as e:
                logger.error(f"Scheduled scan failed to start: {e}")

    async def _monitor_and_commit(self, scan_id: int, options_json: Optional[str]):
        """Wait for scan to complete and run auto-fix."""
        logger.info(f"Monitoring scan {scan_id} for auto-commit")
        
        # Poll status
        import asyncio
        while True:
            await asyncio.sleep(5)
            if scan_manager.current_scan_id != scan_id:
                # Scan finished or another started
                # Check DB for status
                async with async_session_maker() as db:
                    from models.database import Scan
                    scan = await db.get(Scan, scan_id)
                    if not scan:
                        return
                    
                    if scan.status == "completed":
                        # Run auto-fix
                        logger.info(f"Scan {scan_id} completed, running auto-commit")
                        
                        import json
                        options = json.loads(options_json) if options_json else {}
                        
                        await autofix_service.start(
                            db_factory=async_session_maker,
                            scan_id=scan_id,
                            skip_unmatched=options.get("skip_unmatched", True),
                            min_score=options.get("min_score", 0)
                        )
                        return
                    elif scan.status in ["failed", "cancelled"]:
                        logger.info(f"Scan {scan_id} {scan.status}, skipping auto-commit")
                        return
            
            # If still running, loop

# Global instance
scheduler_service = SchedulerService()
