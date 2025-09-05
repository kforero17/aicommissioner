"""Transaction model for storing waiver wire and trade data."""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import DateTime, String, Integer, ForeignKey, Float, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class TransactionType(str, Enum):
    """Types of fantasy transactions."""
    ADD = "add"
    DROP = "drop"
    TRADE = "trade"
    WAIVER = "waiver"
    FREE_AGENT = "free_agent"


class TransactionStatus(str, Enum):
    """Transaction processing status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction(Base):
    """Transaction model for storing all league transactions (adds, drops, trades, etc.)."""
    
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Provider-specific identifiers
    provider_transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Transaction basic info
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Involved parties
    roster_id: Mapped[str] = mapped_column(String(100), nullable=False)  # Primary roster involved
    trade_partner_roster_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # For trades
    
    # Players involved (JSON arrays)
    players_added: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON array of player objects
    players_dropped: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of player objects
    
    # Financial details
    faab_bid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    waiver_priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Processing times
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign Keys
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    
    # Relationships
    league: Mapped["League"] = relationship("League", back_populates="transactions")
    
    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.transaction_type}, status={self.status}, week={self.week})>"
