import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models.schemas import ArtworkType, MediaType, Provider
from services.providers.fanart import FanartProvider
from services.providers.tmdb import TMDBProvider
from services.providers.tvdb import TVDBProvider
from services.providers.mediux import MediuxProvider

@pytest.mark.asyncio
async def test_fanart_provider_movie():
    provider = FanartProvider(api_key="test_key")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hdmovielogo": [{"url": "http://example.com/logo.png", "lang": "en", "likes": "5"}]
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        results = await provider.get_artwork(
            MediaType.MOVIE,
            {"tmdb": "123"},
            [ArtworkType.LOGO]
        )
        
        assert len(results) == 1
        assert results[0].source == Provider.FANART
        assert results[0].image_url == "http://example.com/logo.png"
        assert results[0].score == 5

@pytest.mark.asyncio
async def test_tmdb_provider_movie():
    provider = TMDBProvider(api_key="test_key")
    
    # Mock config response
    mock_config_response = MagicMock()
    mock_config_response.status_code = 200
    mock_config_response.json.return_value = {
        "images": {"secure_base_url": "http://image.tmdb.org/t/p/"}
    }
    
    # Mock images response
    mock_img_response = MagicMock()
    mock_img_response.status_code = 200
    mock_img_response.json.return_value = {
        "posters": [{"file_path": "/poster.jpg", "vote_average": 8.5, "iso_639_1": "en"}]
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_config_response, mock_img_response]
        
        results = await provider.get_artwork(
            MediaType.MOVIE,
            {"tmdb": "123"},
            [ArtworkType.POSTER]
        )
        
        assert len(results) == 1
        assert results[0].source == Provider.TMDB
        assert results[0].image_url == "http://image.tmdb.org/t/p/original/poster.jpg"
        assert results[0].score == 85  # 8.5 * 10

@pytest.mark.asyncio
async def test_mediux_provider():
    provider = MediuxProvider(api_key="test_key")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "result": {
                "sets": [{
                    "name": "Test Set",
                    "user": {"username": "Creator"},
                    "files": [{"id": "xyz", "type": "poster"}]
                }]
            }
        }
    }
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        results = await provider.get_artwork(
            MediaType.MOVIE,
            {"tmdb": "123"},
            [ArtworkType.POSTER]
        )
        
        assert len(results) == 1
        assert results[0].source == Provider.MEDIUX
        assert "xyz" in results[0].image_url
        assert results[0].set_name == "Test Set"
