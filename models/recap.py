"""Recap model for storing generated AI content."""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class RecapType(str, Enum):
    """Types of generated recaps."""
    POWER_RANKINGS = "power_rankings"
    WAIVER_RECAP = "waiver_recap"
    WEEKLY_RECAP = "weekly_recap"


class RecapStatus(str, Enum):
    """Publication status of a recap."""
    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"


class Recap(Base):
    """
    Recap model for storing generated AI content.

    Persists all generated recaps (power rankings, waiver recaps, weekly recaps)
    allowing users to view historical content in the league hub feed and history tabs.
    """

    __tablename__ = "recaps"

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
