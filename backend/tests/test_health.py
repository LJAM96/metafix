"""Tests for health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    """Backend health check returns 200."""
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_returns_healthy_status(client: AsyncClient):
    """Health check returns healthy status."""
    response = await client.get("/api/health")
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_returns_version(client: AsyncClient):
    """Health check returns version."""
    response = await client.get("/api/health")
    data = response.json()
    assert "version" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health_endpoint_returns_timestamp(client: AsyncClient):
    """Health check returns timestamp."""
    response = await client.get("/api/health")
    data = response.json()
    assert "timestamp" in data
