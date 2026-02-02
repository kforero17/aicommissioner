"""Recap model for storing generated AI content."""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class RecapType(str, Enum):
    """Types of generated recaps."""
    POWER_RANKINGS = "power_rankings"
    WAIVER_RECAP = "waiver_recap"
    WEEKLY_RECAP = "weekly_recap"


class RecapStatus(str, Enum):
    """Publication status of a recap.

    State machine flow:
    - DRAFT: Created immediately, may have no content yet or content generated
    - PUBLISHED: Content generated and successfully published to channels
    - FAILED: Content generation failed (no content to publish)
    - PUBLISH_FAILED: Content generated but publishing to channels failed (can retry)
    """
    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"
    PUBLISH_FAILED = "publish_failed"  # Content generated but publishing failed


class Recap(Base):
    """
    Recap model for storing generated AI content.

    Persists all generated recaps (power rankings, waiver recaps, weekly recaps)
    allowing users to view historical content in the league hub feed and history tabs.
    """

    __tablename__ = "recaps"
    __table_args__ = (
        # Idempotency constraint: prevents duplicate recaps when Celery retries or manual sync spam
        # Uses functional index on COALESCE(ai_persona, '') to handle NULL persona values
        Index(
            'uq_recaps_league_season_week_type_persona',
            'league_id', 'season', 'week', 'recap_type',
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    recap_type: Mapped[RecapType] = mapped_column(
        SQLEnum(RecapType),
        nullable=False,
        index=True
    )
    week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[RecapStatus] = mapped_column(
        SQLEnum(RecapStatus),
        default=RecapStatus.DRAFT,
        nullable=False,
        index=True
    )

    rendering_mode: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    ai_persona: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    publish_channels: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Observability and debugging fields
    generation_metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON blob: facts pack, scores, transaction IDs, derived picks, warnings"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Stores failure reason if status=failed"
    )
    llm_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model used for generation (e.g., gpt-4o-mini)"
    )
    llm_latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="LLM API call latency in milliseconds"
    )
    tokens_in: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Input tokens sent to LLM"
    )
    tokens_out: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Output tokens received from LLM"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    league: Mapped["League"] = relationship("League", back_populates="recaps")

    def __repr__(self) -> str:
        return f"<Recap(id={self.id}, league_id={self.league_id}, type={self.recap_type}, week={self.week})>"
