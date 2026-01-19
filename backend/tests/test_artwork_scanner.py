"""Tests for artwork scanner."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from services.artwork_scanner import ArtworkScanner, ArtworkIssue, IssueType
from services.plex_service import PlexItem


def create_mock_item(
    rating_key: str = "123",
    title: str = "Test Movie",
    year: int = 2024,
    item_type: str = "movie",
    guid: str = "plex://movie/abc",
    thumb: str = "/library/metadata/123/thumb",
    art: str = "/library/metadata/123/art",
    guids: list = None,
) -> PlexItem:
    """Create a mock PlexItem for testing."""
    return PlexItem(
        rating_key=rating_key,
        title=title,
        year=year,
        type=item_type,
        guid=guid,
        thumb=thumb,
        art=art,
        library_name="Movies",
        added_at=1234567890,
        guids=guids or [{"id": "tmdb://12345"}, {"id": "imdb://tt1234567"}],
    )


class TestArtworkScanner:
    """Tests for ArtworkScanner class."""
    
    @pytest.fixture
    def mock_plex(self):
        """Create a mock PlexService."""
        plex = MagicMock()
        plex.get_poster_url = AsyncMock(return_value="http://plex/thumb?token=abc")
        plex.close = AsyncMock()
        return plex
    
    @pytest.mark.asyncio
    async def test_detect_missing_poster(self, mock_plex):
        """Items without thumb attribute are flagged as missing poster."""
        scanner = ArtworkScanner(mock_plex)
        
        item = create_mock_item(thumb=None)
        
        issues = await scanner.scan_item(item)
        
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.NO_POSTER
        assert issues[0].title == "Test Movie"
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_detect_missing_background(self, mock_plex):
        """Items without art attribute are flagged as missing background."""
        scanner = ArtworkScanner(mock_plex)
        
        item = create_mock_item(art=None)
        
        issues = await scanner.scan_item(item)
        
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.NO_BACKGROUND
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_detect_unmatched_local_guid(self, mock_plex):
        """Items with local:// GUID are flagged as unmatched."""
        scanner = ArtworkScanner(mock_plex)
        
        item = create_mock_item(guid="local://456")
        
        issues = await scanner.scan_item(item)
        
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.NO_MATCH
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_unmatched_returns_only_no_match(self, mock_plex):
        """Unmatched items only return NO_MATCH, not missing artwork."""
        scanner = ArtworkScanner(mock_plex)
        
        # Item with local GUID and no artwork
        item = create_mock_item(guid="local://456", thumb=None, art=None)
        
        issues = await scanner.scan_item(item)
        
        # Should only have one issue: NO_MATCH
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.NO_MATCH
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_detect_placeholder_landscape_poster(self, mock_plex):
        """Landscape images (ratio > 1.0) are flagged as placeholder posters."""
        scanner = ArtworkScanner(mock_plex)
        
        item = create_mock_item()
        
        # Mock fetching a landscape image (16:9 = 1.78 ratio)
        with patch.object(scanner, "_get_image_aspect_ratio", new_callable=AsyncMock) as mock_ratio:
            mock_ratio.return_value = 1.78  # 16:9 landscape
            
            issues = await scanner.scan_item(item)
            
            placeholder_issues = [i for i in issues if i.issue_type == IssueType.PLACEHOLDER_POSTER]
            assert len(placeholder_issues) == 1
            assert placeholder_issues[0].details.get("detected_aspect_ratio") == 1.78
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_valid_poster_not_flagged(self, mock_plex):
        """Valid portrait posters (2:3 ratio) are not flagged."""
        scanner = ArtworkScanner(mock_plex)
        
        item = create_mock_item()
        
        # Mock fetching a proper poster (2:3 = 0.667 ratio)
        with patch.object(scanner, "_get_image_aspect_ratio", new_callable=AsyncMock) as mock_ratio:
            mock_ratio.return_value = 0.667  # 2:3 portrait
            
            issues = await scanner.scan_item(item)
            
            # No issues should be found
            assert len(issues) == 0
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_external_ids_extracted(self, mock_plex):
        """External IDs are correctly extracted from issues."""
        scanner = ArtworkScanner(mock_plex)
        
        item = PlexItem(
            rating_key="123",
            title="Test Movie",
            year=2024,
            type="movie",
            guid="local://123",  # Unmatched to trigger an issue
            thumb="/thumb",
            art="/art",
            library_name="Movies",
            added_at=None,
            guids=["tmdb://999", "imdb://tt9999999", "tvdb://888"],
        )
        
        issues = await scanner.scan_item(item)
        
        assert len(issues) == 1
        assert issues[0].external_ids.get("tmdb") == "999"
        assert issues[0].external_ids.get("imdb") == "tt9999999"
        assert issues[0].external_ids.get("tvdb") == "888"
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_scanner_respects_check_flags(self, mock_plex):
        """Scanner respects check_* configuration flags."""
        # Scanner with only poster checking enabled
        scanner = ArtworkScanner(
            mock_plex,
            check_posters=True,
            check_backgrounds=False,
            check_logos=False,
            check_unmatched=False,
            check_placeholders=False,
        )
        
        # Item missing both poster and background
        item = create_mock_item(thumb=None, art=None)
        
        issues = await scanner.scan_item(item)
        
        # Should only detect missing poster, not background
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.NO_POSTER
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_multiple_issues_detected(self, mock_plex):
        """Multiple issues can be detected for a single item."""
        scanner = ArtworkScanner(
            mock_plex,
            check_placeholders=False,  # Disable to simplify test
        )
        
        # Item missing both poster and background
        item = create_mock_item(thumb=None, art=None)
        
        issues = await scanner.scan_item(item)
        
        assert len(issues) == 2
        issue_types = {i.issue_type for i in issues}
        assert IssueType.NO_POSTER in issue_types
        assert IssueType.NO_BACKGROUND in issue_types
        
        await scanner.close()
    
    @pytest.mark.asyncio
    async def test_no_issues_for_complete_item(self, mock_plex):
        """Complete items with valid artwork return no issues."""
        scanner = ArtworkScanner(mock_plex)
        
        item = create_mock_item()
        
        # Mock valid aspect ratios
        with patch.object(scanner, "_get_image_aspect_ratio", new_callable=AsyncMock) as mock_ratio:
            mock_ratio.return_value = 0.667  # Valid poster ratio
            
            issues = await scanner.scan_item(item)
            
            assert len(issues) == 0
        
        await scanner.close()


class TestPlexItemProperties:
    """Tests for PlexItem helper properties."""
    
    def test_is_matched_with_valid_guid(self):
        """Items with valid GUIDs are matched."""
        item = create_mock_item(guid="plex://movie/abc123")
        assert item.is_matched is True
    
    def test_is_matched_with_local_guid(self):
        """Items with local:// GUIDs are unmatched."""
        item = create_mock_item(guid="local://123")
        assert item.is_matched is False
    
    def test_is_matched_with_no_guid(self):
        """Items with no GUID are unmatched."""
        item = create_mock_item(guid=None)
        assert item.is_matched is False
    
    def test_has_poster_true(self):
        """Items with thumb have poster."""
        item = create_mock_item(thumb="/library/metadata/123/thumb")
        assert item.has_poster is True
    
    def test_has_poster_false(self):
        """Items without thumb have no poster."""
        item = create_mock_item(thumb=None)
        assert item.has_poster is False
    
    def test_has_background_true(self):
        """Items with art have background."""
        item = create_mock_item(art="/library/metadata/123/art")
        assert item.has_background is True
    
    def test_has_background_false(self):
        """Items without art have no background."""
        item = create_mock_item(art=None)
        assert item.has_background is False
    
    def test_get_external_id_tmdb(self):
        """Can extract TMDB ID from GUIDs."""
        item = PlexItem(
            rating_key="1",
            title="Test",
            year=2024,
            type="movie",
            guid="plex://movie/abc",
            thumb=None,
            art=None,
            library_name="Movies",
            added_at=None,
            guids=["tmdb://12345", "imdb://tt9999999"],
        )
        assert item.get_external_id("tmdb") == "12345"
        assert item.get_external_id("imdb") == "tt9999999"
        assert item.get_external_id("tvdb") is None
