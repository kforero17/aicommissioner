"""Helper utilities for managing league member emails."""
import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models.league import League
from models.user import User
from models.roster import Roster


async def add_league_member_email(
    db: AsyncSession, 
    league_id: int, 
    email: str
) -> bool:
    """
    Add an email address to a league's member email list.
    
    Args:
        db: Database session
        league_id: League ID
        email: Email address to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get league
        result = await db.execute(select(League).filter(League.id == league_id))
        league = result.scalar_one_or_none()
        
        if not league:
            print(f"League {league_id} not found")
            return False
        
        # Parse existing emails
        existing_emails = []
        if league.league_member_emails:
            try:
                existing_emails = json.loads(league.league_member_emails)
                if not isinstance(existing_emails, list):
                    existing_emails = []
            except json.JSONDecodeError:
                existing_emails = []
        
        # Add email if not already present
        if email not in existing_emails:
            existing_emails.append(email)
            
            # Update league
            await db.execute(
                update(League)
                .where(League.id == league_id)
                .values(league_member_emails=json.dumps(existing_emails))
            )
            await db.commit()
            
            print(f"Added email {email} to league {league_id}")
            return True
        else:
            print(f"Email {email} already exists in league {league_id}")
            return True
            
    except Exception as e:
        print(f"Error adding email to league {league_id}: {e}")
        await db.rollback()
        return False


async def remove_league_member_email(
    db: AsyncSession, 
    league_id: int, 
    email: str
) -> bool:
    """
    Remove an email address from a league's member email list.
    
    Args:
        db: Database session
        league_id: League ID
        email: Email address to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get league
        result = await db.execute(select(League).filter(League.id == league_id))
        league = result.scalar_one_or_none()
        
        if not league:
            print(f"League {league_id} not found")
            return False
        
        # Parse existing emails
        existing_emails = []
        if league.league_member_emails:
            try:
                existing_emails = json.loads(league.league_member_emails)
                if not isinstance(existing_emails, list):
                    existing_emails = []
            except json.JSONDecodeError:
                existing_emails = []
        
        # Remove email if present
        if email in existing_emails:
            existing_emails.remove(email)
            
            # Update league
            await db.execute(
                update(League)
                .where(League.id == league_id)
                .values(league_member_emails=json.dumps(existing_emails))
            )
            await db.commit()
            
            print(f"Removed email {email} from league {league_id}")
            return True
        else:
            print(f"Email {email} not found in league {league_id}")
            return True
            
    except Exception as e:
        print(f"Error removing email from league {league_id}: {e}")
        await db.rollback()
        return False


async def set_league_member_emails(
    db: AsyncSession, 
    league_id: int, 
    emails: List[str]
) -> bool:
    """
    Set the complete list of member emails for a league.
    
    Args:
        db: Database session
        league_id: League ID
        emails: List of email addresses
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate emails
        valid_emails = [email.strip() for email in emails if email and email.strip()]
        
        # Update league
        await db.execute(
            update(League)
            .where(League.id == league_id)
            .values(league_member_emails=json.dumps(valid_emails))
        )
        await db.commit()
        
        print(f"Set {len(valid_emails)} emails for league {league_id}")
        return True
        
    except Exception as e:
        print(f"Error setting emails for league {league_id}: {e}")
        await db.rollback()
        return False


async def enable_email_recaps(
    db: AsyncSession, 
    league_id: int, 
    enable: bool = True
) -> bool:
    """
    Enable or disable email recaps for a league.
    
    Args:
        db: Database session
        league_id: League ID
        enable: Whether to enable (True) or disable (False) email recaps
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        await db.execute(
            update(League)
            .where(League.id == league_id)
            .values(enable_email_recaps=enable)
        )
        await db.commit()
        
        status = "enabled" if enable else "disabled"
        print(f"Email recaps {status} for league {league_id}")
        return True
        
    except Exception as e:
        print(f"Error updating email recap setting for league {league_id}: {e}")
        await db.rollback()
        return False


async def get_league_email_settings(
    db: AsyncSession, 
    league_id: int
) -> Optional[dict]:
    """
    Get current email settings for a league.
    
    Args:
        db: Database session
        league_id: League ID
        
    Returns:
        dict: Email settings or None if league not found
    """
    try:
        result = await db.execute(select(League).filter(League.id == league_id))
        league = result.scalar_one_or_none()
        
        if not league:
            return None
        
        member_emails = []
        if league.league_member_emails:
            try:
                member_emails = json.loads(league.league_member_emails)
                if not isinstance(member_emails, list):
                    member_emails = []
            except json.JSONDecodeError:
                member_emails = []
        
        return {
            "league_id": league.id,
            "league_name": league.name,
            "enable_email_recaps": league.enable_email_recaps,
            "member_emails": member_emails,
            "email_count": len(member_emails)
        }
        
    except Exception as e:
        print(f"Error getting email settings for league {league_id}: {e}")
        return None


async def sync_roster_emails_to_league(
    db: AsyncSession, 
    league_id: int
) -> bool:
    """
    Sync league member emails from roster owners to league email list.
    This is useful when users have registered accounts with email addresses.
    
    Args:
        db: Database session
        league_id: League ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get all roster owners for this league with their user emails
        query = (
            select(User.email)
            .join(Roster, User.id == Roster.provider_owner_id)  # Assuming provider_owner_id links to User.id
            .filter(Roster.league_id == league_id)
            .filter(User.email.isnot(None))
            .distinct()
        )
        
        result = await db.execute(query)
        emails = [row[0] for row in result.fetchall() if row[0]]
        
        if emails:
            success = await set_league_member_emails(db, league_id, emails)
            if success:
                print(f"Synced {len(emails)} roster owner emails to league {league_id}")
            return success
        else:
            print(f"No roster owner emails found for league {league_id}")
            return True
            
    except Exception as e:
        print(f"Error syncing roster emails for league {league_id}: {e}")
        return False
