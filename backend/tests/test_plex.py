"""Tests for Plex integration."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from services.plex_service import PlexService, PlexConnectionError, PlexAuthenticationError


class TestPlexService:
    """Tests for PlexService class."""
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Valid Plex credentials establish connection."""
        plex = PlexService("http://localhost:32400", "valid-token")
        
        mock_response = {
            "MediaContainer": {
                "friendlyName": "My Plex Server",
                "version": "1.32.0",
            }
        }
        
        with patch.object(plex, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            success, message, server_name = await plex.test_connection()
            
            assert success is True
            assert server_name == "My Plex Server"
            assert "successful" in message.lower()
    
    @pytest.mark.asyncio
    async def test_test_connection_invalid_token(self):
        """Invalid token returns failure."""
        plex = PlexService("http://localhost:32400", "invalid-token")
        
        with patch.object(plex, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = PlexAuthenticationError("Invalid Plex token")
            
            success, message, server_name = await plex.test_connection()
            
            assert success is False
            assert server_name is None
            assert "invalid" in message.lower() or "token" in message.lower()
    
    @pytest.mark.asyncio
    async def test_test_connection_unreachable_server(self):
        """Unreachable server returns appropriate error."""
        plex = PlexService("http://unreachable:32400", "token")
        
        with patch.object(plex, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = PlexConnectionError("Cannot connect to Plex server")
            
            success, message, server_name = await plex.test_connection()
            
            assert success is False
            assert server_name is None
            assert "connect" in message.lower()
    
    @pytest.mark.asyncio
    async def test_get_libraries_returns_correct_structure(self):
        """Libraries returned with correct structure."""
        plex = PlexService("http://localhost:32400", "token")
        
        mock_response = {
            "MediaContainer": {
                "Directory": [
                    {
                        "key": "1",
                        "title": "Movies",
                        "type": "movie",
                        "count": 500,
                        "uuid": "abc-123",
                    },
                    {
                        "key": "2",
                        "title": "TV Shows",
                        "type": "show",
                        "count": 100,
                        "uuid": "def-456",
                    },
                    {
                        "key": "3",
                        "title": "Music",
                        "type": "artist",
                        "count": 200,
                        "uuid": "ghi-789",
                    },
                ]
            }
        }
        
        with patch.object(plex, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            libraries = await plex.get_libraries()
            
            # Should only return movie and show libraries, not music
            assert len(libraries) == 2
            
            # Check first library
            assert libraries[0].id == "1"
            assert libraries[0].name == "Movies"
            assert libraries[0].type == "movie"
            assert libraries[0].item_count == 500
            
            # Check second library
            assert libraries[1].id == "2"
            assert libraries[1].name == "TV Shows"
            assert libraries[1].type == "show"
    
    @pytest.mark.asyncio
    async def test_get_library_items_pagination(self):
        """Library items are paginated correctly."""
        plex = PlexService("http://localhost:32400", "token")
        
        # Mock library info request
        lib_response = {
            "MediaContainer": {
                "Directory": [{"title": "Movies"}]
            }
        }
        
        # Mock items request
        items_response = {
            "MediaContainer": {
                "totalSize": 100,
                "Metadata": [
                    {
                        "ratingKey": "123",
                        "title": "Test Movie",
                        "year": 2024,
                        "type": "movie",
                        "guid": "plex://movie/abc",
                        "thumb": "/library/metadata/123/thumb",
                        "art": "/library/metadata/123/art",
                        "Guid": [
                            {"id": "tmdb://12345"},
                            {"id": "imdb://tt1234567"},
                        ],
                    }
                ]
            }
        }
        
        with patch.object(plex, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [lib_response, items_response]
            
            items, total = await plex.get_library_items("1", start=0, size=50)
            
            assert total == 100
            assert len(items) == 1
            assert items[0].rating_key == "123"
            assert items[0].title == "Test Movie"
            assert items[0].is_matched is True
            assert items[0].has_poster is True
            assert items[0].get_external_id("tmdb") == "12345"
            assert items[0].get_external_id("imdb") == "tt1234567"
    
    @pytest.mark.asyncio
    async def test_plex_item_is_matched_local_guid(self):
        """Items with local:// GUID are detected as unmatched."""
        plex = PlexService("http://localhost:32400", "token")
        
        lib_response = {"MediaContainer": {"Directory": [{"title": "Movies"}]}}
        items_response = {
            "MediaContainer": {
                "totalSize": 1,
                "Metadata": [
                    {
                        "ratingKey": "456",
                        "title": "Unmatched Movie",
                        "type": "movie",
                        "guid": "local://456",
                        "thumb": None,
                        "art": None,
                    }
                ]
            }
        }
        
        with patch.object(plex, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [lib_response, items_response]
            
            items, _ = await plex.get_library_items("1")
            
            assert items[0].is_matched is False
            assert items[0].has_poster is False


class TestPlexAPI:
    """Integration tests for Plex API endpoints."""
    
    @pytest.mark.asyncio
    async def test_plex_status_not_configured(self, client: AsyncClient):
        """Plex status returns not connected when not configured."""
        response = await client.get("/api/plex/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert data["server_name"] is None
    
    @pytest.mark.asyncio
    async def test_plex_libraries_not_configured(self, client: AsyncClient):
        """Plex libraries returns error when not configured."""
        response = await client.get("/api/plex/libraries")
        
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_plex_connect_with_valid_credentials(
        self, client: AsyncClient, test_session
    ):
        """Connecting with valid credentials saves configuration."""
        with patch(
            "routers.plex.PlexService"
        ) as MockPlexService:
            mock_instance = MagicMock()
            mock_instance.test_connection = AsyncMock(
                return_value=(True, "Connection successful", "Test Server")
            )
            mock_instance.close = AsyncMock()
            MockPlexService.return_value = mock_instance
            
            response = await client.post(
                "/api/plex/connect",
                json={
                    "url": "http://localhost:32400",
                    "token": "test-token",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["server_name"] == "Test Server"
    
    @pytest.mark.asyncio
    async def test_plex_connect_with_invalid_credentials(self, client: AsyncClient):
        """Connecting with invalid credentials returns failure."""
        with patch(
            "routers.plex.PlexService"
        ) as MockPlexService:
            mock_instance = MagicMock()
            mock_instance.test_connection = AsyncMock(
                return_value=(False, "Invalid Plex token", None)
            )
            mock_instance.close = AsyncMock()
            MockPlexService.return_value = mock_instance
            
            response = await client.post(
                "/api/plex/connect",
                json={
                    "url": "http://localhost:32400",
                    "token": "invalid-token",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "invalid" in data["message"].lower()
