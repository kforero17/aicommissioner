"""Admin routes for managing leagues and running recaps."""
import asyncio
import logging
from typing import Optional, List, Any, Dict, Literal
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from celery.result import AsyncResult

from database.connection import get_db
from models.user import User
from models.league import League, ProviderType
from models.roster import Roster
from models.matchup import Matchup
from models.transaction import Transaction, TransactionType
from models.league_member import LeagueMember, MemberRole
from models.recap import Recap, RecapType, RecapStatus
from api.routes.auth import get_current_user
from schedulers.tasks import sync_specific_league, generate_manual_recap
from ai_text.text_formatter import TextFormatter

router = APIRouter()


def _has_email_recipients(league: League) -> bool:
    """Check if league has email recipients configured."""
    if not league.league_member_emails:
        return False
    try:
        emails = json.loads(league.league_member_emails)
        return bool(isinstance(emails, list) and emails)
    except (json.JSONDecodeError, TypeError):
        return False


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
    commissioner_notes: Optional[str] = None


class LeagueUpdate(BaseModel):
    """Model for updating league settings."""
    name: Optional[str] = None
    groupme_bot_id: Optional[str] = None
    enable_power_rankings: Optional[bool] = None
    enable_waiver_recaps: Optional[bool] = None
    enable_llm_rendering: Optional[bool] = None
    ai_persona_style: Optional[str] = None
    commissioner_notes: Optional[str] = None
    power_rankings_day: Optional[str] = None
    power_rankings_time: Optional[str] = None
    waiver_recap_day: Optional[str] = None
    waiver_recap_time: Optional[str] = None
    enable_email_recaps: Optional[bool] = None
    league_member_emails: Optional[str] = None  # JSON array string
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
    commissioner_notes: Optional[str] = None
    is_active: bool
    last_sync_at: Optional[str]
    # Scheduling fields
    power_rankings_day: str
    power_rankings_time: str
    waiver_recap_day: str
    waiver_recap_time: str
    # Email destination fields
    enable_email_recaps: bool
    has_email_recipients: bool  # True if league_member_emails has entries


class RecapRequest(BaseModel):
    """Model for manual recap requests."""
    league_id: int
    week: Optional[int] = None  # If not provided, uses current week
    preview_only: bool = False  # If true, generate but don't publish
    test_mode: bool = False  # If true, prefix title with [TEST]


# League Hub Response Models

class StandingsEntry(BaseModel):
    """Individual team's standings entry."""
    roster_id: int
    provider_roster_id: str
    team_name: str
    owner_name: Optional[str]
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    power_rank: Optional[int]
    power_rank_change: Optional[int]  # positive = moved up
    standing: int  # 1-indexed position


class MatchupResponse(BaseModel):
    """Individual matchup response with team details."""
    matchup_id: int
    week: int
    team1_name: str
    team1_roster_id: str
    team1_points: Optional[float]
    team1_projected: Optional[float]
    team2_name: Optional[str]
    team2_roster_id: Optional[str]
    team2_points: Optional[float]
    team2_projected: Optional[float]
    is_complete: bool
    winner_name: Optional[str]
    margin: Optional[float]
    is_game_of_week: bool


class TransactionResponse(BaseModel):
    """Individual transaction response."""
    transaction_id: int
    transaction_type: str
    week: int
    team_name: str
    players_added: List[str]
    players_dropped: List[str]
    faab_bid: Optional[int]
    processed_at: Optional[str]


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
        commissioner_notes=league_data.commissioner_notes,
    )

    db.add(new_league)
    await db.flush()  # Get league.id before creating member

    # Create commissioner membership record
    commissioner_member = LeagueMember(
        league_id=new_league.id,
        user_id=current_user.id,
        role=MemberRole.COMMISSIONER,
        joined_at=datetime.utcnow()
    )

    db.add(commissioner_member)
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
        commissioner_notes=new_league.commissioner_notes,
        is_active=new_league.is_active,
        last_sync_at=new_league.last_sync_at.isoformat() if new_league.last_sync_at else None,
        power_rankings_day=new_league.power_rankings_day,
        power_rankings_time=new_league.power_rankings_time,
        waiver_recap_day=new_league.waiver_recap_day,
        waiver_recap_time=new_league.waiver_recap_time,
        enable_email_recaps=new_league.enable_email_recaps,
        has_email_recipients=_has_email_recipients(new_league)
    )


def get_current_fantasy_season() -> int:
    """Get the current fantasy season year.

    Both NFL and NBA seasons start in the fall, so the same
    September cutoff applies to all supported sports.
    """
    today = datetime.now()
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
        current_season = get_current_fantasy_season()
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
            commissioner_notes=league.commissioner_notes,
            is_active=league.is_active,
            last_sync_at=league.last_sync_at.isoformat() if league.last_sync_at else None,
            power_rankings_day=league.power_rankings_day,
            power_rankings_time=league.power_rankings_time,
            waiver_recap_day=league.waiver_recap_day,
            waiver_recap_time=league.waiver_recap_time,
            enable_email_recaps=league.enable_email_recaps,
            has_email_recipients=_has_email_recipients(league)
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
    logger.info(
        "update_league called: league_id=%s, user_id=%s, user_email=%s",
        league_id,
        current_user.id,
        current_user.email,
    )

    result = await db.execute(
        select(League).filter(
            League.id == league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()

    if not league:
        league_exists = await db.execute(
            select(League).filter(League.id == league_id)
        )
        existing_league = league_exists.scalar_one_or_none()
        if existing_league:
            logger.warning(
                "League %s exists but user %s (id=%s) is not owner. Owner is user_id=%s",
                league_id,
                current_user.email,
                current_user.id,
                existing_league.owner_id,
            )
        else:
            logger.warning("League %s does not exist in database", league_id)
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
        commissioner_notes=league.commissioner_notes,
        is_active=league.is_active,
        last_sync_at=league.last_sync_at.isoformat() if league.last_sync_at else None,
        power_rankings_day=league.power_rankings_day,
        power_rankings_time=league.power_rankings_time,
        waiver_recap_day=league.waiver_recap_day,
        waiver_recap_time=league.waiver_recap_time,
        enable_email_recaps=league.enable_email_recaps,
        has_email_recipients=_has_email_recipients(league)
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

    # Dispatch Celery task, fall back to async if broker unavailable
    task_id = None
    try:
        task = sync_specific_league.apply_async(
            args=[league_id, league.provider.value, league.provider_league_id]
        )
        task_id = task.id
    except Exception as e:
        logger.warning("Celery unavailable for sync, running in background: %s", e)
        from ingestors.yahoo_ingestor import ingest_yahoo_leagues
        from ingestors.sleeper_ingestor import ingest_sleeper_league

        if league.provider == ProviderType.YAHOO:
            asyncio.create_task(ingest_yahoo_leagues(league.owner_id))
        else:
            asyncio.create_task(ingest_sleeper_league(league.provider_league_id, league.owner_id))

    return {
        "task_id": task_id,
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
    if task_id in ("null", "None", ""):
        return {"task_id": task_id, "status": "UNKNOWN", "error": "No task ID available"}

    try:
        task_result = AsyncResult(task_id)
        task_status = task_result.status
    except Exception:
        return {"task_id": task_id, "status": "UNKNOWN", "error": "Unable to query task status"}

    response: Dict[str, Any] = {
        "task_id": task_id,
        "status": task_status,
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

    # Dispatch Celery task, fall back to direct execution if broker unavailable
    try:
        task = generate_manual_recap.apply_async(
            args=[league.id, "power_rankings", request.week, request.preview_only, request.test_mode]
        )
        return {"task_id": task.id, "message": "Power rankings recap started", "status": "pending"}
    except Exception as e:
        logger.warning("Celery unavailable for power rankings, running directly: %s", e)
        from schedulers.tasks import _generate_manual_recap
        result = await _generate_manual_recap(
            league.id, "power_rankings", request.week, request.preview_only, request.test_mode
        )
        return {
            "task_id": None,
            "message": "Power rankings recap completed",
            "status": "SUCCESS",
            "result": result,
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

    # Dispatch Celery task, fall back to direct execution if broker unavailable
    try:
        task = generate_manual_recap.apply_async(
            args=[league.id, "waiver_recap", request.week, request.preview_only, request.test_mode]
        )
        return {"task_id": task.id, "message": "Waiver recap started", "status": "pending"}
    except Exception as e:
        logger.warning("Celery unavailable for waiver recap, running directly: %s", e)
        from schedulers.tasks import _generate_manual_recap
        result = await _generate_manual_recap(
            league.id, "waiver_recap", request.week, request.preview_only, request.test_mode
        )
        return {
            "task_id": None,
            "message": "Waiver recap completed",
            "status": "SUCCESS",
            "result": result,
        }


class PublishRequest(BaseModel):
    """Model for publishing pre-generated content."""
    league_id: int
    content: str
    test_mode: bool = False  # If true, prefix title with [TEST]


@router.post("/recaps/publish")
async def publish_recap_content(
    request: PublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Publish pre-generated recap content to configured channels.

    This endpoint takes already-generated content (e.g., from a preview)
    and publishes it to the league's configured channels (GroupMe, email).

    Args:
        request: PublishRequest with league_id, content, and test_mode flag
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Dict containing:
        - status: "success" or "error"
        - message: Status message
        - published_to: List of channels where content was published

    Raises:
        HTTPException: If league not found or user doesn't own the league
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

    # Prefix with [TEST] if test_mode is enabled
    content_to_publish = request.content
    if request.test_mode:
        # Insert [TEST] after first line (header)
        lines = content_to_publish.split('\n', 1)
        if len(lines) > 1:
            content_to_publish = f"{lines[0]}\n[TEST] {lines[1]}"
        else:
            content_to_publish = f"[TEST] {content_to_publish}"

    # Import publishers
    from publishers.groupme_publisher import GroupMePublisher
    from publishers.email_publisher import EmailPublisher
    import json

    published_to = []

    # Publish to GroupMe if configured
    if league.groupme_bot_id:
        try:
            groupme_publisher = GroupMePublisher()
            success = await groupme_publisher.send_long_message(
                league.groupme_bot_id,
                content_to_publish
            )
            await groupme_publisher.close()

            if success:
                published_to.append("GroupMe")
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to publish to GroupMe"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error publishing to GroupMe: {str(e)}"
            )

    # Publish to Email if configured
    if league.enable_email_recaps and league.league_member_emails:
        try:
            emails = json.loads(league.league_member_emails)
            if isinstance(emails, list) and emails:
                email_publisher = EmailPublisher()
                success = await email_publisher.send_recap_email(
                    to_emails=emails,
                    league_name=league.name,
                    week=league.week or 1,
                    recap_text=content_to_publish,
                    recap_type="Recap"
                )

                if success:
                    published_to.append("Email")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to publish to Email"
                    )
        except json.JSONDecodeError:
            pass  # Skip if email configuration is invalid
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error publishing to Email: {str(e)}"
            )

    if not published_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No publishing channels configured for this league"
        )

    return {
        "status": "success",
        "message": f"Content published to {', '.join(published_to)}",
        "published_to": published_to
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


# League Status Models
class LastGeneratedInfo(BaseModel):
    """Information about the most recently generated content."""
    type: Optional[Literal["power_rankings", "waiver_recap"]]
    timestamp: Optional[str]
    week: Optional[int]
    label: Optional[str]


class NextScheduledInfo(BaseModel):
    """Information about the next scheduled content generation."""
    type: Literal["power_rankings", "waiver_recap"]
    timestamp: str
    label: str


class HealthInfo(BaseModel):
    """Health and connection status information."""
    status: Literal["connected", "warning", "error"]
    message: str
    last_sync: Optional[str]


class LeagueStatusResponse(BaseModel):
    """League status response for heartbeat monitoring."""
    last_generated: LastGeneratedInfo
    next_scheduled: Optional[NextScheduledInfo]
    publishing_to: List[str]
    health: HealthInfo


def _get_day_number(day_name: str) -> int:
    """Convert day name to number (0=Monday, 6=Sunday)."""
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    return day_map.get(day_name.lower(), 1)  # Default to Tuesday


def _compute_next_scheduled(
    league: League,
    timezone: str = "America/Chicago"
) -> Optional[NextScheduledInfo]:
    """
    Compute the next scheduled recap based on league settings.

    Args:
        league: League with schedule settings
        timezone: Timezone for scheduling (default: America/Chicago)

    Returns:
        NextScheduledInfo with the next scheduled event or None if no schedules enabled
    """
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)

    schedules = []

    # Add power rankings schedule if enabled
    if league.enable_power_rankings:
        pr_day = _get_day_number(league.power_rankings_day)
        pr_hour, pr_minute = map(int, league.power_rankings_time.split(":"))

        # Find next occurrence of this day/time
        days_ahead = (pr_day - now.weekday() + 7) % 7
        if days_ahead == 0:
            # Same day - check if time has passed
            scheduled_time = now.replace(hour=pr_hour, minute=pr_minute, second=0, microsecond=0)
            if scheduled_time <= now:
                days_ahead = 7  # Next week
            else:
                days_ahead = 0  # Today, later

        next_pr = now + timedelta(days=days_ahead)
        next_pr = next_pr.replace(hour=pr_hour, minute=pr_minute, second=0, microsecond=0)

        schedules.append({
            "type": "power_rankings",
            "timestamp": next_pr,
            "label": "Power Rankings"
        })

    # Add waiver recap schedule if enabled
    if league.enable_waiver_recaps:
        wr_day = _get_day_number(league.waiver_recap_day)
        wr_hour, wr_minute = map(int, league.waiver_recap_time.split(":"))

        # Find next occurrence of this day/time
        days_ahead = (wr_day - now.weekday() + 7) % 7
        if days_ahead == 0:
            # Same day - check if time has passed
            scheduled_time = now.replace(hour=wr_hour, minute=wr_minute, second=0, microsecond=0)
            if scheduled_time <= now:
                days_ahead = 7  # Next week
            else:
                days_ahead = 0  # Today, later

        next_wr = now + timedelta(days=days_ahead)
        next_wr = next_wr.replace(hour=wr_hour, minute=wr_minute, second=0, microsecond=0)

        schedules.append({
            "type": "waiver_recap",
            "timestamp": next_wr,
            "label": "Waivers"
        })

    # Return the earliest scheduled event
    if not schedules:
        return None

    next_event = min(schedules, key=lambda x: x["timestamp"])
    return NextScheduledInfo(
        type=next_event["type"],
        timestamp=next_event["timestamp"].isoformat(),
        label=next_event["label"]
    )


@router.get("/leagues/{league_id}/status", response_model=LeagueStatusResponse)
async def get_league_status(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get league status for heartbeat monitoring.

    Returns information about:
    - Last generated content (power rankings or waiver recap)
    - Next scheduled generation
    - Active publishing channels
    - Connection health status

    Args:
        league_id: League ID
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        LeagueStatusResponse with comprehensive league status

    Raises:
        HTTPException: If league not found or user doesn't own the league
    """
    logger.info(
        "get_league_status called: league_id=%s, user_id=%s, user_email=%s",
        league_id,
        current_user.id,
        current_user.email,
    )

    result = await db.execute(
        select(League).filter(
            League.id == league_id,
            League.owner_id == current_user.id
        )
    )
    league = result.scalar_one_or_none()

    if not league:
        league_exists = await db.execute(
            select(League).filter(League.id == league_id)
        )
        existing_league = league_exists.scalar_one_or_none()
        if existing_league:
            logger.warning(
                "Status check: League %s exists but user %s (id=%s) is not owner. Owner is user_id=%s",
                league_id,
                current_user.email,
                current_user.id,
                existing_league.owner_id,
            )
        else:
            logger.warning("Status check: League %s does not exist in database", league_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    # Determine last generated content
    last_generated = LastGeneratedInfo(
        type=None,
        timestamp=None,
        week=None,
        label=None
    )

    # Compare timestamps to find most recent
    if league.last_power_rankings_at and league.last_waiver_recap_at:
        if league.last_power_rankings_at >= league.last_waiver_recap_at:
            last_generated = LastGeneratedInfo(
                type="power_rankings",
                timestamp=league.last_power_rankings_at.isoformat(),
                week=league.last_power_rankings_week,
                label=f"Week {league.last_power_rankings_week} Power Rankings" if league.last_power_rankings_week else "Power Rankings"
            )
        else:
            last_generated = LastGeneratedInfo(
                type="waiver_recap",
                timestamp=league.last_waiver_recap_at.isoformat(),
                week=league.last_waiver_recap_week,
                label=f"Week {league.last_waiver_recap_week} Waivers" if league.last_waiver_recap_week else "Waivers"
            )
    elif league.last_power_rankings_at:
        last_generated = LastGeneratedInfo(
            type="power_rankings",
            timestamp=league.last_power_rankings_at.isoformat(),
            week=league.last_power_rankings_week,
            label=f"Week {league.last_power_rankings_week} Power Rankings" if league.last_power_rankings_week else "Power Rankings"
        )
    elif league.last_waiver_recap_at:
        last_generated = LastGeneratedInfo(
            type="waiver_recap",
            timestamp=league.last_waiver_recap_at.isoformat(),
            week=league.last_waiver_recap_week,
            label=f"Week {league.last_waiver_recap_week} Waivers" if league.last_waiver_recap_week else "Waivers"
        )

    # Compute next scheduled event
    next_scheduled = _compute_next_scheduled(league)

    # Determine active publishing channels
    publishing_to = []
    if league.groupme_bot_id:
        publishing_to.append("GroupMe")
    if league.enable_email_recaps and league.league_member_emails:
        publishing_to.append("Email")

    # Determine health status
    health_status = "connected"
    health_message = f"Connected to {league.provider.value.title()}"

    if not league.is_active:
        health_status = "error"
        health_message = "League is inactive"
    elif league.last_sync_at:
        time_since_sync = datetime.utcnow() - league.last_sync_at.replace(tzinfo=None)
        if time_since_sync > timedelta(hours=24):
            health_status = "warning"
            health_message = f"Connected to {league.provider.value.title()} (last sync {time_since_sync.days}d ago)"
    else:
        health_status = "warning"
        health_message = f"Connected to {league.provider.value.title()} (never synced)"

    health = HealthInfo(
        status=health_status,
        message=health_message,
        last_sync=league.last_sync_at.isoformat() if league.last_sync_at else None
    )

    return LeagueStatusResponse(
        last_generated=last_generated,
        next_scheduled=next_scheduled,
        publishing_to=publishing_to,
        health=health
    )


# League Hub Endpoints

@router.get("/leagues/{league_id}/standings", response_model=List[StandingsEntry])
async def get_league_standings(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get league standings sorted by wins and points.

    Returns all rosters in the league sorted by standings (wins descending,
    then points_for descending). Includes power ranking changes.

    Args:
        league_id: League ID
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        List of StandingsEntry objects with team standings

    Raises:
        HTTPException: If league not found or user doesn't have access
    """
    # Verify league access (owner or member)
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    # Check if user is owner or member
    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    # Get all rosters for this league
    result = await db.execute(
        select(Roster)
        .filter(Roster.league_id == league_id)
        .order_by(Roster.wins.desc(), Roster.points_for.desc())
    )
    rosters = result.scalars().all()

    # Build standings response
    standings = []
    for idx, roster in enumerate(rosters, start=1):
        # Calculate power rank change (positive = moved up)
        power_rank_change = None
        if roster.power_rank is not None and roster.power_rank_previous is not None:
            power_rank_change = roster.power_rank_previous - roster.power_rank

        standings.append(StandingsEntry(
            roster_id=roster.id,
            provider_roster_id=roster.provider_roster_id,
            team_name=roster.team_name or "Unknown Team",
            owner_name=roster.owner_name,
            wins=roster.wins,
            losses=roster.losses,
            ties=roster.ties,
            points_for=roster.points_for,
            points_against=roster.points_against,
            power_rank=roster.power_rank,
            power_rank_change=power_rank_change,
            standing=idx
        ))

    return standings


@router.get("/leagues/{league_id}/matchups", response_model=List[MatchupResponse])
async def get_league_matchups(
    league_id: int,
    week: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get matchups for a specific week.

    Returns all matchups for the specified week with team names resolved.
    If week not provided, uses the league's current week. Determines the
    "game of the week" as the closest matchup if complete, or highest
    combined projected if not.

    Args:
        league_id: League ID
        week: Optional week number (defaults to league's current week)
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        List of MatchupResponse objects with matchup details

    Raises:
        HTTPException: If league not found or user doesn't have access
    """
    # Verify league access (owner or member)
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    # Check if user is owner or member
    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    # Use league's current week if not specified
    target_week = week or league.week
    if target_week is None:
        return []  # No week available

    # Get matchups for the week
    result = await db.execute(
        select(Matchup)
        .filter(
            Matchup.league_id == league_id,
            Matchup.week == target_week
        )
    )
    matchups = result.scalars().all()

    if not matchups:
        return []

    # Get all rosters to map roster_id to team names
    result = await db.execute(
        select(Roster).filter(Roster.league_id == league_id)
    )
    rosters = result.scalars().all()
    roster_map = {r.provider_roster_id: r for r in rosters}

    # Determine game of the week
    game_of_week_id = None

    # Check for completed matchups with smallest margin
    completed_matchups = [m for m in matchups if m.is_complete and m.margin_of_victory is not None]
    if completed_matchups:
        game_of_week = min(completed_matchups, key=lambda m: m.margin_of_victory)
        game_of_week_id = game_of_week.id
    else:
        # Use highest combined projected for incomplete matchups
        matchups_with_projected = [
            m for m in matchups
            if m.team1_projected is not None and m.team2_projected is not None
        ]
        if matchups_with_projected:
            game_of_week = max(
                matchups_with_projected,
                key=lambda m: m.team1_projected + m.team2_projected
            )
            game_of_week_id = game_of_week.id

    # Build matchup responses
    matchup_responses = []
    for matchup in matchups:
        # Get team names
        team1 = roster_map.get(matchup.team1_roster_id)
        team1_name = team1.team_name if team1 else "Unknown Team"

        team2_name = None
        if matchup.team2_roster_id:
            team2 = roster_map.get(matchup.team2_roster_id)
            team2_name = team2.team_name if team2 else "Unknown Team"

        # Determine winner name
        winner_name = None
        if matchup.winner_roster_id:
            winner = roster_map.get(matchup.winner_roster_id)
            winner_name = winner.team_name if winner else "Unknown Team"

        matchup_responses.append(MatchupResponse(
            matchup_id=matchup.id,
            week=matchup.week,
            team1_name=team1_name,
            team1_roster_id=matchup.team1_roster_id,
            team1_points=matchup.team1_points,
            team1_projected=matchup.team1_projected,
            team2_name=team2_name,
            team2_roster_id=matchup.team2_roster_id,
            team2_points=matchup.team2_points,
            team2_projected=matchup.team2_projected,
            is_complete=matchup.is_complete,
            winner_name=winner_name,
            margin=matchup.margin_of_victory,
            is_game_of_week=(matchup.id == game_of_week_id)
        ))

    return matchup_responses


@router.get("/leagues/{league_id}/transactions", response_model=List[TransactionResponse])
async def get_league_transactions(
    league_id: int,
    week: Optional[int] = None,
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get league transactions, optionally filtered by week and type.

    Returns transactions with team names resolved and player data parsed.
    Can be filtered by week and/or transaction type.

    Args:
        league_id: League ID
        week: Optional week number to filter transactions
        type: Optional transaction type (add, drop, trade, waiver, free_agent)
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        List of TransactionResponse objects with transaction details

    Raises:
        HTTPException: If league not found or user doesn't have access
    """
    # Verify league access (owner or member)
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    # Check if user is owner or member
    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    # Build query with filters
    query = select(Transaction).filter(Transaction.league_id == league_id)

    if week is not None:
        query = query.filter(Transaction.week == week)

    if type is not None:
        try:
            transaction_type = TransactionType(type.lower())
            query = query.filter(Transaction.transaction_type == transaction_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transaction type: {type}. Valid types: add, drop, trade, waiver, free_agent"
            )

    query = query.order_by(Transaction.processed_at.desc())

    result = await db.execute(query)
    transactions = result.scalars().all()

    if not transactions:
        return []

    # Get all rosters to map roster_id to team names
    result = await db.execute(
        select(Roster).filter(Roster.league_id == league_id)
    )
    rosters = result.scalars().all()
    roster_map = {r.provider_roster_id: r for r in rosters}

    # Build transaction responses
    transaction_responses = []
    for txn in transactions:
        # Get team name
        roster = roster_map.get(txn.roster_id)
        team_name = roster.team_name if roster else "Unknown Team"

        # Parse player data from JSON
        players_added = []
        if txn.players_added:
            try:
                players_data = json.loads(txn.players_added)
                if isinstance(players_data, list):
                    # Extract player names or IDs
                    for player in players_data:
                        if isinstance(player, dict):
                            # Try to get name, fall back to player_id
                            player_name = player.get("name") or player.get("player_id") or "Unknown Player"
                            players_added.append(player_name)
                        elif isinstance(player, str):
                            players_added.append(player)
            except (json.JSONDecodeError, TypeError):
                players_added = []

        players_dropped = []
        if txn.players_dropped:
            try:
                players_data = json.loads(txn.players_dropped)
                if isinstance(players_data, list):
                    # Extract player names or IDs
                    for player in players_data:
                        if isinstance(player, dict):
                            # Try to get name, fall back to player_id
                            player_name = player.get("name") or player.get("player_id") or "Unknown Player"
                            players_dropped.append(player_name)
                        elif isinstance(player, str):
                            players_dropped.append(player)
            except (json.JSONDecodeError, TypeError):
                players_dropped = []

        transaction_responses.append(TransactionResponse(
            transaction_id=txn.id,
            transaction_type=txn.transaction_type.value,
            week=txn.week,
            team_name=team_name,
            players_added=players_added,
            players_dropped=players_dropped,
            faab_bid=txn.faab_bid,
            processed_at=txn.processed_at.isoformat() if txn.processed_at else None
        ))

    return transaction_responses


# Recap Content Endpoints

class RecapResponse(BaseModel):
    """Response model for a single recap."""
    id: int
    recap_type: str
    week: int
    season: int
    title: str
    content: str
    status: str
    rendering_mode: Optional[str] = None
    ai_persona: Optional[str] = None
    published_at: Optional[str] = None
    created_at: str
    # Observability fields
    generation_metadata: Optional[dict] = None
    error_message: Optional[str] = None
    llm_model: Optional[str] = None
    llm_latency_ms: Optional[int] = None


class RecapListResponse(BaseModel):
    """Response model for list of recaps."""
    recaps: List[RecapResponse]
    total: int
    has_more: bool


def _recap_to_response(recap: Recap) -> RecapResponse:
    """Convert a Recap model to RecapResponse, parsing generation_metadata JSON."""
    metadata_dict = None
    if recap.generation_metadata:
        try:
            metadata_dict = json.loads(recap.generation_metadata)
        except (json.JSONDecodeError, TypeError):
            pass

    return RecapResponse(
        id=recap.id,
        recap_type=recap.recap_type.value,
        week=recap.week,
        season=recap.season,
        title=recap.title,
        content=recap.content,
        status=recap.status.value,
        rendering_mode=recap.rendering_mode,
        ai_persona=recap.ai_persona,
        published_at=recap.published_at.isoformat() if recap.published_at else None,
        created_at=recap.created_at.isoformat(),
        generation_metadata=metadata_dict,
        error_message=recap.error_message,
        llm_model=recap.llm_model,
        llm_latency_ms=recap.llm_latency_ms,
    )


@router.get("/leagues/{league_id}/recaps", response_model=RecapListResponse)
async def get_league_recaps(
    league_id: int,
    week: Optional[int] = None,
    recap_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recaps for a league with optional filtering.

    Args:
        league_id: League ID
        week: Filter by week number
        recap_type: Filter by type (power_rankings, waiver_recap, weekly_recap)
        status_filter: Filter by status (draft, published)
        limit: Max results to return (default 20)
        offset: Number of results to skip for pagination
        current_user: Authenticated user
        db: Database session

    Returns:
        RecapListResponse with list of recaps and pagination info
    """
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    query = select(Recap).filter(Recap.league_id == league_id)

    if week is not None:
        query = query.filter(Recap.week == week)

    if recap_type:
        try:
            rt = RecapType(recap_type)
            query = query.filter(Recap.recap_type == rt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid recap_type: {recap_type}"
            )

    if status_filter:
        try:
            rs = RecapStatus(status_filter)
            query = query.filter(Recap.status == rs)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    count_result = await db.execute(
        select(Recap.id).filter(Recap.league_id == league_id)
    )
    total = len(count_result.all())

    query = query.order_by(Recap.created_at.desc()).offset(offset).limit(limit + 1)
    result = await db.execute(query)
    recaps = result.scalars().all()

    has_more = len(recaps) > limit
    recaps = recaps[:limit]

    recap_responses = [_recap_to_response(recap) for recap in recaps]

    return RecapListResponse(
        recaps=recap_responses,
        total=total,
        has_more=has_more
    )


@router.get("/leagues/{league_id}/recaps/latest", response_model=List[RecapResponse])
async def get_latest_recaps(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the latest recap of each type for the league.

    Returns the most recent power_rankings, waiver_recap, and weekly_recap
    (one of each type if available).

    Args:
        league_id: League ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of RecapResponse with latest recap of each type
    """
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    latest_recaps = []
    for recap_type in RecapType:
        result = await db.execute(
            select(Recap)
            .filter(
                Recap.league_id == league_id,
                Recap.recap_type == recap_type,
                Recap.status == RecapStatus.PUBLISHED
            )
            .order_by(Recap.created_at.desc())
            .limit(1)
        )
        recap = result.scalar_one_or_none()
        if recap:
            latest_recaps.append(_recap_to_response(recap))

    return latest_recaps


@router.get("/leagues/{league_id}/recaps/{recap_id}", response_model=RecapResponse)
async def get_recap_by_id(
    league_id: int,
    recap_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a single recap by ID."""
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    result = await db.execute(
        select(Recap).filter(
            Recap.id == recap_id,
            Recap.league_id == league_id
        )
    )
    recap = result.scalar_one_or_none()

    if not recap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recap not found"
        )

    return _recap_to_response(recap)


class RetryPublishResponse(BaseModel):
    """Response for retry publish operation."""
    success: bool
    message: str
    recap_id: int
    new_status: str


@router.post("/recaps/{recap_id}/retry-publish", response_model=RetryPublishResponse)
async def retry_publish_recap(
    recap_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry publishing a failed recap.

    This endpoint allows commissioners to retry publishing a recap that
    previously failed to publish. Works for recaps in DRAFT or PUBLISH_FAILED
    status that have content generated.

    This is useful when:
    - GroupMe was temporarily down
    - Email service had issues
    - Network problems occurred during publishing

    Args:
        recap_id: ID of the recap to retry publishing
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        RetryPublishResponse with success status and new recap status

    Raises:
        HTTPException: If recap not found, user doesn't have access,
                      or recap is not in a retryable state
    """
    # Get the recap first
    result = await db.execute(
        select(Recap).filter(Recap.id == recap_id)
    )
    recap = result.scalar_one_or_none()

    if not recap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recap not found"
        )

    # Check user has access to the league
    result = await db.execute(
        select(League).filter(League.id == recap.league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    is_owner = league.owner_id == current_user.id
    if not is_owner:
        result = await db.execute(
            select(LeagueMember).filter(
                LeagueMember.league_id == recap.league_id,
                LeagueMember.user_id == current_user.id,
                LeagueMember.joined_at.isnot(None)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this league"
            )

    # Use RecapService to retry publishing
    from services.recap_service import RecapService

    service = RecapService()
    try:
        success = await service.retry_publish(recap_id)

        # Refresh the recap to get updated status
        await db.refresh(recap)

        if success:
            return RetryPublishResponse(
                success=True,
                message="Recap successfully published",
                recap_id=recap_id,
                new_status=recap.status.value
            )
        else:
            return RetryPublishResponse(
                success=False,
                message=f"Publishing failed: {recap.error_message or 'Unknown error'}",
                recap_id=recap_id,
                new_status=recap.status.value
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    finally:
        await service.close()
