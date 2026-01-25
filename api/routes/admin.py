"""Admin routes for managing leagues and running recaps."""
from typing import Optional, List, Any, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from celery.result import AsyncResult

from database.connection import get_db
from models.user import User
from models.league import League, ProviderType
from api.routes.auth import get_current_user
from schedulers.tasks import sync_specific_league, generate_manual_recap
from ai_text.text_formatter import TextFormatter

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


def get_current_nfl_season() -> int:
    """Get the current NFL season year based on today's date."""
    today = datetime.now()
    # NFL season starts in September, so if we're before September,
    # the current season is the previous year
    if today.month < 9:
        return today.year - 1
    return today.year


@router.get("/leagues", response_model=List[LeagueResponse])
async def get_user_leagues(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    all_seasons: bool = False
):
    """Get leagues for the current user.

    By default, only returns leagues from the current NFL season.
    Set all_seasons=true to return all historical leagues.
    """
    query = select(League).filter(League.owner_id == current_user.id)

    if not all_seasons:
        current_season = get_current_nfl_season()
        query = query.filter(League.season >= current_season)

    query = query.order_by(League.season.desc(), League.name)

    result = await db.execute(query)
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
    week: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually sync league data from provider.

    Dispatches a Celery task to sync league data and returns the task ID
    for polling the sync progress.

    Args:
        league_id: ID of the league to sync
        week: Optional week number (currently unused, reserved for future use)
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Dict containing:
        - task_id: Celery task ID for polling status
        - message: Status message
        - status: Initial task status ("pending")

    Raises:
        HTTPException: If league not found or user doesn't own the league
    """
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

    # Dispatch Celery task to sync the league
    task = sync_specific_league.apply_async(
        args=[league_id, league.provider.value, league.provider_league_id]
    )

    return {
        "task_id": task.id,
        "message": "League sync started",
        "status": "pending"
    }


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Poll task status for a Celery task.

    Returns current status and result/error information for tracking
    async task progress (sync operations, recap generation, etc.).

    Args:
        task_id: Celery task ID returned from async operations
        current_user: Authenticated user from dependency injection

    Returns:
        Dict containing:
        - task_id: The task identifier
        - status: Task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
        - result: Task result if SUCCESS
        - error: Error message if FAILURE
        - progress: Progress metadata if STARTED

    Example responses:
        Pending: {"task_id": "abc-123", "status": "PENDING"}
        Success: {"task_id": "abc-123", "status": "SUCCESS", "result": {...}}
        Failure: {"task_id": "abc-123", "status": "FAILURE", "error": "..."}
    """
    task_result = AsyncResult(task_id)

    response: Dict[str, Any] = {
        "task_id": task_id,
        "status": task_result.status,
    }

    if task_result.successful():
        response["result"] = task_result.result
    elif task_result.failed():
        # Get error information
        error_info = task_result.info
        if isinstance(error_info, Exception):
            response["error"] = str(error_info)
        else:
            response["error"] = str(error_info) if error_info else "Task failed"
    elif task_result.status == "STARTED":
        # Include progress information if available
        response["progress"] = task_result.info if task_result.info else {}

    return response


@router.post("/recaps/power-rankings")
async def run_manual_power_rankings(
    request: RecapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually run power rankings recap for a league.

    Dispatches a Celery task to generate power rankings and returns
    the task ID for polling the generation progress.

    Args:
        request: RecapRequest containing league_id and optional week
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Dict containing:
        - task_id: Celery task ID for polling status
        - message: Status message
        - status: Initial task status ("pending")

    Raises:
        HTTPException: If league not found, user doesn't own league,
                      or power rankings are disabled
    """
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

    # Dispatch Celery task to generate power rankings
    task = generate_manual_recap.apply_async(
        args=[league.id, "power_rankings", request.week]
    )

    return {
        "task_id": task.id,
        "message": "Power rankings recap started",
        "status": "pending"
    }


@router.post("/recaps/waiver-recap")
async def run_manual_waiver_recap(
    request: RecapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually run waiver recap for a league.

    Dispatches a Celery task to generate waiver recap and returns
    the task ID for polling the generation progress.

    Args:
        request: RecapRequest containing league_id and optional week
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Dict containing:
        - task_id: Celery task ID for polling status
        - message: Status message
        - status: Initial task status ("pending")

    Raises:
        HTTPException: If league not found, user doesn't own league,
                      or waiver recaps are disabled
    """
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

    # Dispatch Celery task to generate waiver recap
    task = generate_manual_recap.apply_async(
        args=[league.id, "waiver_recap", request.week]
    )

    return {
        "task_id": task.id,
        "message": "Waiver recap started",
        "status": "pending"
    }


@router.get("/monitoring/llm-circuit-status")
async def get_llm_circuit_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get LLM circuit breaker status for monitoring.

    Returns the current state of circuit breakers for all LLM providers,
    including failure counts, state, and when circuits were opened.

    Useful for:
    - Monitoring dashboards
    - Alerting on circuit opens
    - Debugging LLM issues
    - Understanding service health
    """
    # Create a formatter instance to access circuit breaker status
    formatter = TextFormatter()
    status = formatter.get_circuit_status()

    return {
        "status": "ok",
        "circuit_breakers": status,
        "timestamp": datetime.utcnow().isoformat()
    }
