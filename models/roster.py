"""Roster model for storing team roster information."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Integer, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class Roster(Base):
    """Roster model for storing team roster and performance data."""
    
    __tablename__ = "rosters"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Provider-specific identifiers
    provider_roster_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider_owner_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Team info
    team_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Performance metrics
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    ties: Mapped[int] = mapped_column(Integer, default=0)
    points_for: Mapped[float] = mapped_column(Float, default=0.0)
    points_against: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Power ranking data
    power_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    power_rank_previous: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Current roster data (JSON)
    starters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of player IDs
    bench: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON array of player IDs
    ir: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON array of player IDs
    
    # FAAB/Waiver budget
    faab_budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    waiver_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign Keys
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    
    # Relationships
    league: Mapped["League"] = relationship("League", back_populates="rosters")
    
    def __repr__(self) -> str:
        return f"<Roster(id={self.id}, team_name={self.team_name}, wins={self.wins}, losses={self.losses})>"
