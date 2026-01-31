"""Authentication routes for Yahoo OAuth and Sleeper integration."""
import json
from datetime import datetime, timedelta, timezone
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

oauth = OAuth()

if settings.debug:
    oauth.register(
        name='yahoo',
        client_id=settings.yahoo_client_id,
        client_secret=settings.yahoo_client_secret,
        authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
        access_token_url='https://api.login.yahoo.com/oauth2/get_token',
        client_kwargs={'verify': False}
    )
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'verify': False
        }
    )
else:
    oauth.register(
        name='yahoo',
        client_id=settings.yahoo_client_id,
        client_secret=settings.yahoo_client_secret,
        authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
        access_token_url='https://api.login.yahoo.com/oauth2/get_token',
        client_kwargs={}
    )
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> User:
    """Get current authenticated user from cookie or Authorization header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = None

    # Try to get token from cookie first
    token = request.cookies.get("access_token")

    # Fallback to Authorization header if no cookie
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
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
            detail="Yahoo OAuth not configured. Please set YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET environment variables."
        )

    try:
        # Use configured redirect URI to ensure HTTPS
        redirect_uri = settings.yahoo_redirect_uri
        print(f"OAuth redirect URI being sent: {redirect_uri}")
        return await oauth.yahoo.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Yahoo OAuth: {str(e)}"
        )


@router.get("/yahoo/start")
async def yahoo_start(request: Request):
    """Alias for yahoo_login - matches frontend expectation."""
    return await yahoo_login(request)


@router.get("/yahoo/callback")
async def yahoo_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Yahoo OAuth callback."""
    try:
        token = await oauth.yahoo.authorize_access_token(request)
    except OAuthError as error:
        print(f"OAuth Error Details: {error.error}")
        print(f"Error Description: {error.description}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error.error} - {error.description}"
        )
    except Exception as e:
        print(f"Unexpected error during token exchange: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token exchange failed: {str(e)}"
        )

    # Extract user info from JWT access token
    print(f"Token received: {list(token.keys())}")

    # Try to decode the access token as a JWT to extract user info
    access_token = token.get('access_token')
    yahoo_user_id = None
    email = None
    username = None

    try:
        # Decode JWT without verification (we trust Yahoo's token)
        from jose import jwt as jose_jwt
        payload = jose_jwt.get_unverified_claims(access_token)
        print(f"JWT payload: {payload}")

        yahoo_user_id = payload.get('sub')
        email = payload.get('email')
        username = payload.get('preferred_username') or payload.get('name') or payload.get('nickname')
    except Exception as e:
        print(f"Could not decode JWT: {e}")
        # JWT decode failed - use Yahoo GUID from token endpoint response
        # Yahoo sometimes includes xoauth_yahoo_guid in the token response
        yahoo_user_id = token.get('xoauth_yahoo_guid')

    if not yahoo_user_id:
        # Last resort: generate a stable ID from the access token
        import hashlib
        yahoo_user_id = hashlib.sha256(access_token.encode()).hexdigest()[:16]
        print(f"Generated fallback user ID: {yahoo_user_id}")
        username = f"yahoo_user_{yahoo_user_id[:8]}"

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
        user.yahoo_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token['expires_in'])

    await db.commit()
    await db.refresh(user)

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Trigger league import - try Celery first, fall back to sync if unavailable
    task_id = None
    try:
        from schedulers.tasks import import_yahoo_leagues_task
        task = import_yahoo_leagues_task.apply_async(args=[user.id])
        task_id = task.id
    except Exception as e:
        # Celery/Redis not available - run import synchronously
        import logging
        logging.warning(f"Celery unavailable, running import synchronously: {e}")
        from ingestors.yahoo_ingestor import ingest_yahoo_leagues
        import asyncio
        asyncio.create_task(ingest_yahoo_leagues(user.id))

    # Redirect to frontend with token and optional task_id
    frontend_url = settings.frontend_url or "http://localhost:3000"
    redirect_url = f"{frontend_url}/connect?yahoo_connected=true"
    if task_id:
        redirect_url += f"&task_id={task_id}"

    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Required for samesite="none"
        samesite="none",  # Allow cross-origin cookie sending (localhost -> tunnel)
        max_age=settings.access_token_expire_minutes * 60,
        path="/"
    )

    return response


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth flow."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    try:
        redirect_uri = settings.google_redirect_uri
        print(f"Google OAuth redirect URI being sent: {redirect_uri}")
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error.error} - {error.description}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token exchange failed: {str(e)}"
        )

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Google"
        )

    google_user_id = user_info.get('sub')
    email = user_info.get('email')
    name = user_info.get('name')

    if not google_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user ID from Google"
        )

    result = await db.execute(select(User).filter(User.google_user_id == google_user_id))
    user = result.scalar_one_or_none()

    if not user:
        existing_user_by_email = None
        if email:
            result = await db.execute(select(User).filter(User.email == email))
            existing_user_by_email = result.scalar_one_or_none()

        if existing_user_by_email:
            user = existing_user_by_email
            user.google_user_id = google_user_id
        else:
            user = User(
                google_user_id=google_user_id,
                email=email,
                username=name,
            )
            db.add(user)
    else:
        user.email = email or user.email
        user.username = name or user.username

    await db.commit()
    await db.refresh(user)

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    frontend_url = settings.frontend_url or "http://localhost:3000"
    redirect_url = f"{frontend_url}/dashboard"

    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.access_token_expire_minutes * 60,
        path="/"
    )

    return response


@router.post("/sleeper/leagues")
async def add_sleeper_leagues(
    request: SleeperLeagueRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add Sleeper league IDs to user account and trigger import."""
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

    # Trigger imports - try Celery first, fall back to sync if unavailable
    task_ids = []
    try:
        from schedulers.tasks import import_sleeper_league_task
        for league_id in request.league_ids:
            task = import_sleeper_league_task.apply_async(args=[league_id, current_user.id])
            task_ids.append({
                "league_id": league_id,
                "task_id": task.id
            })
    except Exception as e:
        # Celery/Redis not available - run imports synchronously
        import logging
        logging.warning(f"Celery unavailable, running Sleeper import synchronously: {e}")
        from ingestors.sleeper_ingestor import ingest_sleeper_league
        import asyncio
        for league_id in request.league_ids:
            asyncio.create_task(ingest_sleeper_league(league_id, current_user.id))
            task_ids.append({"league_id": league_id, "task_id": None})

    # Convert back to list for response
    sleeper_leagues = json.loads(current_user.sleeper_leagues) if current_user.sleeper_leagues else []

    return {
        "message": "Sleeper league import started",
        "task_ids": task_ids,
        "user": UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            yahoo_user_id=current_user.yahoo_user_id,
            sleeper_leagues=sleeper_leagues,
            timezone=current_user.timezone,
            enable_llm_rendering=current_user.enable_llm_rendering
        )
    }


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


@router.post("/yahoo/import-leagues")
async def import_yahoo_leagues(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger Yahoo league import for authenticated user."""
    if not current_user.yahoo_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yahoo account not connected"
        )

    # Trigger import - try Celery first, fall back to sync if unavailable
    task_id = None
    try:
        from schedulers.tasks import import_yahoo_leagues_task
        task = import_yahoo_leagues_task.apply_async(args=[current_user.id])
        task_id = task.id
    except Exception as e:
        # Celery/Redis not available - run import synchronously
        import logging
        logging.warning(f"Celery unavailable, running Yahoo import synchronously: {e}")
        from ingestors.yahoo_ingestor import ingest_yahoo_leagues
        import asyncio
        asyncio.create_task(ingest_yahoo_leagues(current_user.id))

    return {
        "message": "Yahoo league import started",
        "task_id": task_id
    }


@router.get("/yahoo/status")
async def yahoo_connection_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check Yahoo connection status and imported leagues."""
    from models.league import League, ProviderType
    
    is_connected = bool(current_user.yahoo_access_token)
    token_expired = False
    
    if current_user.yahoo_token_expires_at:
        token_expired = current_user.yahoo_token_expires_at <= datetime.now(timezone.utc)
    
    # Get Yahoo leagues
    result = await db.execute(
        select(League).filter(
            League.provider == ProviderType.YAHOO,
            League.owner_id == current_user.id
        )
    )
    leagues = result.scalars().all()
    
    return {
        "connected": is_connected,
        "token_expired": token_expired,
        "yahoo_user_id": current_user.yahoo_user_id,
        "leagues": [
            {
                "id": league.id,
                "name": league.name,
                "provider_league_id": league.provider_league_id,
                "season": league.season,
                "last_sync_at": league.last_sync_at
            }
            for league in leagues
        ]
    }


@router.get("/yahoo/debug")
async def debug_yahoo_connection(
    current_user: User = Depends(get_current_user)
):
    """Debug Yahoo API connection."""
    if not current_user.yahoo_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yahoo account not connected"
        )
    
    from ingestors.yahoo_ingestor import YahooAPI
    import httpx
    
    api = YahooAPI(current_user.yahoo_access_token)
    debug_info = {
        "user_id": current_user.id,
        "yahoo_user_id": current_user.yahoo_user_id,
        "token_expires_at": current_user.yahoo_token_expires_at.isoformat() if current_user.yahoo_token_expires_at else None,
        "tests": {}
    }
    
    try:
        # Test 1: User info
        try:
            response = await api.client.get("https://api.login.yahoo.com/openid/v1/userinfo")
            debug_info["tests"]["user_info"] = {
                "status": response.status_code,
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text[:200]
            }
        except Exception as e:
            debug_info["tests"]["user_info"] = {"error": str(e)}
        
        # Test 2: Leagues endpoint
        try:
            game_id = "423"  # NFL
            url = f"{api.BASE_URL}/users;use_login=1/games;game_keys={game_id}/leagues"
            response = await api.client.get(url)
            debug_info["tests"]["leagues_api"] = {
                "url": url,
                "status": response.status_code,
                "content_type": response.headers.get('content-type', 'unknown'),
                "success": response.status_code == 200,
                "response_length": len(response.text),
                "response_preview": response.text[:300] if response.status_code == 200 else response.text[:200]
            }
        except Exception as e:
            debug_info["tests"]["leagues_api"] = {"error": str(e)}
        
        # Test 3: Parse leagues
        try:
            leagues = await api.get_user_leagues("nfl")
            debug_info["tests"]["parse_leagues"] = {
                "success": True,
                "count": len(leagues),
                "leagues": leagues[:2] if leagues else []  # First 2 leagues only
            }
        except Exception as e:
            debug_info["tests"]["parse_leagues"] = {"error": str(e)}
            
    finally:
        await api.close()
    
    return debug_info
