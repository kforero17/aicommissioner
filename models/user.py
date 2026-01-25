"""User model for storing user information."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property

from database.connection import Base
from utilities.encryption import token_encryption


class User(Base):
    """User model for storing user authentication and profile data."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    
    # OAuth provider data
    yahoo_user_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    _yahoo_access_token_encrypted: Mapped[Optional[str]] = mapped_column("yahoo_access_token", Text, nullable=True)
    _yahoo_refresh_token_encrypted: Mapped[Optional[str]] = mapped_column("yahoo_refresh_token", Text, nullable=True)
    yahoo_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Sleeper integration (simple league ID)
    sleeper_leagues: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of league IDs
    
    # User preferences
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(50), default="America/Chicago")
    
    # AI preferences
    enable_llm_rendering: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_persona_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    leagues: Mapped[list["League"]] = relationship("League", back_populates="owner", cascade="all, delete-orphan")

    @hybrid_property
    def yahoo_access_token(self) -> Optional[str]:
        """Decrypt and return Yahoo access token."""
        return token_encryption.decrypt_optional(self._yahoo_access_token_encrypted)

    @yahoo_access_token.setter
    def yahoo_access_token(self, value: Optional[str]) -> None:
        """Encrypt and store Yahoo access token."""
        self._yahoo_access_token_encrypted = token_encryption.encrypt_optional(value)

    @hybrid_property
    def yahoo_refresh_token(self) -> Optional[str]:
        """Decrypt and return Yahoo refresh token."""
        return token_encryption.decrypt_optional(self._yahoo_refresh_token_encrypted)

    @yahoo_refresh_token.setter
    def yahoo_refresh_token(self, value: Optional[str]) -> None:
        """Encrypt and store Yahoo refresh token."""
        self._yahoo_refresh_token_encrypted = token_encryption.encrypt_optional(value)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
