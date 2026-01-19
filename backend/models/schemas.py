"""Pydantic schemas for API request/response models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# Enums
class ScanType(str, Enum):
    ARTWORK = "artwork"
    EDITION = "edition"
    BOTH = "both"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class IssueType(str, Enum):
    NO_MATCH = "no_match"
    NO_POSTER = "no_poster"
    NO_BACKGROUND = "no_background"
    NO_LOGO = "no_logo"
    PLACEHOLDER_POSTER = "placeholder_poster"
    PLACEHOLDER_BACKGROUND = "placeholder_background"


class IssueStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


class MediaType(str, Enum):
    MOVIE = "movie"
    SHOW = "show"
    SEASON = "season"
    EPISODE = "episode"


class ArtworkType(str, Enum):
    POSTER = "poster"
    BACKGROUND = "background"
    LOGO = "logo"


class Provider(str, Enum):
    FANART = "fanart"
    MEDIUX = "mediux"
    TMDB = "tmdb"
    TVDB = "tvdb"
    PLEX = "plex"


# Health Check
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Plex Connection
class PlexConnectRequest(BaseModel):
    url: str = Field(..., description="Plex server URL")
    token: str = Field(..., description="Plex authentication token")


class PlexConnectResponse(BaseModel):
    success: bool
    message: str
    server_name: Optional[str] = None


class PlexLibrary(BaseModel):
    id: str
    name: str
    type: str
    item_count: int


class PlexLibrariesResponse(BaseModel):
    libraries: list[PlexLibrary]


# Scan Configuration
class ScanConfig(BaseModel):
    scan_type: ScanType = ScanType.BOTH
    libraries: list[str] = Field(default_factory=list, description="Library IDs to scan")
    check_posters: bool = True
    check_backgrounds: bool = True
    check_logos: bool = True
    check_unmatched: bool = True
    check_placeholders: bool = True
    edition_enabled: bool = True
    backup_editions: bool = True


class ScanStartRequest(BaseModel):
    config: ScanConfig


class ScanStatusResponse(BaseModel):
    id: int
    scan_type: ScanType
    status: ScanStatus
    total_items: int
    processed_items: int
    issues_found: int
    editions_updated: int
    current_library: Optional[str] = None
    current_item: Optional[str] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0


class ScanProgressEvent(BaseModel):
    type: str = "progress"
    scan_id: int
    processed: int
    total: int
    current_item: Optional[str] = None
    current_library: Optional[str] = None


# Issues
class SuggestionResponse(BaseModel):
    id: int
    source: Provider
    artwork_type: ArtworkType
    image_url: str
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    score: int = 0
    set_name: Optional[str] = None
    creator_name: Optional[str] = None
    is_selected: bool = False


class IssueResponse(BaseModel):
    id: int
    plex_rating_key: str
    plex_guid: Optional[str] = None
    title: str
    year: Optional[int] = None
    media_type: MediaType
    issue_type: IssueType
    status: IssueStatus
    library_name: Optional[str] = None
    created_at: datetime
    suggestions: list[SuggestionResponse] = Field(default_factory=list)


class IssueListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    issues: list[IssueResponse]


class IssueAcceptRequest(BaseModel):
    suggestion_id: int


# Edition Configuration
class EditionModuleConfig(BaseModel):
    name: str
    enabled: bool = True
    order: int


class EditionSettingsRequest(BaseModel):
    enabled_modules: list[str]
    module_order: list[str]
    separator: str = " . "
    excluded_languages: list[str] = Field(default_factory=lambda: ["English"])
    skip_multiple_audio_tracks: bool = True
    rating_source: str = "imdb"
    tmdb_api_key: Optional[str] = None


class EditionSettingsResponse(BaseModel):
    enabled_modules: list[str]
    module_order: list[str]
    separator: str
    excluded_languages: list[str]
    skip_multiple_audio_tracks: bool
    rating_source: str


# Schedule
class ScheduleCreateRequest(BaseModel):
    name: str
    cron_expression: str
    scan_type: ScanType = ScanType.BOTH
    config: ScanConfig
    auto_commit: bool = False
    auto_commit_skip_unmatched: bool = True
    auto_commit_min_score: int = 0


class ScheduleResponse(BaseModel):
    id: int
    name: str
    enabled: bool
    cron_expression: str
    scan_type: ScanType
    auto_commit: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]


# Provider Settings
class ProviderSettingsRequest(BaseModel):
    fanart_api_key: Optional[str] = None
    mediux_api_key: Optional[str] = None
    tmdb_api_key: Optional[str] = None
    tvdb_api_key: Optional[str] = None
    provider_priority: list[Provider] = Field(
        default_factory=lambda: [
            Provider.FANART,
            Provider.MEDIUX,
            Provider.TMDB,
            Provider.TVDB,
            Provider.PLEX,
        ]
    )


class ProviderTestResponse(BaseModel):
    provider: Provider
    success: bool
    message: str
