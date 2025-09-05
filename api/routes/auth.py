"""Authentication routes for Yahoo OAuth and Sleeper integration."""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from jose import JWTError, jwt
from pydantic import BaseModel

from config import settings
from database.connection import get_db
from models.user import User
from models.league import League, ProviderType

router = APIRouter()
security = HTTPBearer()

# OAuth configuration
oauth = OAuth()
oauth.register(
    name='yahoo',
    client_id=settings.yahoo_client_id,
    client_secret=settings.yahoo_client_secret,
    server_metadata_url='https://api.login.yahoo.com/.well-known/openid_connect',
    client_kwargs={'scope': 'openid email profile'}
)


class SleeperLeagueRequest(BaseModel):
    """Request model for adding Sleeper leagues."""
    league_ids: list[str]


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: Optional[str]
    email: Optional[str]
    yahoo_user_id: Optional[str]
    sleeper_leagues: Optional[list[str]]
    timezone: str
    enable_llm_rendering: bool


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


@router.get("/yahoo/login")
async def yahoo_login(request: Request):
    """Initiate Yahoo OAuth flow."""
    if not settings.yahoo_client_id or not settings.yahoo_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Yahoo OAuth not configured"
        )
    
    redirect_uri = request.url_for('yahoo_callback')
    return await oauth.yahoo.authorize_redirect(request, redirect_uri)


@router.get("/yahoo/callback")
async def yahoo_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Yahoo OAuth callback."""
    try:
        token = await oauth.yahoo.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error.error}"
        )
    
    # Get user info from Yahoo
    user_info = token.get('userinfo')
    if not user_info:
        # Fallback to getting user info manually
        resp = await oauth.yahoo.get('https://api.login.yahoo.com/openid/v1/userinfo', token=token)
        user_info = resp.json()
    
    yahoo_user_id = user_info.get('sub')
    email = user_info.get('email')
    username = user_info.get('preferred_username') or user_info.get('nickname')
    
    # Find or create user
    result = await db.execute(select(User).filter(User.yahoo_user_id == yahoo_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            yahoo_user_id=yahoo_user_id,
            email=email,
            username=username,
        )
        db.add(user)
    else:
        # Update existing user
        user.email = email or user.email
        user.username = username or user.username
    
    # Store OAuth tokens
    user.yahoo_access_token = token['access_token']
    user.yahoo_refresh_token = token.get('refresh_token')
    if 'expires_in' in token:
        user.yahoo_token_expires_at = datetime.utcnow() + timedelta(seconds=token['expires_in'])
    
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # In a real app, you'd redirect to your frontend with the token
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/sleeper/leagues", response_model=UserResponse)
async def add_sleeper_leagues(
    request: SleeperLeagueRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add Sleeper league IDs to user account."""
    # Validate league IDs (basic validation - you might want to call Sleeper API to verify)
    for league_id in request.league_ids:
        if not league_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="League ID cannot be empty"
            )
    
    # Store league IDs as JSON
    current_user.sleeper_leagues = json.dumps(request.league_ids)
    await db.commit()
    await db.refresh(current_user)
    
    # Convert back to list for response
    sleeper_leagues = json.loads(current_user.sleeper_leagues) if current_user.sleeper_leagues else []
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        yahoo_user_id=current_user.yahoo_user_id,
        sleeper_leagues=sleeper_leagues,
        timezone=current_user.timezone,
        enable_llm_rendering=current_user.enable_llm_rendering
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    sleeper_leagues = json.loads(current_user.sleeper_leagues) if current_user.sleeper_leagues else []
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        yahoo_user_id=current_user.yahoo_user_id,
        sleeper_leagues=sleeper_leagues,
        timezone=current_user.timezone,
        enable_llm_rendering=current_user.enable_llm_rendering
    )


@router.post("/logout")
async def logout():
    """Logout endpoint (for completeness - JWT tokens are stateless)."""
    return {"message": "Successfully logged out"}


@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user account and all associated data."""
    await db.delete(current_user)
    await db.commit()
    return {"message": "Account deleted successfully"}
