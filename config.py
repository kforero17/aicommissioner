"""Application configuration settings."""
import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://username:password@localhost/aicommissioner"
    
    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379"
    
    # Yahoo OAuth
    yahoo_client_id: Optional[str] = None
    yahoo_client_secret: Optional[str] = None
    yahoo_redirect_uri: str = "http://localhost:8000/auth/yahoo/callback"
    
    # AI Services
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Security
    secret_key: str = "your_secret_key_here_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # GroupMe
    groupme_access_token: Optional[str] = None
    
    # Email/SMTP
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    
    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Timezone
    default_timezone: str = "America/Chicago"
    
    class Config:
        env_file = ".env"


settings = Settings()
