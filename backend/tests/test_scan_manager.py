"""Tests for scan manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from services.scan_manager import (
    ScanManager,
    ScanStatus,
    ScanAlreadyRunningError,
)


class TestScanManager:
    """Tests for ScanManager class."""
    
    @pytest.fixture
    def fresh_scan_manager(self):
        """Create a fresh ScanManager instance for testing."""
        # Reset singleton
        ScanManager._instance = None
        manager = ScanManager()
        yield manager
        # Cleanup
        ScanManager._instance = None
    
    def test_singleton_pattern(self):
        """ScanManager follows singleton pattern."""
        ScanManager._instance = None
        
        manager1 = ScanManager()
        manager2 = ScanManager()
        
        assert manager1 is manager2
        
        ScanManager._instance = None
    
    def test_initial_state(self, fresh_scan_manager):
        """ScanManager starts in IDLE state."""
        assert fresh_scan_manager.status == ScanStatus.IDLE
        assert fresh_scan_manager.current_scan_id is None
        assert fresh_scan_manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_scan_creates_record(
        self, fresh_scan_manager, test_session: AsyncSession
    ):
        """Starting a scan creates a database record."""
        config = {
            "scan_type": "artwork",
            "libraries": ["1"],
            "check_posters": True,
        }
        
        scan_id = await fresh_scan_manager.start_scan(test_session, config)
        
        assert scan_id is not None
        assert scan_id > 0
        assert fresh_scan_manager.status == ScanStatus.RUNNING
        assert fresh_scan_manager.current_scan_id == scan_id
        
        # Reset state for other tests
        fresh_scan_manager._status = ScanStatus.IDLE
        fresh_scan_manager._current_scan_id = None
    
    @pytest.mark.asyncio
    async def test_prevents_concurrent_scans(
        self, fresh_scan_manager, test_session: AsyncSession
    ):
        """Starting second scan raises ScanAlreadyRunningError."""
        config = {"scan_type": "artwork", "libraries": []}
        
        # Start first scan
        await fresh_scan_manager.start_scan(test_session, config)
        
        # Try to start second scan
        with pytest.raises(ScanAlreadyRunningError):
            await fresh_scan_manager.start_scan(test_session, config)
        
        # Cleanup
        fresh_scan_manager._status = ScanStatus.IDLE
        fresh_scan_manager._current_scan_id = None
    
    @pytest.mark.asyncio
    async def test_pause_blocks_processing(
        self, fresh_scan_manager, test_session: AsyncSession
    ):
        """Pause stops item processing."""
        config = {"scan_type": "artwork"}
        await fresh_scan_manager.start_scan(test_session, config)
        
        # Pause scan
        result = await fresh_scan_manager.pause_scan(test_session)
        
        assert result is True
        assert fresh_scan_manager.status == ScanStatus.PAUSED
        assert not fresh_scan_manager._pause_event.is_set()
        
        # Cleanup
        fresh_scan_manager._status = ScanStatus.IDLE
        fresh_scan_manager._current_scan_id = None
        fresh_scan_manager._pause_event.set()
    
    @pytest.mark.asyncio
    async def test_resume_continues_processing(
        self, fresh_scan_manager, test_session: AsyncSession
    ):
        """Resume continues from paused state."""
        config = {"scan_type": "artwork"}
        await fresh_scan_manager.start_scan(test_session, config)
        await fresh_scan_manager.pause_scan(test_session)
        
        # Resume scan
        result = await fresh_scan_manager.resume_scan(test_session)
        
        assert result is True
        assert fresh_scan_manager.status == ScanStatus.RUNNING
        assert fresh_scan_manager._pause_event.is_set()
        
        # Cleanup
        fresh_scan_manager._status = ScanStatus.IDLE
        fresh_scan_manager._current_scan_id = None
    
    @pytest.mark.asyncio
    async def test_cancel_stops_scan(
        self, fresh_scan_manager, test_session: AsyncSession
    ):
        """Cancel terminates scan and updates status."""
        config = {"scan_type": "artwork"}
        await fresh_scan_manager.start_scan(test_session, config)
        
        # Cancel scan
        result = await fresh_scan_manager.cancel_scan(test_session)
        
        assert result is True
        assert fresh_scan_manager._cancel_requested is True
        
        # Cleanup
        fresh_scan_manager._status = ScanStatus.IDLE
        fresh_scan_manager._current_scan_id = None
        fresh_scan_manager._cancel_requested = False
    
    @pytest.mark.asyncio
    async def test_pause_when_not_running_returns_false(self, fresh_scan_manager, test_session):
        """Pausing when not running returns False."""
        result = await fresh_scan_manager.pause_scan(test_session)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resume_when_not_paused_returns_false(self, fresh_scan_manager, test_session):
        """Resuming when not paused returns False."""
        result = await fresh_scan_manager.resume_scan(test_session)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_when_not_running_returns_false(self, fresh_scan_manager, test_session):
        """Cancelling when not running returns False."""
        result = await fresh_scan_manager.cancel_scan(test_session)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_subscribe_returns_queue(self, fresh_scan_manager):
        """Subscribe returns a queue that receives events."""
        queue = await fresh_scan_manager.subscribe()
        
        assert queue is not None
        assert queue in fresh_scan_manager._subscribers
        
        # Should receive initial connected event
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "connected"
        
        # Cleanup
        fresh_scan_manager.unsubscribe(queue)
    
    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_subscribers(self, fresh_scan_manager):
        """Broadcast sends events to all subscribed clients."""
        queue1 = await fresh_scan_manager.subscribe()
        queue2 = await fresh_scan_manager.subscribe()
        
        # Clear initial events
        await queue1.get()
        await queue2.get()
        
        # Broadcast event
        await fresh_scan_manager._broadcast({"type": "test_event", "data": "test"})
        
        event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
        
        assert event1["type"] == "test_event"
        assert event2["type"] == "test_event"
        
        # Cleanup
        fresh_scan_manager.unsubscribe(queue1)
        fresh_scan_manager.unsubscribe(queue2)
    
    @pytest.mark.asyncio
    async def test_get_progress_returns_current_state(
        self, fresh_scan_manager, test_session
    ):
        """get_progress returns current scan state."""
        config = {"scan_type": "artwork"}
        scan_id = await fresh_scan_manager.start_scan(test_session, config)
        
        # Update progress
        fresh_scan_manager._progress["processed"] = 50
        fresh_scan_manager._progress["total"] = 100
        fresh_scan_manager._progress["issues_found"] = 5
        
        progress = fresh_scan_manager.get_progress()
        
        assert progress["scan_id"] == scan_id
        assert progress["status"] == ScanStatus.RUNNING.value
        assert progress["processed"] == 50
        assert progress["total"] == 100
        assert progress["issues_found"] == 5
        
        # Cleanup
        fresh_scan_manager._status = ScanStatus.IDLE
        fresh_scan_manager._current_scan_id = None


class TestScanAPI:
    """Integration tests for scan API endpoints."""
    
    @pytest.mark.asyncio
    async def test_start_scan_returns_scan_id(self, client):
        """Start scan endpoint returns scan ID."""
        # Reset singleton for clean state
        from services.scan_manager import scan_manager
        scan_manager._status = ScanStatus.IDLE
        scan_manager._current_scan_id = None
        
        with patch("routers.scan.scan_manager") as mock_manager:
            mock_manager.start_scan = AsyncMock(return_value=1)
            mock_manager.run_scan = AsyncMock()
            
            response = await client.post(
                "/api/scan/start",
                json={
                    "config": {
                        "scan_type": "artwork",
                        "libraries": ["1"],
                    }
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["scan_id"] == 1
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_scan_status_returns_progress(self, client, test_session):
        """Scan status endpoint returns current progress."""
        response = await client.get("/api/scan/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "total_items" in data
        assert "processed_items" in data
