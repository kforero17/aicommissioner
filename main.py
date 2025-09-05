"""Main FastAPI application entry point."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import auth, admin, webhooks
from database.connection import init_db


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Commissioner",
        description="Fantasy Sports AI Agent SaaS Platform",
        version="1.0.0",
        debug=settings.debug,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["authentication"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    
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
