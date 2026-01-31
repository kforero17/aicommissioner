"""League member model for multi-user league access."""
from datetime import datetime
from typing import Optional
from enum import Enum
import secrets

from sqlalchemy import ForeignKey, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class MemberRole(str, Enum):
    """Roles for league members."""
    COMMISSIONER = "commissioner"
    MEMBER = "member"


class LeagueMember(Base):
    """
    League membership model for multi-user access.

    Supports invite-based membership system where commissioners can invite
    other users to view and interact with league content. Each member can
    have different roles and preferences for content delivery.
    """

    __tablename__ = "league_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Role and status
    role: Mapped[MemberRole] = mapped_column(
        SQLEnum(MemberRole),
        default=MemberRole.MEMBER,
        nullable=False
    )

    # Invite tracking
    invite_token: Mapped[Optional[str]] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True
    )
    invite_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    invited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Member preferences (JSON stored as text)
    # Schema: {
    #   "mute_waivers": false,
    #   "mute_power_rankings": false,
    #   "mute_weekly_recaps": false,
    #   "email_digest": "weekly"  # "none", "daily", "weekly"
    # }
    preferences: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    league: Mapped["League"] = relationship("League", back_populates="members")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="league_memberships")

    @staticmethod
    def generate_invite_token() -> str:
        """Generate a secure random invite token."""
        return secrets.token_urlsafe(32)

    def __repr__(self) -> str:
        return f"<LeagueMember(id={self.id}, league_id={self.league_id}, user_id={self.user_id}, role={self.role})>"
