import asyncio
import logging
from typing import Optional, Set

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.database import Issue, Suggestion
from services.config_service import ConfigService
from services.plex_service import PlexService

logger = logging.getLogger(__name__)

class AutoFixService:
    """Service to automatically fix pending issues."""
    
    _instance: Optional["AutoFixService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._running = False
        self._cancel_requested = False
        self._progress = {
            "processed": 0,
            "total": 0,
            "applied": 0,
            "skipped": 0,
            "failed": 0,
        }
        self._subscribers: Set[asyncio.Queue] = set()
        
    @property
    def is_running(self) -> bool:
        return self._running
        
    @property
    def progress(self) -> dict:
        return self._progress
        
    async def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        await queue.put({"type": "connected", **self._progress})
        return queue
        
    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)
        
    async def _broadcast(self, event: dict):
        for queue in list(self._subscribers):
            try:
                await queue.put(event)
            except Exception:
                self._subscribers.discard(queue)

    async def start(
        self,
        db_factory,
        scan_id: Optional[int] = None,
        skip_unmatched: bool = True,
        min_score: int = 0
    ):
        """Start auto-fix process."""
        if self._running:
            raise RuntimeError("Auto-fix is already running")
            
        self._running = True
        self._cancel_requested = False
        self._progress = {
            "processed": 0,
            "total": 0,
            "applied": 0,
            "skipped": 0,
            "failed": 0,
        }
        
        asyncio.create_task(self._run(db_factory, scan_id, skip_unmatched, min_score))
        return True

    async def cancel(self):
        """Cancel auto-fix."""
        if self._running:
            self._cancel_requested = True

    async def _run(self, db_factory, scan_id, skip_unmatched, min_score):
        try:
            async with db_factory() as db:
                # Fetch pending issues
                query = select(Issue).where(Issue.status == "pending")
                if scan_id:
                    query = query.where(Issue.scan_id == scan_id)
                
                # Eager load suggestions to pick the best one
                query = query.options(selectinload(Issue.suggestions))
                
                result = await db.execute(query)
                issues = result.scalars().all()
                
                self._progress["total"] = len(issues)
                await self._broadcast({"type": "started", "total": len(issues)})
                
                if not issues:
                    self._running = False
                    await self._broadcast({"type": "completed", **self._progress})
                    return

                # Initialize Plex
                config_service = ConfigService(db)
                plex_url, plex_token, _ = await config_service.get_plex_config()
                if not plex_url or not plex_token:
                    logger.error("Plex not configured for auto-fix")
                    self._running = False
                    return
                    
                plex = PlexService(plex_url, plex_token)
                
                try:
                    for issue in issues:
                        if self._cancel_requested:
                            break
                            
                        processed = False
                        applied = False
                        skipped = False
                        
                        # Check unmatched
                        if skip_unmatched and issue.issue_type == "no_match":
                            # Or check if matched?
                            # Usually scanner marks no_match based on guid.
                            # If unmatched, we might skip applying artwork because it might be wrong item
                            skipped = True
                        else:
                            # Find best suggestion
                            best_suggestion = None
                            if issue.suggestions:
                                # Sort by score desc, then provider priority if score equal?
                                # Assuming suggestions already sorted or score reflects priority
                                # Let's assume highest score is best
                                sorted_suggestions = sorted(
                                    issue.suggestions, 
                                    key=lambda s: s.score, 
                                    reverse=True
                                )
                                best = sorted_suggestions[0]
                                if best.score >= min_score:
                                    best_suggestion = best
                            
                            if best_suggestion:
                                # Apply
                                try:
                                    success = False
                                    if best_suggestion.artwork_type == "poster":
                                        success = await plex.upload_poster(issue.plex_rating_key, best_suggestion.image_url)
                                        if success:
                                            await plex.lock_poster(issue.plex_rating_key)
                                    elif best_suggestion.artwork_type == "background":
                                        success = await plex.upload_background(issue.plex_rating_key, best_suggestion.image_url)
                                        if success:
                                            await plex.lock_background(issue.plex_rating_key)
                                            
                                    if success:
                                        issue.status = "applied"
                                        best_suggestion.is_selected = True
                                        applied = True
                                    else:
                                        self._progress["failed"] += 1
                                except Exception as e:
                                    logger.error(f"Failed to apply auto-fix for {issue.id}: {e}")
                                    self._progress["failed"] += 1
                            else:
                                skipped = True
                        
                        if skipped:
                            # Maybe mark as skipped in DB or just leave pending?
                            # Ideally leave pending so manual review can handle it?
                            # Or mark as skipped if we want to clear the queue.
                            # Let's leave as pending but count as skipped in this run
                            self._progress["skipped"] += 1
                            
                        if applied:
                            self._progress["applied"] += 1
                            
                        self._progress["processed"] += 1
                        
                        # Commit every item or batch? Every item is safer for long running
                        if applied:
                            await db.commit()
                            
                        await self._broadcast({"type": "progress", **self._progress})
                        
                finally:
                    await plex.close()
                    
        except Exception as e:
            logger.exception("Auto-fix failed")
        finally:
            self._running = False
            await self._broadcast({"type": "completed", **self._progress})

# Global instance
autofix_service = AutoFixService()
