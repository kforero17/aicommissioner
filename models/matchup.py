"""Matchup model for storing weekly matchup data."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Integer, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class Matchup(Base):
    """Matchup model for storing weekly head-to-head matchup data."""
    
    __tablename__ = "matchups"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Matchup identifiers
    provider_matchup_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Team 1 data
    team1_roster_id: Mapped[str] = mapped_column(String(100), nullable=False)
    team1_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    team1_projected: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Team 2 data (nullable for bye weeks)
    team2_roster_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    team2_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    team2_projected: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Matchup metadata
    is_playoff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_championship: Mapped[bool] = mapped_column(Boolean, default=False)
    is_consolation: Mapped[bool] = mapped_column(Boolean, default=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Winner determination
    winner_roster_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    margin_of_victory: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign Keys
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    
    # Relationships
    league: Mapped["League"] = relationship("League", back_populates="matchups")
    
    def __repr__(self) -> str:
        return f"<Matchup(id={self.id}, week={self.week}, team1_points={self.team1_points}, team2_points={self.team2_points})>"
