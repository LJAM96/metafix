"""Database models for MetaFix."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Config(Base):
    """Configuration key-value storage."""

    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Scan(Base):
    """Scan job tracking."""

    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False, default="artwork")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Configuration (JSON)
    config: Mapped[str] = mapped_column(Text, nullable=False)

    # Progress
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    issues_found: Mapped[int] = mapped_column(Integer, default=0)
    editions_updated: Mapped[int] = mapped_column(Integer, default=0)
    current_library: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_item: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Checkpoint for resume (JSON)
    checkpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Trigger source
    triggered_by: Mapped[str] = mapped_column(String(50), default="manual")

    # Relationships
    events: Mapped[list["ScanEvent"]] = relationship(
        "ScanEvent", back_populates="scan", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="scan", cascade="all, delete-orphan"
    )


class ScanEvent(Base):
    """Scan event log."""

    __tablename__ = "scan_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(Integer, ForeignKey("scans.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="events")


class Issue(Base):
    """Artwork issue tracking."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(Integer, ForeignKey("scans.id", ondelete="CASCADE"))
    plex_rating_key: Mapped[str] = mapped_column(String(50), nullable=False)
    plex_guid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    library_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="issues")
    suggestions: Mapped[list["Suggestion"]] = relationship(
        "Suggestion", back_populates="issue", cascade="all, delete-orphan"
    )


class Suggestion(Base):
    """Artwork suggestions for issues."""

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    artwork_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    set_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    creator_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    issue: Mapped["Issue"] = relationship("Issue", back_populates="suggestions")


class ArtworkCache(Base):
    """Artwork provider response cache."""

    __tablename__ = "artwork_cache"

    external_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    artwork_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EditionBackup(Base):
    """Edition metadata backup."""

    __tablename__ = "edition_backups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plex_rating_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_edition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_edition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    backed_up_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    restored_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EditionConfig(Base):
    """Edition module configuration."""

    __tablename__ = "edition_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled_modules: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    module_order: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    settings: Mapped[str] = mapped_column(Text, nullable=False)  # JSON object
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Schedule(Base):
    """Scheduled scan configuration."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)

    # What to run
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False, default="both")
    config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON

    # Auto-commit settings
    auto_commit: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_commit_options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
