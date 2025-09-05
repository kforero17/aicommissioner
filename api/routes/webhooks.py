"""Webhook routes for external integrations."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, Any, Optional

from database.connection import get_db
from models.league import League, ProviderType
from services.recap_service import run_power_rankings, run_waiver_recap
from ingestors.sleeper_ingestor import ingest_sleeper_league

router = APIRouter()


class SleeperWebhookPayload(BaseModel):
    """Sleeper webhook payload model."""
    type: str  # "waiver", "trade", "transaction", etc.
    league_id: str
    week: Optional[int] = None
    transaction_id: Optional[str] = None
    roster_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class GenericWebhookPayload(BaseModel):
    """Generic webhook payload for other services."""
    event_type: str
    league_id: str
    provider: str
    data: Dict[str, Any]


@router.post("/sleeper/{league_id}")
async def sleeper_webhook(
    league_id: str,
    payload: SleeperWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle Sleeper webhooks for real-time updates."""
    # Verify the league exists in our system
    result = await db.execute(
        select(League).filter(
            League.provider == ProviderType.SLEEPER,
            League.provider_league_id == league_id,
            League.is_active == True
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or inactive"
        )
    
    # Handle different webhook types
    if payload.type == "waiver":
        # Waiver processing completed - trigger waiver recap if enabled
        if league.enable_waiver_recaps:
            background_tasks.add_task(run_waiver_recap, league.id, payload.week)
        
        # Also sync league data to get latest transactions
        background_tasks.add_task(ingest_sleeper_league, league_id)
    
    elif payload.type == "transaction":
        # Any transaction occurred - sync data
        background_tasks.add_task(ingest_sleeper_league, league_id)
    
    elif payload.type == "trade":
        # Trade occurred - sync data and potentially trigger notifications
        background_tasks.add_task(ingest_sleeper_league, league_id)
    
    elif payload.type == "week_start":
        # New week started - sync data and potentially trigger power rankings
        background_tasks.add_task(ingest_sleeper_league, league_id)
        if league.enable_power_rankings and payload.week and payload.week > 1:
            # Run power rankings for the previous week
            background_tasks.add_task(run_power_rankings, league.id, payload.week - 1)
    
    elif payload.type == "matchup_score_update":
        # Scores updated - sync matchup data
        background_tasks.add_task(ingest_sleeper_league, league_id)
    
    return {"status": "success", "message": f"Webhook processed for league {league_id}"}


@router.post("/yahoo/{league_id}")
async def yahoo_webhook(
    league_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle Yahoo webhooks (if Yahoo supports them in the future)."""
    # Note: Yahoo doesn't currently support webhooks, but this is here for future compatibility
    body = await request.body()
    
    # Verify the league exists in our system
    result = await db.execute(
        select(League).filter(
            League.provider == ProviderType.YAHOO,
            League.provider_league_id == league_id,
            League.is_active == True
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or inactive"
        )
    
    # For now, just acknowledge the webhook
    # In the future, parse the payload and trigger appropriate actions
    
    return {"status": "success", "message": f"Yahoo webhook received for league {league_id}"}


@router.post("/generic")
async def generic_webhook(
    payload: GenericWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle generic webhooks from external services."""
    provider_type = None
    if payload.provider.lower() == "sleeper":
        provider_type = ProviderType.SLEEPER
    elif payload.provider.lower() == "yahoo":
        provider_type = ProviderType.YAHOO
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {payload.provider}"
        )
    
    # Verify the league exists in our system
    result = await db.execute(
        select(League).filter(
            League.provider == provider_type,
            League.provider_league_id == payload.league_id,
            League.is_active == True
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or inactive"
        )
    
    # Handle different event types
    if payload.event_type == "data_sync_required":
        # External service requesting data sync
        if provider_type == ProviderType.SLEEPER:
            background_tasks.add_task(ingest_sleeper_league, payload.league_id)
        # Add Yahoo sync logic when available
    
    elif payload.event_type == "generate_recap":
        # External request to generate recap
        recap_type = payload.data.get("recap_type", "power_rankings")
        week = payload.data.get("week")
        
        if recap_type == "power_rankings" and league.enable_power_rankings:
            background_tasks.add_task(run_power_rankings, league.id, week)
        elif recap_type == "waiver_recap" and league.enable_waiver_recaps:
            background_tasks.add_task(run_waiver_recap, league.id, week)
    
    return {"status": "success", "message": "Generic webhook processed"}


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhook services."""
    return {"status": "healthy", "service": "webhooks"}


@router.post("/test/{league_id}")
async def test_webhook(
    league_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Test webhook endpoint for development and debugging."""
    # Find any league with the given ID for testing
    result = await db.execute(
        select(League).filter(
            League.provider_league_id == league_id,
            League.is_active == True
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or inactive"
        )
    
    # Trigger a test sync
    if league.provider == ProviderType.SLEEPER:
        background_tasks.add_task(ingest_sleeper_league, league_id)
    
    return {
        "status": "success", 
        "message": f"Test webhook triggered for league {league_id}",
        "provider": league.provider,
        "league_name": league.name
    }
