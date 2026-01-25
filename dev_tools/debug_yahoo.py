#!/usr/bin/env python3
"""Debug Yahoo OAuth parameters."""

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from config import settings
import urllib.parse

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

oauth = OAuth()
oauth.register(
    name='yahoo',
    client_id=settings.yahoo_client_id,
    client_secret=settings.yahoo_client_secret,
    authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
    access_token_url='https://api.login.yahoo.com/oauth2/get_token',
    client_kwargs={'scope': 'openid email profile fspt-r'}
)

@app.get("/debug/oauth-params")
async def debug_oauth_params(request: Request):
    """Debug OAuth parameters being sent to Yahoo."""
    
    redirect_uri = str(request.url_for('yahoo_callback'))
    
    # Build the OAuth URL manually to see what parameters are sent
    params = {
        'response_type': 'code',
        'client_id': settings.yahoo_client_id,
        'redirect_uri': redirect_uri,
        'scope': 'openid email profile fspt-r',
        'state': 'debug_state'
    }
    
    oauth_url = 'https://api.login.yahoo.com/oauth2/request_auth?' + urllib.parse.urlencode(params)
    
    return {
        'oauth_url': oauth_url,
        'redirect_uri': redirect_uri,
        'client_id': settings.yahoo_client_id,
        'parameters': params,
        'app_config_should_have': {
            'redirect_uri': redirect_uri,
            'note': 'Make sure this EXACT redirect URI is configured in your Yahoo app'
        }
    }

@app.get("/auth/yahoo/callback")
async def yahoo_callback():
    return {"message": "This is the callback endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
