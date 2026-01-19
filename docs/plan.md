# MetaFix - Complete Technical Plan

> **Version:** 1.0  
> **Last Updated:** January 2026  
> **Status:** Planning Complete - Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature Overview](#feature-overview)
3. [Technology Stack](#technology-stack)
4. [Architecture](#architecture)
5. [API Research Summary](#api-research-summary)
6. [Database Schema](#database-schema)
7. [Module 1: Artwork Scanner](#module-1-artwork-scanner)
8. [Module 2: Edition Manager](#module-2-edition-manager)
9. [Scan Management System](#scan-management-system)
10. [Scheduling & Automation](#scheduling--automation)
11. [User Interface Design](#user-interface-design)
12. [Project Structure](#project-structure)
13. [Implementation Plan](#implementation-plan)
14. [Testing Strategy](#testing-strategy)
15. [Deployment](#deployment)

---

## Executive Summary

**MetaFix** is a comprehensive Plex library management tool that provides two core modules:

1. **Artwork Scanner** - Detects and fixes missing/incorrect artwork (posters, backgrounds, logos) using multiple metadata sources
2. **Edition Manager** - Automatically generates rich Edition metadata for movies based on technical and content information

The tool differentiates itself from existing solutions (like AURA) by:
- Scanning entire libraries for issues (not just browsing)
- Aggregating artwork from multiple sources with configurable priority
- Detecting placeholder artwork (wrong aspect ratio screenshots)
- Supporting both manual review and fully automated fixes
- Integrating Edition metadata management

---

## Feature Overview

### Artwork Scanner Features

| Feature | Description |
|---------|-------------|
| **Missing Artwork Detection** | Scan for missing posters, backgrounds, and logos |
| **Unmatched Item Detection** | Find items with no metadata match |
| **Placeholder Detection** | Identify video screenshots used as posters (wrong aspect ratio) |
| **Multi-Source Artwork** | Aggregate from Fanart.tv, Mediux, TMDB, TVDB, Plex |
| **Configurable Priority** | User-defined provider priority order |
| **Manual Review** | Browse and select artwork for each issue |
| **Auto-Fix Mode** | Automatically apply top suggestions |
| **Artwork Locking** | Lock applied artwork to prevent Plex overwriting |

### Edition Manager Features

| Feature | Description |
|---------|-------------|
| **22 Metadata Modules** | Resolution, AudioCodec, Bitrate, HDR, Cut, Release, etc. |
| **Customizable Order** | User-defined module order via drag-and-drop |
| **Module Toggle** | Enable/disable individual modules |
| **Applies to All Items** | Works on matched items regardless of artwork status |
| **Backup & Restore** | Backup edition data before processing |
| **TMDB Integration** | Required for IMDb ratings via TMDB API |

### Scan Management Features

| Feature | Description |
|---------|-------------|
| **Singleton Scans** | Only one scan runs at a time server-wide |
| **Client Independence** | Scans continue if browser closes |
| **Pause/Resume** | User can pause and resume scans |
| **Cancel** | User can cancel running scans |
| **Crash Recovery** | Resume from checkpoint after server restart |
| **Multi-Client Sync** | All clients see same scan state |

### Automation Features

| Feature | Description |
|---------|-------------|
| **Cron Scheduling** | Schedule scans with cron expressions |
| **Scan Type Selection** | Run artwork scan, edition scan, or both |
| **Auto-Commit** | Automatically apply fixes after scheduled scans |
| **Preset Schedules** | Daily, weekly, monthly presets |

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Frontend** | Next.js 14 + React | User preference, SSR capabilities |
| **UI Components** | shadcn/UI + Tailwind CSS | Modern, accessible components |
| **Backend** | Python FastAPI | User preference, great async support |
| **Database** | SQLite | Lightweight, no setup, file-based |
| **Task Queue** | APScheduler | Built-in Python scheduling |
| **Real-time** | SSE (Server-Sent Events) | Simple, reliable progress streaming |
| **Deployment** | Docker | Self-hosted alongside Plex |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Frontend Clients                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                                 │
│   │ Client A │  │ Client B │  │ Client C │  (can connect/disconnect)       │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘                                 │
│        └─────────────┼─────────────┘                                        │
│                      │ SSE + REST API                                       │
└──────────────────────┼──────────────────────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────────────────────┐
│                      │            Backend (FastAPI)                         │
│  ┌───────────────────┴────────────────────┐                                │
│  │              API Layer                  │                                │
│  │  /api/scan, /api/issues, /api/artwork  │                                │
│  │  /api/edition, /api/schedules          │                                │
│  └───────────────────┬────────────────────┘                                │
│                      │                                                      │
│  ┌───────────────────┴────────────────────┐                                │
│  │         Scan Manager (Singleton)        │◄──────┐                       │
│  │  • Enforces single scan                 │       │                       │
│  │  • Manages pause/resume/cancel          │       │                       │
│  │  • Broadcasts to all clients            │       │                       │
│  └───────────────────┬────────────────────┘       │                       │
│                      │                             │                       │
│  ┌──────────┬────────┴─────────┬──────────┐       │                       │
│  │          │                  │          │       │                       │
│  ▼          ▼                  ▼          ▼       │                       │
│ ┌────────┐ ┌────────┐ ┌────────────┐ ┌────────┐  │                       │
│ │Artwork │ │Edition │ │  AutoFix   │ │  Plex  │  │                       │
│ │Scanner │ │Manager │ │  Service   │ │Service │  │                       │
│ └───┬────┘ └───┬────┘ └────────────┘ └────────┘  │                       │
│     │          │                                   │                       │
│     ▼          ▼                                   │                       │
│ ┌──────────────────────────────────────────────┐  │                       │
│ │              Metadata Providers              │  │                       │
│ │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│  │                       │
│ │  │Fanart  │ │Mediux  │ │ TMDB   │ │ TVDB   ││  │                       │
│ │  └────────┘ └────────┘ └────────┘ └────────┘│  │                       │
│ └──────────────────────────────────────────────┘  │                       │
│                      │                             │                       │
│  ┌───────────────────┴────────────────────┐       │                       │
│  │           Scheduler (APScheduler)       │───────┘                       │
│  │  • Cron-based triggers                  │                               │
│  │  • Auto-commit after scans              │                               │
│  └─────────────────────────────────────────┘                               │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │     SQLite Database     │
          │  • Configuration        │
          │  • Scan state           │
          │  • Issues & suggestions │
          │  • Edition backups      │
          │  • Schedules            │
          └─────────────────────────┘
```

---

## API Research Summary

### Plex API

| Capability | Endpoint/Method |
|------------|-----------------|
| Authentication | Token-based (`X-Plex-Token` header) |
| Get libraries | `GET /library/sections` |
| Get all items | `GET /library/sections/{id}/all` |
| Get item metadata | `GET /library/metadata/{ratingKey}` |
| Check match status | GUID attribute (`local://` = unmatched) |
| Check artwork | `thumb`, `art` attributes |
| Upload artwork | `POST /library/metadata/{id}/posters?url=` |
| Lock artwork | `PUT /library/sections/{id}/all?thumb.locked=1` |
| Set edition | `PUT /library/metadata/{id}?editionTitle=` |
| Get matches | `GET /library/metadata/{id}/matches` |
| Fix match | `PUT /library/metadata/{id}/match?guid=` |

### Mediux API (GraphQL)

```
Base URL: https://staged.mediux.io
GraphQL: POST /graphql
Assets: GET /assets/{fileId}
Auth: API Key (user-provided)
```

**Sample Query:**
```graphql
query {
  shows_by_id(id: "tmdb-12345") {
    title
    show_sets {
      id, set_title, user_created { username }
      showPoster: files(filter: { file_type: { _eq: "poster" } }) { id }
      backgrounds: files(filter: { file_type: { _eq: "background" } }) { id }
    }
  }
}
```

### Other Providers

| Provider | Auth | Key Features |
|----------|------|--------------|
| **Fanart.tv** | API Key | HD logos, clearart, backgrounds, posters |
| **TMDB** | API Key/Bearer | Movies + TV, posters/backdrops/logos |
| **TVDB** | JWT (1 month) | TV shows, all artwork types |
| **Trakt** | OAuth 2.0 | ID resolution (IMDB/TMDB/TVDB cross-reference) |

### Provider Priority (Default)

```
1. Fanart.tv   (best for HD logos/clearart)
2. Mediux      (community curated sets)
3. TMDB        (comprehensive movie data)
4. TVDB        (TV show focus)
5. Plex        (built-in suggestions)
```

User can reorder via drag-and-drop in settings.

---

## Database Schema

```sql
-- ============================================================================
-- CONFIGURATION
-- ============================================================================

CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT FALSE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SCAN MANAGEMENT
-- ============================================================================

CREATE TABLE scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Type: 'artwork', 'edition', 'both'
    scan_type TEXT NOT NULL DEFAULT 'artwork',
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK(status IN ('pending', 'running', 'paused', 'completed', 'cancelled', 'failed')),
    
    -- Timing
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    paused_at DATETIME,
    completed_at DATETIME,
    
    -- Configuration (JSON)
    config TEXT NOT NULL,
    
    -- Progress
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    issues_found INTEGER DEFAULT 0,
    editions_updated INTEGER DEFAULT 0,
    current_library TEXT,
    current_item TEXT,
    
    -- Checkpoint for resume (JSON)
    checkpoint TEXT,
    
    -- Trigger source
    triggered_by TEXT DEFAULT 'manual'
);

CREATE TABLE scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

-- ============================================================================
-- ARTWORK ISSUES
-- ============================================================================

CREATE TABLE issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    plex_rating_key TEXT NOT NULL,
    plex_guid TEXT,
    title TEXT NOT NULL,
    year INTEGER,
    media_type TEXT NOT NULL CHECK(media_type IN ('movie', 'show', 'season', 'episode')),
    issue_type TEXT NOT NULL CHECK(issue_type IN (
        'no_match', 'no_poster', 'no_background', 'no_logo', 
        'placeholder_poster', 'placeholder_background'
    )),
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK(status IN ('pending', 'accepted', 'rejected', 'applied', 'failed')),
    library_name TEXT,
    external_ids TEXT,  -- JSON
    details TEXT,       -- JSON (e.g., detected aspect ratio)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('fanart', 'mediux', 'tmdb', 'tvdb', 'plex')),
    artwork_type TEXT NOT NULL CHECK(artwork_type IN ('poster', 'background', 'logo')),
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    language TEXT,
    score INTEGER DEFAULT 0,
    set_name TEXT,
    creator_name TEXT,
    is_selected BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
);

-- ============================================================================
-- ARTWORK CACHE
-- ============================================================================

CREATE TABLE artwork_cache (
    external_id TEXT NOT NULL,
    artwork_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    data TEXT NOT NULL,  -- JSON
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    PRIMARY KEY (external_id, artwork_type, provider)
);

-- ============================================================================
-- EDITION MANAGER
-- ============================================================================

CREATE TABLE edition_backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plex_rating_key TEXT NOT NULL,
    title TEXT NOT NULL,
    original_edition TEXT,
    new_edition TEXT,
    backed_up_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    restored_at DATETIME
);

CREATE TABLE edition_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    enabled_modules TEXT NOT NULL,  -- JSON array of enabled module names
    module_order TEXT NOT NULL,     -- JSON array defining order
    settings TEXT NOT NULL,         -- JSON object with module-specific settings
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SCHEDULING
-- ============================================================================

CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    cron_expression TEXT NOT NULL,
    
    -- What to run
    scan_type TEXT NOT NULL DEFAULT 'both' CHECK(scan_type IN ('artwork', 'edition', 'both')),
    config TEXT NOT NULL,  -- JSON scan configuration
    
    -- Auto-commit settings
    auto_commit BOOLEAN DEFAULT FALSE,
    auto_commit_options TEXT,  -- JSON
    
    -- Tracking
    last_run_at DATETIME,
    next_run_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_scans_status ON scans(status);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_scan ON issues(scan_id);
CREATE INDEX idx_suggestions_issue ON suggestions(issue_id);
CREATE INDEX idx_schedules_enabled ON schedules(enabled);
CREATE INDEX idx_edition_backups_key ON edition_backups(plex_rating_key);
```

---

## Module 1: Artwork Scanner

### Issue Types

| Issue Type | Description | Detection Method |
|------------|-------------|------------------|
| `no_match` | Item has no metadata match | GUID is `local://` or missing |
| `no_poster` | Completely missing poster | `thumb` attribute is empty |
| `no_background` | Completely missing background | `art` attribute is empty |
| `no_logo` | Missing clear logo | No logo in extended metadata |
| `placeholder_poster` | Video screenshot as poster | Aspect ratio > 1.0 (landscape) |
| `placeholder_background` | Wrong/tiny background | Suspicious dimensions |

### Placeholder Detection Logic

```python
class ArtworkScanner:
    POSTER_ASPECT_RATIO = 0.667  # 2:3 portrait
    ASPECT_RATIO_TOLERANCE = 0.15
    
    async def check_placeholder_poster(self, item) -> bool:
        """Detect if poster is a video screenshot."""
        if not item.thumb:
            return False
        
        ratio = await self._get_image_aspect_ratio(item.thumb)
        if ratio is None:
            return False
        
        # Landscape ratio (> 1.0) = video screenshot, not poster
        if ratio > 1.0:
            return True
        
        # Check if close to standard poster ratio
        min_valid = self.POSTER_ASPECT_RATIO * (1 - self.ASPECT_RATIO_TOLERANCE)
        max_valid = self.POSTER_ASPECT_RATIO * (1 + self.ASPECT_RATIO_TOLERANCE)
        
        return not (min_valid <= ratio <= max_valid)
```

### Artwork Service (Multi-Source Aggregation)

```python
class ArtworkService:
    DEFAULT_PRIORITY = ["fanart", "mediux", "tmdb", "tvdb", "plex"]
    
    async def get_suggestions(
        self,
        media_type: str,
        external_ids: dict,
        artwork_type: str
    ) -> list[ArtworkSuggestion]:
        """Fetch artwork from all providers in priority order."""
        priority = self.config.get("provider_priority", self.DEFAULT_PRIORITY)
        all_suggestions = []
        
        for rank, provider_name in enumerate(priority):
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_configured():
                continue
            
            try:
                artwork = await provider.get_artwork(
                    media_type=media_type,
                    external_ids=external_ids,
                    artwork_type=artwork_type
                )
                for item in artwork:
                    item.source = provider_name
                    item.priority_rank = rank
                all_suggestions.extend(artwork)
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
        
        return sorted(all_suggestions, key=lambda x: (x.priority_rank, -x.score))
```

---

## Module 2: Edition Manager

### Supported Modules (22 Total)

| Module | Description | Example Output |
|--------|-------------|----------------|
| `AudioChannels` | Audio channel layout | `5.1`, `7.1` |
| `AudioCodec` | Audio codec name | `Dolby TrueHD`, `DTS-HD MA` |
| `Bitrate` | Video bitrate | `24.5 Mbps` |
| `ContentRating` | Age rating | `PG-13`, `R` |
| `Country` | Production country | `United States` |
| `Cut` | Special cut version | `Director's Cut`, `Extended` |
| `Director` | Film director | `Christopher Nolan` |
| `Duration` | Runtime | `2h 14m` |
| `DynamicRange` | HDR format | `Dolby Vision`, `HDR10+` |
| `FrameRate` | Frame rate | `24fps`, `60fps` |
| `Genre` | Primary genre | `Drama`, `Sci-Fi` |
| `Language` | Audio language | `Japanese`, `French` |
| `Rating` | IMDb/RT rating | `8.4`, `92%` |
| `Release` | Special release | `Criterion`, `Anniversary Edition` |
| `Resolution` | Video resolution | `4K`, `1080p` |
| `ShortFilm` | Short film marker | `Short Film` |
| `Size` | File size | `58.2 GB` |
| `Source` | Media source | `REMUX`, `WEB-DL`, `BluRay` |
| `SpecialFeatures` | Bonus content | `Behind The Scenes` |
| `Studio` | Production studio | `Warner Bros.`, `A24` |
| `VideoCodec` | Video codec | `H.265`, `AV1` |
| `Writer` | Screenwriter | `Quentin Tarantino` |

### Edition Configuration Schema

```python
class EditionConfig:
    enabled_modules: list[str]  # Which modules are active
    module_order: list[str]     # Display order
    settings: EditionSettings   # Module-specific settings

class EditionSettings:
    # Language module
    excluded_languages: list[str] = ["English"]
    skip_multiple_audio_tracks: bool = True
    
    # Rating module
    rating_source: str = "imdb"  # "imdb" or "rotten_tomatoes"
    rotten_tomatoes_type: str = "audience"  # "critic" or "audience"
    tmdb_api_key: str = ""  # Required for IMDb lookups
    
    # Performance
    max_workers: int = 8
    batch_size: int = 20
    
    # Separator between modules
    separator: str = " · "
```

### Edition Manager Service

```python
class EditionManagerService:
    """Generates and applies Edition metadata to Plex movies."""
    
    MODULES = {
        "AudioChannels": AudioChannelsModule,
        "AudioCodec": AudioCodecModule,
        "Bitrate": BitrateModule,
        "ContentRating": ContentRatingModule,
        "Country": CountryModule,
        "Cut": CutModule,
        "Director": DirectorModule,
        "Duration": DurationModule,
        "DynamicRange": DynamicRangeModule,
        "FrameRate": FrameRateModule,
        "Genre": GenreModule,
        "Language": LanguageModule,
        "Rating": RatingModule,
        "Release": ReleaseModule,
        "Resolution": ResolutionModule,
        "ShortFilm": ShortFilmModule,
        "Size": SizeModule,
        "Source": SourceModule,
        "SpecialFeatures": SpecialFeaturesModule,
        "Studio": StudioModule,
        "VideoCodec": VideoCodecModule,
        "Writer": WriterModule,
    }
    
    async def generate_edition(self, movie: PlexMovie) -> str:
        """Generate edition string from enabled modules."""
        config = await self.get_config()
        parts = []
        
        for module_name in config.module_order:
            if module_name not in config.enabled_modules:
                continue
            
            module_class = self.MODULES.get(module_name)
            if not module_class:
                continue
            
            module = module_class(config.settings)
            value = await module.extract(movie)
            
            if value:
                parts.append(value)
        
        return config.settings.separator.join(parts)
    
    async def apply_edition(self, movie: PlexMovie, edition: str, backup: bool = True):
        """Apply edition to a movie, optionally backing up original."""
        if backup:
            await self.backup_edition(movie)
        
        await self.plex.set_edition(movie.ratingKey, edition)
    
    async def process_library(self, library_id: str, emit_progress: Callable):
        """Process all movies in a library."""
        movies = await self.plex.get_all_movies(library_id)
        
        for i, movie in enumerate(movies):
            edition = await self.generate_edition(movie)
            
            if edition:
                await self.apply_edition(movie, edition)
            
            await emit_progress({
                "processed": i + 1,
                "total": len(movies),
                "current_item": movie.title
            })
```

### Module Implementation Examples

```python
class ResolutionModule:
    """Extracts video resolution."""
    
    RESOLUTION_MAP = {
        (7680, 4320): "8K",
        (3840, 2160): "4K",
        (2560, 1440): "2K",
        (1920, 1080): "1080p",
        (1280, 720): "720p",
        (720, 576): "576p",
        (720, 480): "480p",
    }
    
    async def extract(self, movie: PlexMovie) -> str | None:
        media = self._get_largest_media(movie)
        if not media or not media.videoResolution:
            return None
        
        width = media.width
        height = media.height
        
        # Find closest match
        for (w, h), label in self.RESOLUTION_MAP.items():
            if width >= w * 0.9 and height >= h * 0.9:
                return label
        
        return "SD"


class DynamicRangeModule:
    """Extracts HDR/Dolby Vision information."""
    
    async def extract(self, movie: PlexMovie) -> str | None:
        media = self._get_largest_media(movie)
        if not media:
            return None
        
        parts = []
        
        # Check for Dolby Vision
        if "dovi" in (media.DOVIPresent or "").lower():
            profile = media.DOVIProfile
            if profile:
                parts.append(f"DV P{profile}")
            else:
                parts.append("Dolby Vision")
        
        # Check for HDR
        if media.videoHDRType:
            hdr_type = media.videoHDRType.upper()
            if "HDR10+" in hdr_type:
                parts.append("HDR10+")
            elif "HDR" in hdr_type:
                parts.append("HDR")
        
        return " · ".join(parts) if parts else None


class CutModule:
    """Detects special cut versions from filename or title."""
    
    CUT_PATTERNS = {
        r"theatrical[.\s_-]*cut": "Theatrical Cut",
        r"director'?s?[.\s_-]*cut": "Director's Cut",
        r"producer'?s?[.\s_-]*cut": "Producer's Cut",
        r"extended[.\s_-]*(cut|edition)?": "Extended",
        r"unrated[.\s_-]*(cut|edition)?": "Unrated",
        r"final[.\s_-]*cut": "Final Cut",
        r"television[.\s_-]*cut": "Television Cut",
        r"international[.\s_-]*cut": "International Cut",
        r"redux": "Redux",
    }
    
    async def extract(self, movie: PlexMovie) -> str | None:
        # Check filename first
        filename = self._get_largest_file_name(movie)
        for pattern, label in self.CUT_PATTERNS.items():
            if re.search(pattern, filename, re.IGNORECASE):
                return label
        
        # Check embedded title
        title = self._get_embedded_title(movie)
        if title:
            for pattern, label in self.CUT_PATTERNS.items():
                if re.search(pattern, title, re.IGNORECASE):
                    return label
        
        return None


class SourceModule:
    """Detects media source from filename."""
    
    SOURCE_PATTERNS = {
        r"\bremux\b": "REMUX",
        r"\bblu-?ray\b|\bbd\b": "BluRay",
        r"\bbdrip\b": "BDRip",
        r"\bweb-?dl\b": "WEB-DL",
        r"\bwebrip\b": "WEBRip",
        r"\bhdtv\b": "HDTV",
        r"\bdvd\b": "DVD",
        r"\bdvdrip\b": "DVDRip",
        # ... more patterns
    }
```

---

## Scan Management System

### Scan State Machine

```
                    ┌─────────────┐
                    │    IDLE     │◄────────────────────────┐
                    └──────┬──────┘                         │
                           │ start()                        │
                           ▼                                │
                    ┌─────────────┐                         │
            ┌──────►│   RUNNING   │────────┐                │
            │       └──────┬──────┘        │                │
            │              │               │                │
            │   resume()   │ pause()       │ cancel()       │ complete()
            │              ▼               │                │
            │       ┌─────────────┐        │                │
            └───────│   PAUSED    │        │                │
                    └──────┬──────┘        │                │
                           │               │                │
                           │ cancel()      │                │
                           ▼               ▼                │
                    ┌─────────────┐ ┌─────────────┐        │
                    │  CANCELLED  │ │  COMPLETED  │────────┘
                    └─────────────┘ └─────────────┘
```

### Scan Manager (Singleton)

```python
class ScanManager:
    """Singleton manager ensuring only one scan runs at a time."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def start_scan(self, config: ScanConfig) -> int:
        """Start a new scan. Raises if scan already running."""
        if self._status in [ScanStatus.RUNNING, ScanStatus.PAUSED]:
            raise ScanAlreadyRunningError(
                f"Scan {self._current_scan_id} is already in progress"
            )
        
        # Create scan record
        scan_id = await self.db.create_scan(config)
        self._current_scan_id = scan_id
        
        # Start background task
        self._scan_task = asyncio.create_task(
            self._run_scan(scan_id, config)
        )
        
        return scan_id
    
    async def pause_scan(self) -> bool:
        """Pause the current scan."""
        if self._status != ScanStatus.RUNNING:
            return False
        
        self._pause_event.clear()
        self._status = ScanStatus.PAUSED
        await self._broadcast({"type": "scan_paused"})
        return True
    
    async def resume_scan(self) -> bool:
        """Resume a paused scan."""
        if self._status != ScanStatus.PAUSED:
            return False
        
        self._pause_event.set()
        self._status = ScanStatus.RUNNING
        await self._broadcast({"type": "scan_resumed"})
        return True
    
    async def cancel_scan(self) -> bool:
        """Cancel the current scan."""
        if self._status not in [ScanStatus.RUNNING, ScanStatus.PAUSED]:
            return False
        
        self._cancel_requested = True
        self._pause_event.set()  # Unblock if paused
        
        if self._scan_task:
            self._scan_task.cancel()
        
        self._status = ScanStatus.IDLE
        await self._broadcast({"type": "scan_cancelled"})
        return True
```

### Combined Scan Execution

```python
async def _run_scan(self, scan_id: int, config: ScanConfig):
    """Execute artwork and/or edition scan based on config."""
    
    # Determine what to run
    run_artwork = config.scan_type in ["artwork", "both"]
    run_edition = config.scan_type in ["edition", "both"]
    
    items = await self.plex.get_all_items(config.libraries)
    total = len(items)
    
    for i, item in enumerate(items):
        # Check pause/cancel
        if self._cancel_requested:
            return
        await self._pause_event.wait()
        
        # Artwork scan
        if run_artwork:
            issues = await self.artwork_scanner.scan_item(item)
            for issue in issues:
                await self.db.create_issue(scan_id, issue)
        
        # Edition scan (movies only)
        if run_edition and item.type == "movie":
            edition = await self.edition_manager.generate_edition(item)
            if edition:
                await self.edition_manager.apply_edition(item, edition)
                await self.db.increment_editions_updated(scan_id)
        
        # Checkpoint every 100 items
        if (i + 1) % 100 == 0:
            await self.db.save_checkpoint(scan_id, {"item_index": i + 1})
        
        # Broadcast progress
        await self._broadcast({
            "type": "scan_progress",
            "processed": i + 1,
            "total": total,
            "current_item": item.title
        })
```

---

## Scheduling & Automation

### Schedule Configuration

```python
class ScheduleConfig:
    name: str
    enabled: bool = True
    cron_expression: str  # e.g., "0 3 * * *" (3am daily)
    
    # What to run
    scan_type: str = "both"  # "artwork", "edition", "both"
    libraries: list[str]
    
    # Artwork scan options
    check_posters: bool = True
    check_backgrounds: bool = True
    check_logos: bool = True
    check_unmatched: bool = True
    check_placeholders: bool = True
    
    # Edition scan options
    edition_enabled: bool = True
    
    # Auto-commit options
    auto_commit: bool = False
    auto_commit_skip_unmatched: bool = True
    auto_commit_min_score: int = 0
```

### Scheduler Service

```python
class ScanScheduler:
    """Manages scheduled scan jobs."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scan_manager = ScanManager()
    
    async def create_schedule(self, config: ScheduleConfig) -> int:
        """Create a new scheduled scan."""
        # Validate cron
        trigger = CronTrigger.from_crontab(config.cron_expression)
        
        # Save to database
        schedule_id = await self.db.create_schedule(config)
        
        # Register with APScheduler
        self.scheduler.add_job(
            self._execute_scheduled_scan,
            trigger,
            id=f"scan_{schedule_id}",
            args=[schedule_id]
        )
        
        return schedule_id
    
    async def _execute_scheduled_scan(self, schedule_id: int):
        """Execute a scheduled scan."""
        schedule = await self.db.get_schedule(schedule_id)
        
        try:
            scan_id = await self.scan_manager.start_scan(
                ScanConfig(**schedule.config),
                triggered_by="schedule"
            )
            
            if schedule.auto_commit:
                await self._wait_for_completion(scan_id)
                await self._auto_commit(scan_id, schedule.auto_commit_options)
                
        except ScanAlreadyRunningError:
            logger.warning(f"Scheduled scan skipped - another scan running")
```

---

## User Interface Design

### Dashboard / Results Page

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MetaFix                                                    [Settings]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SCAN STATUS                                         [New Scan]     │   │
│  │  Last scan: Completed 2 hours ago - Found 247 issues               │   │
│  │  Next scheduled: Tomorrow at 3:00 AM                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Filters: [All Types] [All Libraries] [Pending]         Search...         │
│                                                                             │
│  247 issues found                              [Auto-Fix All] [Rescan]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  [?]     The Matrix (1999)                       Issue: Missing Poster│ │
│  │  poster  Library: Movies                                              │ │
│  │                                                                       │ │
│  │  [img1] [img2] [img3] [img4]                                         │ │
│  │  Fanart Mediux  TMDB   TMDB                                          │ │
│  │                                                                       │ │
│  │                                     [Accept] [Skip] [Browse All]     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  PLACEHOLDER                             Issue: Placeholder Poster   │ │
│  │  [16:9 img]  Inception (2010)                                        │ │
│  │              Detected: 16:9 screenshot instead of 2:3 poster         │ │
│  │                                                                       │ │
│  │                                  [Replace] [Keep Current] [Browse]   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### New Scan Dialog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Start New Scan                                                      [X]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SCAN TYPE                                                                  │
│  ( ) Artwork Scan Only                                                     │
│  ( ) Edition Scan Only                                                     │
│  (*) Both Artwork + Edition                                                │
│                                                                             │
│  LIBRARIES                                                                  │
│  [x] Movies (51,234 items)                                                 │
│  [x] TV Shows (15,678 items)                                               │
│  [ ] Kids Movies (1,234 items)                                             │
│                                                                             │
│  ARTWORK OPTIONS                                                            │
│  [x] Missing posters    [x] Missing backgrounds    [x] Missing logos      │
│  [x] Unmatched items    [x] Placeholder artwork (wrong aspect ratio)      │
│                                                                             │
│  EDITION OPTIONS                                                            │
│  [x] Generate editions for all movies                                      │
│  [x] Backup existing editions before updating                              │
│                                                                             │
│                                              [Cancel]  [Start Scan]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Edition Manager Settings

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Edition Manager Settings                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MODULE ORDER (drag to reorder)                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ = [x] Resolution       Example: 4K                                  │   │
│  │ = [x] DynamicRange     Example: Dolby Vision                        │   │
│  │ = [x] VideoCodec       Example: H.265                               │   │
│  │ = [x] AudioCodec       Example: Dolby TrueHD Atmos                  │   │
│  │ = [x] AudioChannels    Example: 7.1                                 │   │
│  │ = [ ] Bitrate          Example: 24.5 Mbps                           │   │
│  │ = [ ] Size             Example: 58.2 GB                             │   │
│  │ = [x] Cut              Example: Director's Cut                      │   │
│  │ = [x] Release          Example: Criterion                           │   │
│  │ = [ ] Source           Example: REMUX                               │   │
│  │ = [ ] ContentRating    Example: PG-13                               │   │
│  │ = [ ] Duration         Example: 2h 14m                              │   │
│  │ = [ ] Rating           Example: 8.4                                 │   │
│  │ = [ ] Director         Example: Christopher Nolan                   │   │
│  │ = [ ] Genre            Example: Drama                               │   │
│  │ = [ ] Country          Example: United States                       │   │
│  │ = [ ] Studio           Example: Warner Bros.                        │   │
│  │ = [ ] Language         Example: Japanese                            │   │
│  │ = [ ] SpecialFeatures  Example: Behind The Scenes                   │   │
│  │ = [ ] Writer           Example: Quentin Tarantino                   │   │
│  │ = [ ] ShortFilm        Example: Short Film                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  SEPARATOR                                                                  │
│  [ . ]  Preview: "4K . Dolby Vision . H.265 . Dolby TrueHD Atmos"         │
│                                                                             │
│  LANGUAGE MODULE OPTIONS                                                    │
│  Excluded languages: [English, Spanish          ]                          │
│  [x] Skip when multiple audio tracks present                              │
│                                                                             │
│  RATING MODULE OPTIONS                                                      │
│  Source: [IMDb]             TMDB API Key: [************    ] [Test]       │
│                                                                             │
│  PERFORMANCE                                                                │
│  Max workers: [8]           Batch size: [20]                               │
│                                                                             │
│                                              [Reset Defaults] [Save]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Schedule Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Scheduled Scans                                          [+ New Schedule] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ [x] ENABLED     Daily Full Scan                                      │ │
│  │                 Cron: 0 3 * * * (Every day at 3:00 AM)               │ │
│  │                 Type: Artwork + Edition                               │ │
│  │                 Libraries: Movies, TV Shows                           │ │
│  │                 Next run: Tomorrow at 3:00 AM                        │ │
│  │                                                                       │ │
│  │                 Auto-commit: Enabled (skip unmatched)                │ │
│  │                                                                       │ │
│  │                 [Edit] [Run Now] [Disable] [Delete]                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ [ ] DISABLED    Weekly Deep Scan                                     │ │
│  │                 Cron: 0 2 * * 0 (Sundays at 2:00 AM)                 │ │
│  │                 Type: Artwork only                                    │ │
│  │                 Includes: Placeholder detection                      │ │
│  │                                                                       │ │
│  │                 [Edit] [Run Now] [Enable] [Delete]                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
metafix/
├── docker-compose.yml
├── Dockerfile
├── start.sh
├── README.md
│
├── docs/
│   └── plan.md                        # This document
│
├── frontend/                          # Next.js 14 + shadcn/UI
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Dashboard / Results
│   │   ├── globals.css
│   │   ├── onboarding/
│   │   │   └── page.tsx
│   │   ├── scan/
│   │   │   └── page.tsx              # Scan progress
│   │   ├── edition/
│   │   │   └── page.tsx              # Edition manager settings
│   │   ├── schedules/
│   │   │   └── page.tsx              # Schedule management
│   │   └── settings/
│   │       └── page.tsx              # General settings
│   ├── components/
│   │   ├── ui/                       # shadcn components
│   │   ├── issue-card.tsx
│   │   ├── artwork-picker.tsx
│   │   ├── scan-progress.tsx
│   │   ├── scan-controls.tsx
│   │   ├── edition-module-list.tsx
│   │   ├── schedule-card.tsx
│   │   ├── schedule-dialog.tsx
│   │   └── onboarding/
│   │       ├── plex-step.tsx
│   │       ├── providers-step.tsx
│   │       └── libraries-step.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── scan-client.ts            # SSE client
│   │   └── utils.ts
│   ├── package.json
│   └── next.config.js
│
├── backend/                           # Python FastAPI
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── plex.py
│   │   ├── scan.py
│   │   ├── issues.py
│   │   ├── artwork.py
│   │   ├── edition.py
│   │   ├── autofix.py
│   │   ├── schedules.py
│   │   └── settings.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── plex_service.py
│   │   ├── scan_manager.py
│   │   ├── artwork_scanner.py
│   │   ├── artwork_service.py
│   │   ├── edition_manager.py
│   │   ├── autofix_service.py
│   │   └── scheduler.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── fanart.py
│   │   ├── mediux.py
│   │   ├── tmdb.py
│   │   ├── tvdb.py
│   │   └── plex_provider.py
│   │
│   ├── edition_modules/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── audio_channels.py
│   │   ├── audio_codec.py
│   │   ├── bitrate.py
│   │   ├── content_rating.py
│   │   ├── country.py
│   │   ├── cut.py
│   │   ├── director.py
│   │   ├── duration.py
│   │   ├── dynamic_range.py
│   │   ├── frame_rate.py
│   │   ├── genre.py
│   │   ├── language.py
│   │   ├── rating.py
│   │   ├── release.py
│   │   ├── resolution.py
│   │   ├── short_film.py
│   │   ├── size.py
│   │   ├── source.py
│   │   ├── special_features.py
│   │   ├── studio.py
│   │   ├── video_codec.py
│   │   └── writer.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   └── database.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_artwork_scanner.py
│   │   ├── test_edition_modules.py
│   │   ├── test_scan_manager.py
│   │   ├── test_providers.py
│   │   └── integration/
│   │       ├── test_scan_api.py
│   │       └── test_edition_api.py
│   │
│   └── requirements.txt
│
└── data/                              # Docker volume
    └── metafix.db
```

---

## Implementation Plan

> **CRITICAL: Each phase MUST pass all tests before proceeding to the next phase.**
> **No code should be merged that doesn't have corresponding tests passing.**

### Phase 0: Project Setup (Day 1)

**Objective:** Create a working skeleton that builds and runs.

**Tasks:**
1. Initialize Git repository with `.gitignore`
2. Create project directory structure
3. Set up Docker configuration:
   - `Dockerfile` (multi-stage build)
   - `docker-compose.yml`
   - `start.sh` entrypoint script
4. Initialize Next.js frontend:
   - `npx create-next-app@latest frontend`
   - Install and configure shadcn/UI
   - Configure Tailwind CSS
5. Initialize FastAPI backend:
   - Create `requirements.txt`
   - Create basic `main.py` with health check
   - Set up SQLAlchemy with SQLite
6. Create database schema and migrations
7. Set up development environment with hot reload

**Verification Checklist:**
- [ ] `docker-compose up --build` succeeds without errors
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend health check returns 200 at http://localhost:8000/api/health
- [ ] Database file created with all tables
- [ ] Hot reload works for both frontend and backend

**Tests Required:**
```python
def test_health_endpoint():
    """Backend health check returns 200."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_database_connection():
    """Database is accessible and tables exist."""
    # Verify all tables created
```

---

### Phase 1: Plex Integration (Days 2-3)

**Objective:** Connect to Plex and list libraries.

**Tasks:**
1. Create `PlexService` class:
   - `connect(url, token)` - test connection
   - `get_libraries()` - list all libraries
   - `get_library_items(library_id)` - get all items (paginated)
   - `get_item_metadata(rating_key)` - get detailed metadata
2. Create Plex router (`/api/plex/*`):
   - `POST /api/plex/connect` - test and save connection
   - `GET /api/plex/libraries` - list libraries
   - `GET /api/plex/status` - connection status
3. Build onboarding wizard UI:
   - Plex connection step with URL/token inputs
   - Connection test with feedback
   - Library display after successful connection
4. Store encrypted Plex token in database
5. Handle connection errors gracefully

**Verification Checklist:**
- [ ] Can connect to Plex server with valid URL + token
- [ ] Invalid credentials show appropriate error message
- [ ] Libraries listed with correct item counts
- [ ] Token stored encrypted in database
- [ ] Connection persists across restarts

**Tests Required:**
```python
def test_plex_connect_valid_credentials():
    """Valid Plex credentials establish connection."""
    
def test_plex_connect_invalid_token():
    """Invalid token returns 401 with clear message."""
    
def test_plex_connect_unreachable_server():
    """Unreachable server returns appropriate error."""
    
def test_plex_get_libraries():
    """Libraries returned with correct structure."""
    
def test_plex_token_encrypted():
    """Token stored encrypted, not plaintext."""
```

---

### Phase 2: Artwork Scanner Core (Days 4-5)

**Objective:** Scan library and detect artwork issues.

**Tasks:**
1. Create `ArtworkScanner` service:
   - `scan_item(item)` - detect all issues for one item
   - `_is_unmatched(item)` - check for local:// GUID
   - `_has_poster(item)` - check thumb attribute
   - `_has_background(item)` - check art attribute
   - `_check_placeholder(item)` - verify aspect ratio
2. Create `_get_image_aspect_ratio(thumb_path)` helper:
   - Fetch small thumbnail from Plex
   - Calculate width/height ratio
   - Cache results to avoid repeated fetches
3. Create scan router (`/api/scan/*`):
   - `POST /api/scan/start` - begin new scan
   - `GET /api/scan/status` - current scan status
   - `GET /api/scan/subscribe` - SSE endpoint for progress
4. Implement SSE progress streaming
5. Create issues database operations
6. Implement checkpoint saving every 100 items

**Verification Checklist:**
- [ ] Missing posters detected correctly
- [ ] Missing backgrounds detected correctly
- [ ] Unmatched items (local://) detected
- [ ] Placeholder posters (landscape images) detected
- [ ] Progress updates sent via SSE
- [ ] Checkpoints saved to database
- [ ] Scan can be interrupted and resumed

**Tests Required:**
```python
def test_detect_missing_poster():
    """Items without thumb attribute flagged."""
    
def test_detect_missing_background():
    """Items without art attribute flagged."""
    
def test_detect_unmatched_local_guid():
    """Items with local:// GUID flagged as unmatched."""
    
def test_detect_placeholder_landscape():
    """Landscape images (ratio > 1.0) flagged as placeholder."""
    
def test_detect_valid_poster_not_flagged():
    """Valid portrait posters not flagged."""
    
def test_checkpoint_save():
    """Checkpoint saved every 100 items."""
    
def test_checkpoint_restore():
    """Scan resumes from checkpoint correctly."""
```

---

### Phase 3: Scan Manager (Days 6-7)

**Objective:** Robust scan lifecycle management.

**Tasks:**
1. Implement `ScanManager` singleton:
   - Enforce single scan at a time
   - Track current scan state
   - Manage pause/resume/cancel
2. Add pause/resume functionality:
   - `pause_scan()` - block scan loop
   - `resume_scan()` - unblock scan loop
   - Persist paused state to database
3. Add cancel functionality:
   - `cancel_scan()` - stop and cleanup
   - Mark scan as cancelled in database
4. Implement multi-client broadcasting:
   - Subscribe/unsubscribe pattern
   - Broadcast state changes to all clients
5. Create scan control UI:
   - Progress bar with percentage
   - Pause/Resume button
   - Cancel button
   - Current item display
6. Handle server restart:
   - Detect interrupted scans on startup
   - Allow user to resume or discard

**Verification Checklist:**
- [ ] Second scan request returns 409 Conflict
- [ ] Pause stops processing, resumes correctly
- [ ] Cancel stops scan and marks as cancelled
- [ ] Multiple browser tabs see same scan state
- [ ] Closing browser doesn't stop scan
- [ ] Server restart detects interrupted scan
- [ ] Interrupted scan can be resumed

**Tests Required:**
```python
async def test_singleton_prevents_concurrent_scans():
    """Starting second scan raises ScanAlreadyRunningError."""
    
async def test_pause_blocks_processing():
    """Pause stops item processing."""
    
async def test_resume_continues_processing():
    """Resume continues from paused state."""
    
async def test_cancel_stops_scan():
    """Cancel terminates scan and updates status."""
    
async def test_multi_client_broadcast():
    """All subscribed clients receive updates."""
    
async def test_interrupted_scan_detected():
    """Scan running at shutdown detected on restart."""
```

---

### Phase 4: Metadata Providers (Days 8-10)

**Objective:** Fetch artwork from multiple sources.

**Tasks:**
1. Create base provider interface:
   ```python
   class BaseProvider:
       def is_configured(self) -> bool
       async def get_artwork(media_type, external_ids, artwork_type) -> list
   ```
2. Implement Fanart.tv provider:
   - API key authentication
   - Movie artwork endpoint
   - TV show artwork endpoint
   - HD logo extraction
3. Implement Mediux GraphQL provider:
   - GraphQL query construction
   - Show/movie sets retrieval
   - Asset URL generation
4. Implement TMDB provider:
   - Bearer token authentication
   - Image URL construction with sizes
   - Poster/backdrop/logo retrieval
5. Implement TVDB provider:
   - JWT authentication with refresh
   - Artwork type filtering
6. Implement Plex built-in provider:
   - Get available posters from Plex
   - Get available art from Plex
7. Create `ArtworkService` aggregator:
   - Priority-based provider ordering
   - Parallel fetching with error handling
   - Result caching
8. Build provider configuration UI:
   - API key inputs for each provider
   - Connection test buttons
   - Drag-and-drop priority ordering

**Verification Checklist:**
- [ ] Fanart.tv returns HD logos and posters
- [ ] Mediux returns artwork sets with creator attribution
- [ ] TMDB returns posters, backdrops, logos
- [ ] TVDB returns TV show artwork
- [ ] Plex returns built-in suggestions
- [ ] Results sorted by priority order
- [ ] Rate limits handled gracefully
- [ ] API keys validated on save

**Tests Required (per provider):**
```python
def test_fanart_movie_artwork():
    """Fanart.tv returns movie posters and logos."""
    
def test_fanart_tv_artwork():
    """Fanart.tv returns TV show artwork."""
    
def test_mediux_graphql_query():
    """Mediux GraphQL query returns sets."""
    
def test_mediux_asset_url():
    """Mediux asset URL correctly constructed."""
    
def test_tmdb_poster_url():
    """TMDB poster URL includes correct size."""
    
def test_tvdb_jwt_refresh():
    """TVDB JWT refreshes when expired."""
    
def test_provider_priority_order():
    """Results sorted by configured priority."""
    
def test_provider_error_isolation():
    """One provider failing doesn't break others."""
```

---

### Phase 5: Edition Manager (Days 11-13)

**Objective:** Generate and apply Edition metadata.

**Tasks:**
1. Create base edition module interface:
   ```python
   class BaseEditionModule:
       async def extract(self, movie: PlexMovie) -> str | None
   ```
2. Implement all 22 edition modules:
   - Resolution, DynamicRange, VideoCodec
   - AudioCodec, AudioChannels, Bitrate
   - Cut, Release, Source
   - ContentRating, Duration, Rating
   - Director, Writer, Genre
   - Country, Studio, Language
   - Size, SpecialFeatures, ShortFilm
3. Create `EditionManagerService`:
   - `generate_edition(movie)` - build edition string
   - `apply_edition(movie, edition)` - update Plex
   - `backup_edition(movie)` - save original
   - `restore_edition(movie)` - revert to backup
4. Build edition configuration storage:
   - Enabled modules list
   - Module order
   - Module-specific settings
5. Create edition settings UI:
   - Drag-and-drop module ordering
   - Enable/disable toggles
   - Separator configuration
   - Language/Rating module settings
6. Integrate edition scan into scan workflow:
   - Add `scan_type` selection
   - Process editions when enabled

**Verification Checklist:**
- [ ] Each module extracts correct data
- [ ] Module order reflected in output
- [ ] Separator correctly applied
- [ ] Edition applied to Plex successfully
- [ ] Backup created before modification
- [ ] Restore reverts to original
- [ ] Scan type selection works

**Tests Required:**
```python
# Test each module individually
def test_resolution_module_4k():
    """Resolution module returns '4K' for 3840x2160."""
    
def test_resolution_module_1080p():
    """Resolution module returns '1080p' for 1920x1080."""
    
def test_dynamic_range_dolby_vision():
    """DynamicRange returns 'Dolby Vision' when present."""
    
def test_cut_module_directors_cut():
    """Cut module detects 'Director's Cut' from filename."""
    
def test_source_module_remux():
    """Source module detects 'REMUX' from filename."""

# Test edition service
def test_edition_generation_order():
    """Modules applied in configured order."""
    
def test_edition_separator():
    """Configured separator used between modules."""
    
def test_edition_backup_created():
    """Original edition backed up before change."""
    
def test_edition_restore():
    """Restore reverts to backed up edition."""
```

---

### Phase 6: Results UI & Artwork Picker (Days 14-16)

**Objective:** User interface for reviewing and fixing issues.

**Tasks:**
1. Build issue list component:
   - Filterable by issue type
   - Filterable by library
   - Filterable by status
   - Search by title
   - Pagination
2. Create issue card component:
   - Current artwork thumbnail (if exists)
   - Issue type badge
   - Suggested artwork thumbnails
   - Accept/Skip/Browse buttons
3. Build artwork picker modal:
   - Grid of all available artwork
   - Grouped by provider
   - Filter by language
   - Large preview on hover
   - Select and apply
4. Implement artwork application:
   - Upload selected artwork to Plex
   - Lock artwork after applying
   - Verify application success
   - Update issue status
5. Create match fixer for unmatched items:
   - Search for potential matches
   - Display match candidates
   - Apply selected match

**Verification Checklist:**
- [ ] Issues displayed with correct information
- [ ] Filters work correctly
- [ ] Search finds issues by title
- [ ] Pagination works
- [ ] Artwork picker shows all provider results
- [ ] Selected artwork applied to Plex
- [ ] Artwork locked after applying
- [ ] Issue marked as resolved

**Tests Required:**
```javascript
// Frontend E2E tests
test('filter issues by type', async ({ page }) => {
  // Select "Missing Poster" filter
  // Verify only poster issues shown
});

test('search issues by title', async ({ page }) => {
  // Enter search term
  // Verify matching issues shown
});

test('accept artwork suggestion', async ({ page }) => {
  // Click accept on first suggestion
  // Verify toast notification
  // Verify issue removed from list
});

test('browse and select alternative', async ({ page }) => {
  // Click browse all
  // Select different artwork
  // Verify applied
});
```

---

### Phase 7: Auto-Fix & Scheduling (Days 17-19)

**Objective:** Automated fixes and scheduled scans.

**Tasks:**
1. Implement `AutoFixService`:
   - Apply top suggestion to each issue
   - Skip unmatched items (configurable)
   - Track success/failure counts
   - Progress streaming
2. Create auto-fix UI:
   - Confirmation dialog
   - Options (skip unmatched, min score)
   - Progress display
   - Results summary
3. Implement `ScanScheduler`:
   - APScheduler integration
   - Cron expression parsing
   - Job persistence across restarts
4. Create schedule CRUD:
   - Create schedule with cron
   - Update schedule
   - Delete schedule
   - Enable/disable schedule
5. Build schedule management UI:
   - Schedule list with status
   - Create/edit dialog
   - Cron presets (daily, weekly, monthly)
   - Next run time display
6. Implement auto-commit:
   - Wait for scan completion
   - Apply auto-fix with configured options
   - Log results

**Verification Checklist:**
- [ ] Auto-fix applies top suggestions
- [ ] Unmatched items skipped correctly
- [ ] Progress displayed during auto-fix
- [ ] Schedules persist across restarts
- [ ] Scheduled scans trigger at correct time
- [ ] Auto-commit runs after scheduled scan
- [ ] Schedule can be enabled/disabled

**Tests Required:**
```python
async def test_autofix_applies_top_suggestions():
    """Auto-fix selects highest priority artwork."""
    
async def test_autofix_skips_unmatched():
    """Auto-fix skips unmatched items when configured."""
    
async def test_schedule_cron_parsing():
    """Cron expressions parsed correctly."""
    
async def test_schedule_triggers_scan():
    """Scheduled scan starts at configured time."""
    
async def test_autocommit_after_schedule():
    """Auto-commit runs after scheduled scan completes."""
    
async def test_schedule_persistence():
    """Schedules persist across server restarts."""
```

---

### Phase 8: Polish & Documentation (Days 20-21)

**Objective:** Production-ready quality.

**Tasks:**
1. Comprehensive error handling:
   - API errors return clear messages
   - Network failures handled gracefully
   - Rate limits respected
2. Loading states:
   - Skeleton loaders for lists
   - Spinners for actions
   - Disabled buttons during processing
3. Toast notifications:
   - Success messages
   - Error messages with details
   - Progress notifications
4. User documentation:
   - README with setup instructions
   - API key acquisition guides
   - Troubleshooting section
5. API documentation:
   - OpenAPI/Swagger generation
   - Endpoint descriptions
   - Request/response examples
6. Performance optimization:
   - Database query optimization
   - Response caching where appropriate
   - Image lazy loading
7. Security review:
   - API key handling
   - Input validation
   - SQL injection prevention

**Verification Checklist:**
- [ ] All error states have user-friendly messages
- [ ] No unhandled promise rejections
- [ ] Loading spinners during async operations
- [ ] Toasts shown for all actions
- [ ] README complete and accurate
- [ ] API docs accessible at /docs
- [ ] No security vulnerabilities

---

## Testing Strategy

### Test Pyramid

```
                    ┌─────────────┐
                    │    E2E      │  5-10 critical user journeys
                    │   Tests     │
                    ├─────────────┤
                    │ Integration │  30-50 API + DB tests
                    │   Tests     │
                    ├─────────────┤
                    │    Unit     │  100+ function tests
                    │   Tests     │
                    └─────────────┘
```

### Running Tests

```bash
# Backend unit tests
cd backend && pytest tests/ -v

# Backend with coverage
cd backend && pytest tests/ --cov=. --cov-report=html

# Frontend tests
cd frontend && npm test

# E2E tests
cd frontend && npx playwright test

# All tests (CI)
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Pre-Commit Checks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest backend/tests/ -x
        language: system
        pass_filenames: false
        
      - id: frontend-test
        name: frontend tests
        entry: npm test --prefix frontend
        language: system
        pass_filenames: false
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v --cov

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci && npm test

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker-compose up -d
      - run: npx playwright test
```

---

## Deployment

### Docker Compose (Production)

```yaml
version: '3.8'

services:
  metafix:
    build: .
    container_name: metafix
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///app/data/metafix.db
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Dockerfile

```dockerfile
# Stage 1: Frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend
FROM python:3.12-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend build
COPY --from=frontend /app/frontend/.next ./frontend/.next
COPY --from=frontend /app/frontend/public ./frontend/public
COPY --from=frontend /app/frontend/package.json ./frontend/

# Create data directory
RUN mkdir -p /app/data

EXPOSE 3000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "3000"]
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Encryption key for tokens (generate with `openssl rand -hex 32`) |
| `DATABASE_URL` | No | SQLite path (default: `./data/metafix.db`) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

---

## Timeline Summary

| Phase | Duration | Key Deliverables | Tests Required |
|-------|----------|------------------|----------------|
| 0 | 1 day | Project setup, Docker, database | 5 tests |
| 1 | 2 days | Plex integration, onboarding | 10 tests |
| 2 | 2 days | Artwork scanner, issue detection | 15 tests |
| 3 | 2 days | Scan manager, pause/resume/cancel | 10 tests |
| 4 | 3 days | All 5 metadata providers | 20 tests |
| 5 | 3 days | Edition manager, 22 modules | 30 tests |
| 6 | 3 days | Results UI, artwork picker | 10 E2E tests |
| 7 | 3 days | Auto-fix, scheduling | 15 tests |
| 8 | 2 days | Polish, documentation | Review |
| **Total** | **~3 weeks** | Full feature set | **~115 tests** |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Implement caching, respect retry-after headers, exponential backoff |
| Large library performance | Sequential processing, checkpoints, progress streaming |
| Plex API changes | Abstract into service layer, version pinning, graceful degradation |
| Provider API changes | Graceful degradation, fallback to other providers |
| Data loss | Automatic backups before modifications, transaction handling |
| Concurrent modifications | Database transactions, optimistic locking |
| Test flakiness | Mock external APIs, use deterministic test data |

---

## Success Criteria

1. **Functionality**
   - [ ] Can detect all 6 issue types in a 50k+ item library
   - [ ] All 5 providers return artwork successfully
   - [ ] All 22 edition modules extract correct data
   - [ ] Scheduled scans run reliably

2. **Performance**
   - [ ] Full library scan completes within 2 hours
   - [ ] UI remains responsive during scan
   - [ ] Memory usage stable over long scans

3. **Reliability**
   - [ ] Scan resumes after server restart
   - [ ] No data corruption on crash
   - [ ] All errors logged and reported to user

4. **User Experience**
   - [ ] Onboarding completable in under 5 minutes
   - [ ] Artwork preview loads within 2 seconds
   - [ ] All actions provide feedback

5. **Quality**
   - [ ] All tests passing
   - [ ] No critical/high severity bugs
   - [ ] Documentation complete

---

## Appendix: API Keys Required

| Provider | Where to Get | Required? |
|----------|--------------|-----------|
| **Plex** | Server settings or Preferences.xml | Yes |
| **TMDB** | https://www.themoviedb.org/settings/api | Recommended |
| **Fanart.tv** | https://fanart.tv/get-an-api-key/ | Recommended |
| **TVDB** | https://www.thetvdb.com/dashboard/account/apikey | Optional |
| **Mediux** | User registration at mediux.pro | Optional |

---

*End of Technical Plan*
