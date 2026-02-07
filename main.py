"""Main FastAPI application entry point."""
import os
import ssl
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from api.routes import auth, admin, webhooks, members
from database.connection import init_db

# Disable SSL verification in debug mode (corporate network workaround)
if settings.debug:
    import warnings

    # Suppress SSL warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass

    # Set environment variables to disable SSL verification
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['SSL_CERT_FILE'] = ''

    # Override SSL context creation globally
    ssl._create_default_https_context = ssl._create_unverified_context

    print("⚠️  SSL verification disabled for development (DEBUG=true)")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Commissioner",
        description="Fantasy Sports AI Agent SaaS Platform",
        version="1.0.0",
        debug=settings.debug,
    )
    
    # Session middleware (required for OAuth)
    # Configure for development with Cloudflare Tunnel
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="session",
        max_age=3600,  # 1 hour
        same_site="lax",
        https_only=False  # Allow HTTP in development
    )
    
    # CORS middleware - use specific origins even in development
    allowed_origins = [
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3003",
        "https://gate-penny-arrivals-andreas.trycloudflare.com",  # Cloudflare Tunnel
    ] if settings.debug else [settings.frontend_url]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["authentication"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    app.include_router(members.router, tags=["members"])
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup."""
        await init_db()
    
    @app.get("/")
    async def root():
        """Health check endpoint."""
        return {"message": "AI Commissioner API is running"}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
