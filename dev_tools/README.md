# Development Tools

⚠️ **WARNING**: These files are for development and testing purposes only.

## Files in this directory

- `oauth1_server.py` - OAuth 1.0a test server (deprecated)
- `test_oauth.py` - Minimal OAuth test server
- `http_oauth_server.py` - HTTP OAuth test server
- `https_oauth_server.py` - HTTPS OAuth test server
- `https_main_server.py` - HTTPS main server
- `debug_yahoo.py` - Yahoo API debugging script
- `test_yahoo_oauth2.py` - Yahoo OAuth2 testing

## Security Notice

These files contain:
- **SSL verification disabled** - DO NOT use in production
- **Debug endpoints** - Expose internal state
- **Hardcoded redirect URIs** - Not suitable for deployment

## Production OAuth

For production OAuth implementation, see: `api/routes/auth.py`

## Usage

These are for local testing only. Never deploy these to production.