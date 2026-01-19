"""Scan manager singleton for managing scan lifecycle."""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Set

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Issue, Scan, ScanEvent, Suggestion
from services.artwork_scanner import ArtworkIssue, ArtworkScanner, IssueType
from services.config_service import ConfigService
from services.plex_service import PlexService
from services.edition_manager import EditionManager

logger = logging.getLogger(__name__)


class ScanStatus(str, Enum):
    """Scan status states."""
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ScanAlreadyRunningError(Exception):
    """Raised when attempting to start a scan while one is already running."""
    pass


class ScanNotRunningError(Exception):
    """Raised when attempting to control a scan that isn't running."""
    pass


class ScanManager:
    """
    Singleton manager for scan operations.
    
    Ensures only one scan runs at a time and manages pause/resume/cancel.
    """
    
    _instance: Optional["ScanManager"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._status = ScanStatus.IDLE
        self._current_scan_id: Optional[int] = None
        self._scan_task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._cancel_requested = False
        
        # Connected SSE clients
        self._subscribers: Set[asyncio.Queue] = set()
        
        # Current progress
        self._progress = {
            "processed": 0,
            "total": 0,
            "issues_found": 0,
            "editions_updated": 0,
            "current_library": None,
            "current_item": None,
        }
    
    @property
    def status(self) -> ScanStatus:
        """Get current scan status."""
        return self._status
    
    @property
    def current_scan_id(self) -> Optional[int]:
        """Get current scan ID."""
        return self._current_scan_id
    
    @property
    def is_running(self) -> bool:
        """Check if a scan is currently running or paused."""
        return self._status in (ScanStatus.RUNNING, ScanStatus.PAUSED)
    
    def get_progress(self) -> dict:
        """Get current scan progress."""
        return {
            "scan_id": self._current_scan_id,
            "status": self._status.value,
            **self._progress,
        }
    
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to scan events. Returns a queue that receives events."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        
        # Send current state
        await queue.put({
            "type": "connected",
            **self.get_progress(),
        })
        
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from scan events."""
        self._subscribers.discard(queue)
    
    async def _broadcast(self, event: dict):
        """Broadcast event to all subscribers."""
        for queue in list(self._subscribers):
            try:
                await queue.put(event)
            except Exception:
                self._subscribers.discard(queue)
    
    async def start_scan(
        self,
        db: AsyncSession,
        config: dict,
    ) -> int:
        """
        Start a new scan.
        
        Args:
            db: Database session
            config: Scan configuration
            
        Returns:
            Scan ID
            
        Raises:
            ScanAlreadyRunningError: If a scan is already running
        """
        async with self._lock:
            if self.is_running:
                raise ScanAlreadyRunningError(
                    f"Scan {self._current_scan_id} is already in progress"
                )
            
            # Create scan record
            scan = Scan(
                scan_type=config.get("scan_type", "artwork"),
                status="running",
                config=json.dumps(config),
                total_items=0,
                processed_items=0,
                issues_found=0,
                editions_updated=0,
                triggered_by=config.get("triggered_by", "manual"),
                started_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.flush()
            
            self._current_scan_id = scan.id
            self._status = ScanStatus.RUNNING
            self._cancel_requested = False
            self._pause_event.set()
            self._progress = {
                "processed": 0,
                "total": 0,
                "issues_found": 0,
                "editions_updated": 0,
                "current_library": None,
                "current_item": None,
            }
            
            # Log event
            event = ScanEvent(
                scan_id=scan.id,
                event_type="started",
                message="Scan started",
            )
            db.add(event)
            await db.commit()
            
            logger.info(f"Started scan {scan.id}")
            
            await self._broadcast({
                "type": "scan_started",
                "scan_id": scan.id,
            })
            
            return scan.id
    
    async def run_scan(
        self,
        db_factory: Callable[[], AsyncSession],
        scan_id: int,
        config: dict,
    ):
        """
        Execute the scan (called as background task).
        
        Args:
            db_factory: Factory function to create database sessions
            scan_id: Scan ID
            config: Scan configuration
        """
        try:
            async with db_factory() as db:
                await self._execute_scan(db, scan_id, config)
        except asyncio.CancelledError:
            logger.info(f"Scan {scan_id} was cancelled")
        except Exception as e:
            logger.exception(f"Scan {scan_id} failed with error: {e}")
            async with db_factory() as db:
                await self._mark_scan_failed(db, scan_id, str(e))
        finally:
            self._status = ScanStatus.IDLE
            self._current_scan_id = None
            self._scan_task = None
    
    async def _execute_scan(
        self,
        db: AsyncSession,
        scan_id: int,
        config: dict,
    ):
        """Execute the actual scan logic."""
        # Get Plex configuration
        config_service = ConfigService(db)
        plex_url, plex_token, _ = await config_service.get_plex_config()
        
        if not plex_url or not plex_token:
            raise ValueError("Plex is not configured")
        
        plex = PlexService(plex_url, plex_token)
        scanner = None
        
        try:
            # Initialize scanners
            scanner = ArtworkScanner(
                plex=plex,
                check_posters=config.get("check_posters", True),
                check_backgrounds=config.get("check_backgrounds", True),
                check_logos=config.get("check_logos", True),
                check_unmatched=config.get("check_unmatched", True),
                check_placeholders=config.get("check_placeholders", True),
            )
            
            edition_manager = EditionManager(db)
            
            # Determine scan types
            scan_type = config.get("scan_type", "artwork")
            run_artwork = scan_type in ["artwork", "both"]
            run_edition = scan_type in ["edition", "both"]
            edition_enabled = config.get("edition_enabled", True)
            
            # Get libraries to scan
            library_ids = config.get("libraries", [])
            if not library_ids:
                # Scan all libraries if none specified
                libraries = await plex.get_libraries()
                library_ids = [lib.id for lib in libraries]
            
            # Count total items
            total_items = 0
            library_items: dict[str, list] = {}
            
            for lib_id in library_ids:
                if self._cancel_requested:
                    break
                
                items = await plex.get_all_library_items(lib_id)
                library_items[lib_id] = items
                total_items += len(items)
            
            # Update total
            self._progress["total"] = total_items
            await db.execute(
                update(Scan)
                .where(Scan.id == scan_id)
                .values(total_items=total_items)
            )
            await db.commit()
            
            await self._broadcast({
                "type": "scan_progress",
                "scan_id": scan_id,
                "total": total_items,
                "processed": 0,
            })
            
            # Process items
            processed = 0
            issues_found = 0
            editions_updated = 0
            checkpoint_interval = config.get("checkpoint_interval", 100)
            
            for lib_id, items in library_items.items():
                if self._cancel_requested:
                    break
                
                # Get library name
                lib_name = items[0].library_name if items else "Unknown"
                self._progress["current_library"] = lib_name
                
                for item in items:
                    # Check for cancel
                    if self._cancel_requested:
                        await self._mark_scan_cancelled(db, scan_id)
                        return
                    
                    # Wait if paused
                    await self._pause_event.wait()
                    
                    # Scan item
                    self._progress["current_item"] = item.title
                    
                    try:
                        # Artwork Scan
                        if run_artwork:
                            issues = await scanner.scan_item(item)
                            for issue in issues:
                                await self._save_issue(db, scan_id, issue)
                                issues_found += 1
                        
                        # Edition Scan
                        if run_edition and edition_enabled and item.type == "movie":
                            edition = await edition_manager.generate_edition(item.rating_key)
                            # Only apply if different and valid
                            if edition is not None:
                                current_edition = item.edition_title or ""
                                if edition != current_edition:
                                    await edition_manager.apply_edition(item.rating_key, edition)
                                    editions_updated += 1
                        
                    except Exception as e:
                        logger.warning(f"Error scanning {item.title}: {e}")
                    
                    processed += 1
                    self._progress["processed"] = processed
                    self._progress["issues_found"] = issues_found
                    self._progress["editions_updated"] = editions_updated
                    
                    # Update database periodically
                    if processed % checkpoint_interval == 0:
                        await self._save_checkpoint(db, scan_id, processed, issues_found, editions_updated, lib_id)
                    
                    # Broadcast progress
                    if processed % 5 == 0:  # Broadcast more frequently for feedback
                        await self._broadcast({
                            "type": "scan_progress",
                            "scan_id": scan_id,
                            "processed": processed,
                            "total": total_items,
                            "issues_found": issues_found,
                            "editions_updated": editions_updated,
                            "current_item": item.title,
                            "current_library": lib_name,
                        })
            
            # Mark completed
            await self._mark_scan_completed(db, scan_id, processed, issues_found, editions_updated)
            
        finally:
            await plex.close()
            if scanner:
                await scanner.close()
    
    async def _save_issue(
        self,
        db: AsyncSession,
        scan_id: int,
        issue: ArtworkIssue,
    ):
        """Save an issue to the database."""
        db_issue = Issue(
            scan_id=scan_id,
            plex_rating_key=issue.plex_rating_key,
            plex_guid=issue.plex_guid,
            title=issue.title,
            year=issue.year,
            media_type=issue.media_type,
            issue_type=issue.issue_type.value,
            status="pending",
            library_name=issue.library_name,
            external_ids=json.dumps(issue.external_ids) if issue.external_ids else None,
            details=json.dumps(issue.details) if issue.details else None,
        )
        db.add(db_issue)
        await db.flush()
    
    async def _save_checkpoint(
        self,
        db: AsyncSession,
        scan_id: int,
        processed: int,
        issues_found: int,
        editions_updated: int,
        current_library: str,
    ):
        """Save checkpoint for crash recovery."""
        checkpoint = {
            "processed": processed,
            "current_library": current_library,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await db.execute(
            update(Scan)
            .where(Scan.id == scan_id)
            .values(
                processed_items=processed,
                issues_found=issues_found,
                editions_updated=editions_updated,
                current_library=current_library,
                checkpoint=json.dumps(checkpoint),
            )
        )
        await db.commit()
    
    async def _mark_scan_completed(
        self,
        db: AsyncSession,
        scan_id: int,
        processed: int,
        issues_found: int,
        editions_updated: int,
    ):
        """Mark scan as completed."""
        await db.execute(
            update(Scan)
            .where(Scan.id == scan_id)
            .values(
                status="completed",
                processed_items=processed,
                issues_found=issues_found,
                editions_updated=editions_updated,
                completed_at=datetime.utcnow(),
                checkpoint=None,
            )
        )
        
        event = ScanEvent(
            scan_id=scan_id,
            event_type="completed",
            message=f"Scan completed. Found {issues_found} issues, updated {editions_updated} editions.",
        )
        db.add(event)
        await db.commit()
        
        self._status = ScanStatus.COMPLETED
        
        await self._broadcast({
            "type": "scan_completed",
            "scan_id": scan_id,
            "processed": processed,
            "issues_found": issues_found,
            "editions_updated": editions_updated,
        })
        
        logger.info(f"Scan {scan_id} completed. Found {issues_found} issues, updated {editions_updated} editions.")
    
    async def _mark_scan_cancelled(self, db: AsyncSession, scan_id: int):
        """Mark scan as cancelled."""
        await db.execute(
            update(Scan)
            .where(Scan.id == scan_id)
            .values(
                status="cancelled",
                completed_at=datetime.utcnow(),
            )
        )
        
        event = ScanEvent(
            scan_id=scan_id,
            event_type="cancelled",
            message="Scan was cancelled by user.",
        )
        db.add(event)
        await db.commit()
        
        self._status = ScanStatus.CANCELLED
        
        await self._broadcast({
            "type": "scan_cancelled",
            "scan_id": scan_id,
        })
        
        logger.info(f"Scan {scan_id} cancelled.")
    
    async def _mark_scan_failed(
        self,
        db: AsyncSession,
        scan_id: int,
        error: str,
    ):
        """Mark scan as failed."""
        await db.execute(
            update(Scan)
            .where(Scan.id == scan_id)
            .values(
                status="failed",
                completed_at=datetime.utcnow(),
            )
        )
        
        event = ScanEvent(
            scan_id=scan_id,
            event_type="failed",
            message=f"Scan failed: {error}",
        )
        db.add(event)
        await db.commit()
        
        self._status = ScanStatus.FAILED
        
        await self._broadcast({
            "type": "scan_failed",
            "scan_id": scan_id,
            "error": error,
        })
        
        logger.error(f"Scan {scan_id} failed: {error}")
    
    async def pause_scan(self, db: AsyncSession) -> bool:
        """Pause the current scan."""
        if self._status != ScanStatus.RUNNING:
            return False
        
        self._pause_event.clear()
        self._status = ScanStatus.PAUSED
        
        if self._current_scan_id:
            await db.execute(
                update(Scan)
                .where(Scan.id == self._current_scan_id)
                .values(
                    status="paused",
                    paused_at=datetime.utcnow(),
                )
            )
            
            event = ScanEvent(
                scan_id=self._current_scan_id,
                event_type="paused",
                message="Scan paused by user.",
            )
            db.add(event)
            await db.commit()
        
        await self._broadcast({"type": "scan_paused", "scan_id": self._current_scan_id})
        logger.info(f"Scan {self._current_scan_id} paused.")
        
        return True
    
    async def resume_scan(self, db: AsyncSession) -> bool:
        """Resume a paused scan."""
        if self._status != ScanStatus.PAUSED:
            return False
        
        self._pause_event.set()
        self._status = ScanStatus.RUNNING
        
        if self._current_scan_id:
            await db.execute(
                update(Scan)
                .where(Scan.id == self._current_scan_id)
                .values(
                    status="running",
                    paused_at=None,
                )
            )
            
            event = ScanEvent(
                scan_id=self._current_scan_id,
                event_type="resumed",
                message="Scan resumed by user.",
            )
            db.add(event)
            await db.commit()
        
        await self._broadcast({"type": "scan_resumed", "scan_id": self._current_scan_id})
        logger.info(f"Scan {self._current_scan_id} resumed.")
        
        return True
    
    async def cancel_scan(self, db: AsyncSession) -> bool:
        """Cancel the current scan."""
        if not self.is_running:
            return False
        
        self._cancel_requested = True
        self._pause_event.set()  # Unblock if paused
        
        if self._scan_task:
            self._scan_task.cancel()
        
        logger.info(f"Cancel requested for scan {self._current_scan_id}")
        return True
    
    async def check_interrupted_scan(self, db: AsyncSession) -> Optional[dict]:
        """
        Check for interrupted scans on startup.
        
        Returns scan info if an interrupted scan is found.
        """
        result = await db.execute(
            select(Scan)
            .where(Scan.status.in_(["running", "paused"]))
            .order_by(Scan.created_at.desc())
            .limit(1)
        )
        scan = result.scalar_one_or_none()
        
        if scan:
            return {
                "id": scan.id,
                "scan_type": scan.scan_type,
                "status": scan.status,
                "processed_items": scan.processed_items,
                "total_items": scan.total_items,
                "issues_found": scan.issues_found,
                "editions_updated": scan.editions_updated,
                "checkpoint": json.loads(scan.checkpoint) if scan.checkpoint else None,
            }
        
        return None


# Global singleton instance
scan_manager = ScanManager()
