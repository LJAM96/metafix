import pytest
from unittest.mock import AsyncMock, patch
from services.scheduler_service import SchedulerService
from models.database import Schedule

@pytest.mark.asyncio
async def test_scheduler_add_job():
    service = SchedulerService()
    # Mock scheduler backend
    with patch.object(service, "scheduler") as mock_scheduler:
        schedule = Schedule(
            id=1, 
            name="Test Job", 
            cron_expression="0 0 * * *", 
            enabled=True,
            config="{}"
        )
        service._add_job(schedule)
        mock_scheduler.add_job.assert_called_once()
        kwargs = mock_scheduler.add_job.call_args.kwargs
        assert kwargs["id"] == "1"
        assert kwargs["name"] == "Test Job"

@pytest.mark.asyncio
async def test_scheduler_remove_job():
    service = SchedulerService()
    with patch.object(service, "scheduler") as mock_scheduler:
        service._remove_job(1)
        mock_scheduler.remove_job.assert_called_with("1")
