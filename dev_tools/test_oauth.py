#!/usr/bin/env python3
"""Minimal test server for Yahoo OAuth without database dependencies."""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from config import settings

app = FastAPI()

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# OAuth configuration
oauth = OAuth()
oauth.register(
    name='yahoo',
    client_id=settings.yahoo_client_id,
    client_secret=settings.yahoo_client_secret,
    authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
    access_token_url='https://api.login.yahoo.com/oauth2/get_token',
    client_kwargs={
        'scope': 'openid email profile fspt-r',
        'verify': False  # Disable SSL verification for testing
    }
)

@app.get("/")
async def root():
    return {"message": "Yahoo OAuth Test Server", "status": "running"}

@app.get("/auth/yahoo/start")
@app.get("/auth/yahoo/login")
async def yahoo_login(request: Request):
    """Initiate Yahoo OAuth flow."""
    if not settings.yahoo_client_id or not settings.yahoo_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Yahoo OAuth not configured. Please set YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET environment variables."
        )
    
    try:
        redirect_uri = request.url_for('yahoo_callback')
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
        # Fallback to getting user info manually
        resp = await oauth.yahoo.get('https://api.login.yahoo.com/openid/v1/userinfo', token=token)
        user_info = resp.json()
    
    # For testing, just return the user info and token info
    frontend_url = settings.frontend_url or "http://localhost:3000"
    redirect_url = f"{frontend_url}/connect?yahoo_connected=true&test_mode=true"
    
    return RedirectResponse(url=redirect_url)

@app.get("/test/config")
async def test_config():
    """Test endpoint to check configuration."""
    return {
        "yahoo_client_id_set": bool(settings.yahoo_client_id),
        "yahoo_client_secret_set": bool(settings.yahoo_client_secret),
        "frontend_url": settings.frontend_url,
        "redirect_uri": settings.yahoo_redirect_uri
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
