"""League model for storing fantasy league information."""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import DateTime, String, Integer, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class ProviderType(str, Enum):
    """Supported fantasy sports providers."""
    YAHOO = "yahoo"
    SLEEPER = "sleeper"


class LeagueType(str, Enum):
    """Types of fantasy leagues."""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    BASEBALL = "baseball"
    HOCKEY = "hockey"


class League(Base):
    """League model for storing normalized league data from different providers."""
    
    __tablename__ = "leagues"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Provider-specific identifiers
    provider: Mapped[ProviderType] = mapped_column(SQLEnum(ProviderType), nullable=False)
    provider_league_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # League basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    league_type: Mapped[LeagueType] = mapped_column(SQLEnum(LeagueType), default=LeagueType.FOOTBALL)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # League settings
    num_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    scoring_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ppr, standard, etc.
    trade_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # GroupMe integration
    groupme_bot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # AI settings
    enable_power_rankings: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_waiver_recaps: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_llm_rendering: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_persona_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Schedule settings
    power_rankings_day: Mapped[str] = mapped_column(String(10), default="tuesday")
    power_rankings_time: Mapped[str] = mapped_column(String(10), default="09:00")
    waiver_recap_day: Mapped[str] = mapped_column(String(10), default="wednesday")
    waiver_recap_time: Mapped[str] = mapped_column(String(10), default="09:00")
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign Keys
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="leagues")
    rosters: Mapped[list["Roster"]] = relationship("Roster", back_populates="league", cascade="all, delete-orphan")
    matchups: Mapped[list["Matchup"]] = relationship("Matchup", back_populates="league", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="league", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<League(id={self.id}, name={self.name}, provider={self.provider}, season={self.season})>"
