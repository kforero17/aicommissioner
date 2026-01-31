"""League membership routes for invite-based access control."""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel

from database.connection import get_db
from models.user import User
from models.league import League
from models.league_member import LeagueMember, MemberRole
from api.routes.auth import get_current_user

router = APIRouter(prefix="/members", tags=["members"])


# ==================== Pydantic Models ====================

class InviteResponse(BaseModel):
    """Response model for invite creation."""
    invite_url: str
    token: str
    expires_in_days: int = 7


class InviteValidation(BaseModel):
    """Response model for invite validation."""
    valid: bool
    league_name: Optional[str] = None
    league_id: Optional[int] = None
    invited_by: Optional[str] = None
    error: Optional[str] = None


class MemberResponse(BaseModel):
    """Response model for league member."""
    id: int
    user_id: Optional[int]
    email: Optional[str]
    role: str
    joined_at: Optional[str]
    invited_at: Optional[str]
    preferences: Optional[Dict[str, Any]]


class MemberPreferences(BaseModel):
    """Model for member preferences update."""
    mute_waivers: Optional[bool] = None
    mute_power_rankings: Optional[bool] = None
    mute_weekly_recaps: Optional[bool] = None
    email_digest: Optional[str] = None  # "none", "daily", "weekly"


class AccessCheck(BaseModel):
    """Response model for access check."""
    has_access: bool
    role: Optional[str] = None
    is_owner: bool = False
    preferences: Optional[Dict[str, Any]] = None


# ==================== Helper Functions ====================

def _parse_preferences(prefs_json: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse preferences JSON string to dict."""
    if not prefs_json:
        return None
    try:
        return json.loads(prefs_json)
    except (json.JSONDecodeError, TypeError):
        return None


async def _get_league_with_access_check(
    league_id: int,
    user_id: int,
    db: AsyncSession,
    require_owner: bool = False
) -> League:
    """
    Get league and verify user has access.

    Args:
        league_id: League ID to check
        user_id: User ID to check access for
        db: Database session
        require_owner: If True, require user to be the league owner

    Returns:
        League object if access granted

    Raises:
        HTTPException: If league not found or access denied
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

    if require_owner:
        if league.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only league owner can perform this action"
            )
    else:
        # Check if user is owner or member
        is_owner = league.owner_id == user_id
        if not is_owner:
            # Check membership
            result = await db.execute(
                select(LeagueMember).filter(
                    LeagueMember.league_id == league_id,
                    LeagueMember.user_id == user_id,
                    LeagueMember.joined_at.isnot(None)
                )
            )
            member = result.scalar_one_or_none()
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this league"
                )

    return league


# ==================== Admin Endpoints ====================

@router.post("/admin/leagues/{league_id}/invite", response_model=InviteResponse)
async def create_league_invite(
    league_id: int,
    invite_email: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create an invite link for a league (owner only).

    Commissioners can generate invite links to share with other users.
    The invite_email parameter is optional and can be used to track
    which email address was invited.

    Args:
        league_id: League ID to create invite for
        invite_email: Optional email address of invitee
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        InviteResponse with invite URL and token

    Raises:
        HTTPException: If league not found or user is not the owner
    """
    # Verify league ownership
    league = await _get_league_with_access_check(
        league_id, current_user.id, db, require_owner=True
    )

    # Generate invite token
    invite_token = LeagueMember.generate_invite_token()

    # Create league member record with invite
    new_member = LeagueMember(
        league_id=league_id,
        invite_token=invite_token,
        invite_email=invite_email,
        invited_at=datetime.utcnow(),
        role=MemberRole.MEMBER
    )

    db.add(new_member)
    await db.commit()

    # Generate invite URL (frontend will handle this route)
    from config import settings
    invite_url = f"{settings.frontend_url}/invite/{invite_token}"

    return InviteResponse(
        invite_url=invite_url,
        token=invite_token,
        expires_in_days=7  # For future use
    )


@router.get("/admin/leagues/{league_id}/members", response_model=List[MemberResponse])
async def list_league_members(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all members of a league (owner only).

    Returns all members including pending invites and active members.
    Commissioner (owner) is not included in this list.

    Args:
        league_id: League ID to list members for
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        List of MemberResponse objects

    Raises:
        HTTPException: If league not found or user is not the owner
    """
    # Verify league ownership
    await _get_league_with_access_check(
        league_id, current_user.id, db, require_owner=True
    )

    # Get all members
    result = await db.execute(
        select(LeagueMember)
        .filter(LeagueMember.league_id == league_id)
        .order_by(LeagueMember.joined_at.desc().nullslast())
    )
    members = result.scalars().all()

    # Build response
    member_responses = []
    for member in members:
        # Get user email if joined
        email = member.invite_email
        if member.user_id:
            user_result = await db.execute(
                select(User).filter(User.id == member.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and user.email:
                email = user.email

        member_responses.append(MemberResponse(
            id=member.id,
            user_id=member.user_id,
            email=email,
            role=member.role.value,
            joined_at=member.joined_at.isoformat() if member.joined_at else None,
            invited_at=member.invited_at.isoformat() if member.invited_at else None,
            preferences=_parse_preferences(member.preferences)
        ))

    return member_responses


@router.delete("/admin/leagues/{league_id}/members/{member_id}")
async def remove_league_member(
    league_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a member from a league (owner only).

    Can remove both pending invites and active members.

    Args:
        league_id: League ID
        member_id: Member ID to remove
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Success message

    Raises:
        HTTPException: If league/member not found or user is not the owner
    """
    # Verify league ownership
    await _get_league_with_access_check(
        league_id, current_user.id, db, require_owner=True
    )

    # Get member
    result = await db.execute(
        select(LeagueMember).filter(
            LeagueMember.id == member_id,
            LeagueMember.league_id == league_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    await db.delete(member)
    await db.commit()

    return {"message": "Member removed successfully"}


# ==================== Public Endpoints ====================

@router.get("/invite/{token}", response_model=InviteValidation)
async def validate_invite(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate an invite token and return league info (PUBLIC - no auth).

    This endpoint is used by the invite landing page to show league
    information before the user logs in or signs up.

    Args:
        token: Invite token from URL
        db: Database session from dependency injection

    Returns:
        InviteValidation with league info if valid
    """
    # Find invite by token
    result = await db.execute(
        select(LeagueMember)
        .filter(LeagueMember.invite_token == token)
    )
    member = result.scalar_one_or_none()

    if not member:
        return InviteValidation(
            valid=False,
            error="Invalid or expired invite"
        )

    # Check if already used
    if member.user_id is not None:
        return InviteValidation(
            valid=False,
            error="This invite has already been used"
        )

    # Get league info
    result = await db.execute(
        select(League).filter(League.id == member.league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        return InviteValidation(
            valid=False,
            error="League not found"
        )

    # Get owner info
    result = await db.execute(
        select(User).filter(User.id == league.owner_id)
    )
    owner = result.scalar_one_or_none()
    invited_by = owner.username or owner.email or "League Commissioner"

    return InviteValidation(
        valid=True,
        league_name=league.name,
        league_id=league.id,
        invited_by=invited_by
    )


@router.post("/invite/{token}/accept")
async def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept an invite and join the league (requires auth).

    User must be logged in to accept an invite. The invite token
    is consumed and the user becomes a member of the league.

    Args:
        token: Invite token from URL
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Success message with league info

    Raises:
        HTTPException: If invite invalid, already used, or user already a member
    """
    # Find invite by token
    result = await db.execute(
        select(LeagueMember)
        .filter(LeagueMember.invite_token == token)
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite"
        )

    # Check if already used
    if member.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has already been used"
        )

    # Check if user is already a member or owner
    result = await db.execute(
        select(League).filter(League.id == member.league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    if league.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already the owner of this league"
        )

    # Check for existing membership
    result = await db.execute(
        select(LeagueMember).filter(
            LeagueMember.league_id == member.league_id,
            LeagueMember.user_id == current_user.id,
            LeagueMember.joined_at.isnot(None)
        )
    )
    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this league"
        )

    # Update member record
    member.user_id = current_user.id
    member.joined_at = datetime.utcnow()
    member.invite_token = None  # Consume the token

    await db.commit()
    await db.refresh(member)

    return {
        "message": "Successfully joined league",
        "league_id": league.id,
        "league_name": league.name
    }


# ==================== Member Endpoints ====================

@router.get("/leagues/{league_id}/access", response_model=AccessCheck)
async def check_league_access(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if current user has access to a league.

    Returns access status, role, and preferences. Used by frontend
    to determine what to display and what actions are available.

    Args:
        league_id: League ID to check access for
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        AccessCheck with access status and details
    """
    # Get league
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        return AccessCheck(
            has_access=False,
            is_owner=False
        )

    # Check if owner
    if league.owner_id == current_user.id:
        return AccessCheck(
            has_access=True,
            role="commissioner",
            is_owner=True,
            preferences=None
        )

    # Check membership
    result = await db.execute(
        select(LeagueMember).filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == current_user.id,
            LeagueMember.joined_at.isnot(None)
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        return AccessCheck(
            has_access=False,
            is_owner=False
        )

    return AccessCheck(
        has_access=True,
        role=member.role.value,
        is_owner=False,
        preferences=_parse_preferences(member.preferences)
    )


@router.patch("/leagues/{league_id}/members/me/preferences")
async def update_member_preferences(
    league_id: int,
    preferences: MemberPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's preferences for a league.

    Members can update their own preferences for content delivery
    and notifications. Only non-None fields are updated.

    Args:
        league_id: League ID
        preferences: Preferences to update
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Updated preferences

    Raises:
        HTTPException: If user is not a member of the league
    """
    # Get member record
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this league"
        )

    # Parse existing preferences
    current_prefs = _parse_preferences(member.preferences) or {}

    # Update with new preferences (only non-None values)
    update_data = preferences.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            current_prefs[key] = value

    # Save back as JSON
    member.preferences = json.dumps(current_prefs)

    await db.commit()
    await db.refresh(member)

    return {
        "message": "Preferences updated successfully",
        "preferences": current_prefs
    }


@router.get("/leagues/{league_id}/members/me")
async def get_my_membership(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's membership info for a league.

    Returns detailed membership information including role and preferences.

    Args:
        league_id: League ID
        current_user: Authenticated user from dependency injection
        db: Database session from dependency injection

    Returns:
        Membership details

    Raises:
        HTTPException: If user is not a member of the league
    """
    # Check if owner
    result = await db.execute(
        select(League).filter(League.id == league_id)
    )
    league = result.scalar_one_or_none()

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    if league.owner_id == current_user.id:
        return {
            "is_owner": True,
            "role": "commissioner",
            "preferences": None
        }

    # Get member record
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this league"
        )

    return {
        "is_owner": False,
        "role": member.role.value,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        "preferences": _parse_preferences(member.preferences)
    }
