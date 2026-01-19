"""Tests for database initialization and models."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Config, Scan, Issue, Schedule, EditionConfig


@pytest.mark.asyncio
async def test_database_connection(test_session: AsyncSession):
    """Database is accessible."""
    result = await test_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_config_table_exists(test_session: AsyncSession):
    """Config table exists and can be queried."""
    result = await test_session.execute(select(Config))
    configs = result.scalars().all()
    assert isinstance(configs, list)


@pytest.mark.asyncio
async def test_scans_table_exists(test_session: AsyncSession):
    """Scans table exists and can be queried."""
    result = await test_session.execute(select(Scan))
    scans = result.scalars().all()
    assert isinstance(scans, list)


@pytest.mark.asyncio
async def test_issues_table_exists(test_session: AsyncSession):
    """Issues table exists and can be queried."""
    result = await test_session.execute(select(Issue))
    issues = result.scalars().all()
    assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_schedules_table_exists(test_session: AsyncSession):
    """Schedules table exists and can be queried."""
    result = await test_session.execute(select(Schedule))
    schedules = result.scalars().all()
    assert isinstance(schedules, list)


@pytest.mark.asyncio
async def test_edition_config_table_exists(test_session: AsyncSession):
    """Edition config table exists and can be queried."""
    result = await test_session.execute(select(EditionConfig))
    configs = result.scalars().all()
    assert isinstance(configs, list)


@pytest.mark.asyncio
async def test_can_create_scan(test_session: AsyncSession):
    """Can create a scan record."""
    import json
    
    scan = Scan(
        scan_type="artwork",
        status="pending",
        config=json.dumps({"libraries": [], "check_posters": True}),
        total_items=0,
        processed_items=0,
        issues_found=0,
        editions_updated=0,
    )
    test_session.add(scan)
    await test_session.commit()
    
    result = await test_session.execute(select(Scan))
    scans = result.scalars().all()
    assert len(scans) == 1
    assert scans[0].scan_type == "artwork"


@pytest.mark.asyncio
async def test_can_create_config(test_session: AsyncSession):
    """Can create a config record."""
    config = Config(
        key="test_key",
        value="test_value",
        encrypted=False,
    )
    test_session.add(config)
    await test_session.commit()
    
    result = await test_session.execute(
        select(Config).where(Config.key == "test_key")
    )
    saved_config = result.scalar_one()
    assert saved_config.value == "test_value"
