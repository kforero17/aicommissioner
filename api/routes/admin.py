"""Admin routes for managing leagues and running recaps."""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database.connection import get_db
from models.user import User
from models.league import League, ProviderType
from api.routes.auth import get_current_user
from services.recap_service import run_power_rankings, run_waiver_recap
from ingestors.sleeper_ingestor import ingest_sleeper_league
from ingestors.yahoo_ingestor import ingest_yahoo_leagues

router = APIRouter()


class LeagueCreate(BaseModel):
    """Model for creating a new league."""
    provider: ProviderType
    provider_league_id: str
    name: str
    season: int
    groupme_bot_id: Optional[str] = None
    enable_power_rankings: bool = True
    enable_waiver_recaps: bool = True
    enable_llm_rendering: bool = False
    ai_persona_style: Optional[str] = None


class LeagueUpdate(BaseModel):
    """Model for updating league settings."""
    name: Optional[str] = None
    groupme_bot_id: Optional[str] = None
    enable_power_rankings: Optional[bool] = None
    enable_waiver_recaps: Optional[bool] = None
    enable_llm_rendering: Optional[bool] = None
    ai_persona_style: Optional[str] = None
    power_rankings_day: Optional[str] = None
    power_rankings_time: Optional[str] = None
    waiver_recap_day: Optional[str] = None
    waiver_recap_time: Optional[str] = None
    is_active: Optional[bool] = None


class LeagueResponse(BaseModel):
    """League response model."""
    id: int
    provider: ProviderType
    provider_league_id: str
    name: str
    season: int
    week: Optional[int]
    num_teams: int
    groupme_bot_id: Optional[str]
    enable_power_rankings: bool
    enable_waiver_recaps: bool
    enable_llm_rendering: bool
    ai_persona_style: Optional[str]
    is_active: bool
    last_sync_at: Optional[str]


class RecapRequest(BaseModel):
    """Model for manual recap requests."""
    league_id: int
    week: Optional[int] = None  # If not provided, uses current week


@router.post("/leagues", response_model=LeagueResponse)
async def create_league(
    league_data: LeagueCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new league for the current user."""
    # Check if league already exists for this user
    result = await db.execute(
        select(League).filter(
            League.owner_id == current_user.id,
            League.provider == league_data.provider,
            League.provider_league_id == league_data.provider_league_id,
            League.season == league_data.season
        )
    )
    existing_league = result.scalar_one_or_none()
    
    if existing_league:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="League already exists for this user"
        )
    
    # Create new league
    new_league = League(
        owner_id=current_user.id,
        provider=league_data.provider,
        provider_league_id=league_data.provider_league_id,
        name=league_data.name,
        season=league_data.season,
        num_teams=0,  # Will be updated during ingestion
        groupme_bot_id=league_data.groupme_bot_id,
        enable_power_rankings=league_data.enable_power_rankings,
        enable_waiver_recaps=league_data.enable_waiver_recaps,
        enable_llm_rendering=league_data.enable_llm_rendering,
        ai_persona_style=league_data.ai_persona_style,
    )
    
    db.add(new_league)
    await db.commit()
    await db.refresh(new_league)
    
    return LeagueResponse(
        id=new_league.id,
        provider=new_league.provider,
        provider_league_id=new_league.provider_league_id,
        name=new_league.name,
        season=new_league.season,
        week=new_league.week,
        num_teams=new_league.num_teams,
        groupme_bot_id=new_league.groupme_bot_id,
        enable_power_rankings=new_league.enable_power_rankings,
        enable_waiver_recaps=new_league.enable_waiver_recaps,
        enable_llm_rendering=new_league.enable_llm_rendering,
        ai_persona_style=new_league.ai_persona_style,
        is_active=new_league.is_active,
        last_sync_at=new_league.last_sync_at.isoformat() if new_league.last_sync_at else None
    )


@router.get("/leagues", response_model=List[LeagueResponse])
async def get_user_leagues(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all leagues for the current user."""
    result = await db.execute(
        select(League).filter(League.owner_id == current_user.id)
    )
    leagues = result.scalars().all()
    
    return [
        LeagueResponse(
            id=league.id,
            provider=league.provider,
            provider_league_id=league.provider_league_id,
            name=league.name,
            season=league.season,
            week=league.week,
            num_teams=league.num_teams,
            groupme_bot_id=league.groupme_bot_id,
            enable_power_rankings=league.enable_power_rankings,
            enable_waiver_recaps=league.enable_waiver_recaps,
            enable_llm_rendering=league.enable_llm_rendering,
            ai_persona_style=league.ai_persona_style,
            is_active=league.is_active,
            last_sync_at=league.last_sync_at.isoformat() if league.last_sync_at else None
        )
        for league in leagues
    ]


@router.patch("/leagues/{league_id}", response_model=LeagueResponse)
async def update_league(
    league_id: int,
    league_data: LeagueUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update league settings."""
    result = await db.execute(
        select(League).filter(
            League.id == league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    # Update fields if provided
    update_data = league_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(league, field, value)
    
    await db.commit()
    await db.refresh(league)
    
    return LeagueResponse(
        id=league.id,
        provider=league.provider,
        provider_league_id=league.provider_league_id,
        name=league.name,
        season=league.season,
        week=league.week,
        num_teams=league.num_teams,
        groupme_bot_id=league.groupme_bot_id,
        enable_power_rankings=league.enable_power_rankings,
        enable_waiver_recaps=league.enable_waiver_recaps,
        enable_llm_rendering=league.enable_llm_rendering,
        ai_persona_style=league.ai_persona_style,
        is_active=league.is_active,
        last_sync_at=league.last_sync_at.isoformat() if league.last_sync_at else None
    )


@router.delete("/leagues/{league_id}")
async def delete_league(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a league."""
    result = await db.execute(
        select(League).filter(
            League.id == league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    await db.delete(league)
    await db.commit()
    
    return {"message": "League deleted successfully"}


@router.post("/leagues/{league_id}/sync")
async def sync_league_data(
    league_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually sync league data from provider."""
    result = await db.execute(
        select(League).filter(
            League.id == league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    # Add background task to sync data
    if league.provider == ProviderType.SLEEPER:
        background_tasks.add_task(ingest_sleeper_league, league.provider_league_id)
    elif league.provider == ProviderType.YAHOO:
        background_tasks.add_task(ingest_yahoo_leagues, current_user.id)
    
    return {"message": "League sync started"}


@router.post("/recaps/power-rankings")
async def run_manual_power_rankings(
    request: RecapRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually run power rankings recap for a league."""
    result = await db.execute(
        select(League).filter(
            League.id == request.league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    if not league.enable_power_rankings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power rankings are disabled for this league"
        )
    
    # Add background task to run power rankings
    background_tasks.add_task(run_power_rankings, league.id, request.week)
    
    return {"message": "Power rankings recap started"}


@router.post("/recaps/waiver-recap")
async def run_manual_waiver_recap(
    request: RecapRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually run waiver recap for a league."""
    result = await db.execute(
        select(League).filter(
            League.id == request.league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    if not league.enable_waiver_recaps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Waiver recaps are disabled for this league"
        )
    
    # Add background task to run waiver recap
    background_tasks.add_task(run_waiver_recap, league.id, request.week)
    
    return {"message": "Waiver recap started"}
