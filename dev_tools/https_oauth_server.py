#!/usr/bin/env python3
"""HTTPS OAuth server for Yahoo authentication."""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from config import settings

app = FastAPI()

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# OAuth configuration with HTTPS redirect URI
oauth = OAuth()
oauth.register(
    name='yahoo',
    client_id=settings.yahoo_client_id,
    client_secret=settings.yahoo_client_secret,
    authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
    access_token_url='https://api.login.yahoo.com/oauth2/get_token',
    client_kwargs={'scope': 'openid email profile fspt-r'}
)

@app.get("/")
async def root():
    return {"message": "HTTPS Yahoo OAuth Server", "status": "running"}

@app.get("/auth/yahoo/start")
@app.get("/auth/yahoo/login")
async def yahoo_login(request: Request):
    """Initiate Yahoo OAuth flow."""
    if not settings.yahoo_client_id or not settings.yahoo_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Yahoo OAuth not configured"
        )
    
    try:
        # Use the HTTPS redirect URI from settings
        redirect_uri = "https://localhost:8000/auth/yahoo/callback"
        return await oauth.yahoo.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Yahoo OAuth: {str(e)}"
        )

@app.get("/auth/yahoo/callback")
async def yahoo_callback(request: Request):
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
        try:
            resp = await oauth.yahoo.get('https://api.login.yahoo.com/openid/v1/userinfo', token=token)
            user_info = resp.json()
        except Exception as e:
            print(f"Error getting user info: {e}")
            user_info = {}
    
    # For testing, redirect to frontend with success
    frontend_url = settings.frontend_url or "http://localhost:3003"
    
    # Create a simple token for testing (in production, this would be a proper JWT)
    test_token = f"test_token_{user_info.get('sub', 'unknown')}"
    
    redirect_url = f"{frontend_url}/connect?yahoo_connected=true&token={test_token}"
    
    return RedirectResponse(url=redirect_url)

@app.get("/test/config")
async def test_config():
    """Test endpoint to check configuration."""
    client_id = settings.yahoo_client_id or ""
    client_id_preview = f"{client_id[:10]}...{client_id[-6:]}" if len(client_id) > 16 else "Not set"
    
    return {
        "yahoo_client_id_set": bool(settings.yahoo_client_id),
        "yahoo_client_id_preview": client_id_preview,
        "yahoo_client_secret_set": bool(settings.yahoo_client_secret),
        "frontend_url": settings.frontend_url,
        "redirect_uri": "https://localhost:8000/auth/yahoo/callback",
        "server_mode": "HTTPS"
    }

@app.get("/debug/yahoo")
async def debug_yahoo():
    """Debug Yahoo OAuth configuration."""
    return {
        "oauth_endpoints": {
            "authorize_url": "https://api.login.yahoo.com/oauth2/request_auth",
            "access_token_url": "https://api.login.yahoo.com/oauth2/get_token"
        },
        "client_configured": bool(settings.yahoo_client_id and settings.yahoo_client_secret),
        "scope": "openid email profile fspt-r",
        "error_from_url": "unauthorized_client - invalid client id"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
