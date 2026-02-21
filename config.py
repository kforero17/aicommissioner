"""Application configuration settings."""
import os
from typing import Optional

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database (REQUIRED - no default for security)
    database_url: str
    
    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379"
    
    # Yahoo OAuth
    yahoo_client_id: Optional[str] = None
    yahoo_client_secret: Optional[str] = None
    yahoo_redirect_uri: str = "https://pike-charger-learners-schedule.trycloudflare.com/auth/yahoo/callback"

    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "https://pike-charger-learners-schedule.trycloudflare.com/auth/google/callback"
    
    # AI Services
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    news_api_key: Optional[str] = None

    # Security (REQUIRED - no defaults for sensitive keys)
    secret_key: str
    encryption_key: str  # For encrypting OAuth tokens at rest (Fernet key)
    access_token_expire_minutes: int = 30

    @field_validator('encryption_key')
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate that encryption_key is a valid Fernet key."""
        if not v:
            raise ValueError('encryption_key cannot be empty')
        try:
            # Try to create a Fernet instance to validate the key format
            Fernet(v.encode())
        except Exception as e:
            raise ValueError(
                f'encryption_key must be a valid Fernet key. '
                f'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" '
                f'Error: {str(e)}'
            )
        return v
    
    # GroupMe
    groupme_access_token: Optional[str] = None
    
    # Email/SMTP
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    
    # Application (debug defaults to False for security)
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # Timezone
    default_timezone: str = "America/Chicago"
    
    class Config:
        env_file = ".env"


settings = Settings()
