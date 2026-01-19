import pytest
from unittest.mock import AsyncMock, patch
from services.edition_manager import EditionManager
from services.edition.modules.video import ResolutionModule, DynamicRangeModule
from services.edition.modules.content import CutModule

@pytest.mark.asyncio
async def test_resolution_module():
    module = ResolutionModule()
    
    metadata = {"Media": [{"width": 3840, "height": 2160, "videoResolution": "4k"}]}
    assert module.extract(metadata) == "4K"
    
    metadata = {"Media": [{"width": 1920, "height": 1080, "videoResolution": "1080"}]}
    assert module.extract(metadata) == "1080p"

@pytest.mark.asyncio
async def test_dynamic_range_module():
    module = DynamicRangeModule()
    
    # Dolby Vision
    metadata = {
        "Media": [{"Part": [{"Stream": [{"streamType": 1, "DOVIPresent": True, "DOVIProfile": 5}]}]}]
    }
    # My implementation checks string "dovi" in DOVIPresent
    metadata = {
        "Media": [{"Part": [{"Stream": [{"streamType": 1, "DOVIPresent": "dovi", "DOVIProfile": 5}]}]}]
    }
    assert module.extract(metadata) == "DV P5"

@pytest.mark.asyncio
async def test_cut_module():
    module = CutModule()
    
    metadata = {"Media": [{"Part": [{"file": "/movies/Blade Runner (1982) [Director's Cut].mkv"}]}]}
    assert module.extract(metadata) == "Director's Cut"

@pytest.mark.asyncio
async def test_edition_manager_generate(test_session):
    manager = EditionManager(test_session)
    
    # Mock PlexService
    mock_plex = AsyncMock()
    mock_plex._request.return_value = {
        "MediaContainer": {
            "Metadata": [{
                "title": "Test Movie",
                "Media": [{
                    "width": 3840, "height": 2160,
                    "videoResolution": "4k",
                    "Part": [{"file": "Test.mkv"}]
                }]
            }]
        }
    }
    
    with patch.object(manager, "_get_plex_service", new_callable=AsyncMock) as mock_get_plex:
        mock_get_plex.return_value = mock_plex
        
        # Should generate "4K" with default config
        result = await manager.generate_edition("123")
        assert "4K" in str(result)
