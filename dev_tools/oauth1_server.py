#!/usr/bin/env python3
"""
OAuth 1.0a server for Yahoo Fantasy Sports API.

⚠️  WARNING: DEVELOPMENT ONLY ⚠️
This file is for LOCAL DEVELOPMENT ONLY with self-signed certificates.
DO NOT use this code in production - it contains SSL verification settings
that are appropriate ONLY for local development with localhost certificates.

For production, use proper SSL certificates from a trusted CA.
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import requests
from requests_oauthlib import OAuth1Session
from config import settings
import os

app = FastAPI()

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Yahoo OAuth 1.0a endpoints (from their documentation)
REQUEST_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_request_token'
AUTHORIZATION_URL = 'https://api.login.yahoo.com/oauth/v2/request_auth'
ACCESS_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_token'

@app.get("/")
async def root():
    return {"message": "Yahoo OAuth 1.0a Server", "status": "running"}

@app.get("/auth/yahoo/start")
@app.get("/auth/yahoo/login")
async def yahoo_login(request: Request):
    """Initiate Yahoo OAuth 1.0a flow."""
    if not settings.yahoo_client_id or not settings.yahoo_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Yahoo OAuth not configured"
        )
    
    try:
        # Step 1: Get request token
        oauth = OAuth1Session(
            settings.yahoo_client_id,
            client_secret=settings.yahoo_client_secret,
            callback_uri="https://localhost:8000/auth/yahoo/callback"
        )
        
        # Request token from Yahoo
        fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
        
        # Store request token in session
        request.session['oauth_token'] = fetch_response.get('oauth_token')
        request.session['oauth_token_secret'] = fetch_response.get('oauth_token_secret')
        
        # Step 2: Redirect user to Yahoo for authorization
        authorization_url = oauth.authorization_url(AUTHORIZATION_URL)
        
        print(f"🔗 Redirecting to: {authorization_url}")
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        print(f"❌ OAuth 1.0a error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Yahoo OAuth: {str(e)}"
        )

@app.get("/auth/yahoo/callback")
async def yahoo_callback(request: Request):
    """Handle Yahoo OAuth 1.0a callback."""
    try:
        # Get OAuth verifier from callback
        oauth_verifier = request.query_params.get('oauth_verifier')
        if not oauth_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OAuth verifier received"
            )
        
        # Get stored request token from session
        oauth_token = request.session.get('oauth_token')
        oauth_token_secret = request.session.get('oauth_token_secret')
        
        if not oauth_token or not oauth_token_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No request token found in session"
            )
        
        # Step 3: Exchange request token for access token
        oauth = OAuth1Session(
            settings.yahoo_client_id,
            client_secret=settings.yahoo_client_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret,
            verifier=oauth_verifier
        )
        
        # Get access token
        oauth_tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
        
        # Store access token (in production, store this securely)
        access_token = oauth_tokens.get('oauth_token')
        access_token_secret = oauth_tokens.get('oauth_token_secret')
        
        print(f"✅ Got access token: {access_token[:10]}...")
        print(f"✅ Got access token secret: {access_token_secret[:10]}...")
        
        # Test API call to verify it works
        try:
            # Create authenticated session
            auth_session = OAuth1Session(
                settings.yahoo_client_id,
                client_secret=settings.yahoo_client_secret,
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret
            )
            
            # Test API call - get user's leagues
            test_url = 'https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/leagues'
            response = auth_session.get(test_url)
            
            print(f"🧪 Test API call status: {response.status_code}")
            print(f"🧪 Test API response: {response.text[:200]}...")
            
        except Exception as e:
            print(f"⚠️ Test API call failed: {e}")
        
        # Redirect to frontend with success
        frontend_url = settings.frontend_url or "http://localhost:3000"
        test_token = f"oauth1_{access_token[:10]}"
        redirect_url = f"{frontend_url}/connect?yahoo_connected=true&token={test_token}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        print(f"❌ Callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )

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
        "oauth_version": "1.0a",
        "server_mode": "HTTPS"
    }

@app.get("/debug/oauth")
async def debug_oauth():
    """Debug OAuth 1.0a configuration."""
    return {
        "oauth_version": "1.0a (corrected from 2.0)",
        "request_token_url": REQUEST_TOKEN_URL,
        "authorization_url": AUTHORIZATION_URL,
        "access_token_url": ACCESS_TOKEN_URL,
        "callback_uri": "https://localhost:8000/auth/yahoo/callback",
        "fantasy_api_base": "https://fantasysports.yahooapis.com/fantasy/v2/",
        "documentation": "https://developer.yahoo.com/fantasysports/guide/"
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
