"""Celery tasks for scheduled operations."""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database.connection import AsyncSessionLocal
from models.league import League, ProviderType
from models.user import User
from models.transaction import Transaction
from models.matchup import Matchup
from services.recap_service import run_power_rankings, run_waiver_recap
from ingestors.sleeper_ingestor import ingest_sleeper_league
from ingestors.yahoo_ingestor import ingest_yahoo_leagues


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_weekly_power_rankings(self):
    """
    Scheduled task to run power rankings for all leagues.
    Runs Tuesday 9:00 AM Chicago time.
    """
    try:
        return asyncio.run(_run_weekly_power_rankings())
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_weekly_waiver_recaps(self):
    """
    Scheduled task to run waiver recaps for all leagues.
    Runs Wednesday 9:00 AM Chicago time.
    """
    try:
        return asyncio.run(_run_weekly_waiver_recaps())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def sync_all_leagues(self):
    """
    Scheduled task to sync data for all active leagues.
    Runs multiple times daily.
    """
    try:
        return asyncio.run(_sync_all_leagues())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))


@shared_task
def sync_specific_league(league_id: int, provider: str, provider_league_id: str):
    """
    Task to sync a specific league.
    
    Args:
        league_id: Internal league ID
        provider: Provider type ("sleeper" or "yahoo")
        provider_league_id: Provider-specific league ID
    """
    return asyncio.run(_sync_specific_league(league_id, provider, provider_league_id))


@shared_task
def generate_manual_recap(league_id: int, recap_type: str, week: Optional[int] = None):
    """
    Task to generate a manual recap for a league.
    
    Args:
        league_id: Internal league ID
        recap_type: Type of recap ("power_rankings" or "waiver_recap")
        week: Optional week number
    """
    return asyncio.run(_generate_manual_recap(league_id, recap_type, week))


@shared_task
def cleanup_old_data(self):
    """
    Scheduled task to clean up old data.
    Runs weekly on Sunday at 2 AM Chicago time.
    """
    try:
        return asyncio.run(_cleanup_old_data())
    except Exception as exc:
        print(f"Error in cleanup task: {exc}")
        return {"status": "error", "message": str(exc)}


@shared_task
def health_check():
    """
    Health check task to verify system is working.
    Runs every 15 minutes.
    """
    return asyncio.run(_health_check())


# Async implementations

async def _run_weekly_power_rankings():
    """Run power rankings for all enabled leagues."""
    results = {"successful": 0, "failed": 0, "skipped": 0, "errors": []}
    
    async with AsyncSessionLocal() as db:
        # Get all active leagues with power rankings enabled
        result = await db.execute(
            select(League).filter(
                League.is_active == True,
                League.enable_power_rankings == True,
                League.groupme_bot_id.isnot(None)
            )
        )
        leagues = result.scalars().all()
        
        print(f"Running power rankings for {len(leagues)} leagues")
        
        for league in leagues:
            try:
                # Calculate week (previous week for review)
                current_week = league.week or 1
                review_week = max(1, current_week - 1)
                
                print(f"Generating power rankings for {league.name} (Week {review_week})")
                
                await run_power_rankings(league.id, review_week)
                results["successful"] += 1
                
            except Exception as e:
                error_msg = f"Failed power rankings for league {league.id}: {str(e)}"
                print(error_msg)
                results["failed"] += 1
                results["errors"].append(error_msg)
    
    return results


async def _run_weekly_waiver_recaps():
    """Run waiver recaps for all enabled leagues."""
    results = {"successful": 0, "failed": 0, "skipped": 0, "errors": []}
    
    async with AsyncSessionLocal() as db:
        # Get all active leagues with waiver recaps enabled
        result = await db.execute(
            select(League).filter(
                League.is_active == True,
                League.enable_waiver_recaps == True,
                League.groupme_bot_id.isnot(None)
            )
        )
        leagues = result.scalars().all()
        
        print(f"Running waiver recaps for {len(leagues)} leagues")
        
        for league in leagues:
            try:
                # Use current week for waiver recap (Wednesday covers Tuesday waivers)
                current_week = league.week or 1
                
                print(f"Generating waiver recap for {league.name} (Week {current_week})")
                
                await run_waiver_recap(league.id, current_week)
                results["successful"] += 1
                
            except Exception as e:
                error_msg = f"Failed waiver recap for league {league.id}: {str(e)}"
                print(error_msg)
                results["failed"] += 1
                results["errors"].append(error_msg)
    
    return results


async def _sync_all_leagues():
    """Sync data for all active leagues."""
    results = {"successful": 0, "failed": 0, "skipped": 0, "errors": []}
    
    async with AsyncSessionLocal() as db:
        # Get all active leagues
        result = await db.execute(
            select(League).filter(League.is_active == True)
        )
        leagues = result.scalars().all()
        
        print(f"Syncing {len(leagues)} leagues")
        
        # Group leagues by provider for efficient processing
        sleeper_leagues = [l for l in leagues if l.provider == ProviderType.SLEEPER]
        yahoo_leagues = [l for l in leagues if l.provider == ProviderType.YAHOO]
        
        # Sync Sleeper leagues
        for league in sleeper_leagues:
            try:
                success = await ingest_sleeper_league(league.provider_league_id)
                if success:
                    results["successful"] += 1
                    # Update last sync time
                    league.last_sync_at = datetime.utcnow()
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Sleeper sync failed for league {league.id}")
                    
            except Exception as e:
                error_msg = f"Error syncing Sleeper league {league.id}: {str(e)}"
                print(error_msg)
                results["failed"] += 1
                results["errors"].append(error_msg)
        
        # Sync Yahoo leagues (grouped by user)
        yahoo_users = set(l.owner_id for l in yahoo_leagues)
        for user_id in yahoo_users:
            try:
                success = await ingest_yahoo_leagues(user_id)
                if success:
                    # Update last sync time for all leagues of this user
                    user_leagues = [l for l in yahoo_leagues if l.owner_id == user_id]
                    for league in user_leagues:
                        league.last_sync_at = datetime.utcnow()
                    results["successful"] += len(user_leagues)
                else:
                    user_leagues = [l for l in yahoo_leagues if l.owner_id == user_id]
                    results["failed"] += len(user_leagues)
                    results["errors"].append(f"Yahoo sync failed for user {user_id}")
                    
            except Exception as e:
                error_msg = f"Error syncing Yahoo leagues for user {user_id}: {str(e)}"
                print(error_msg)
                user_leagues = [l for l in yahoo_leagues if l.owner_id == user_id]
                results["failed"] += len(user_leagues)
                results["errors"].append(error_msg)
        
        await db.commit()
    
    return results


async def _sync_specific_league(league_id: int, provider: str, provider_league_id: str):
    """Sync a specific league."""
    try:
        if provider.lower() == "sleeper":
            success = await ingest_sleeper_league(provider_league_id)
        elif provider.lower() == "yahoo":
            # For Yahoo, we need the user ID, which we'll get from the league
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(League).filter(League.id == league_id))
                league = result.scalar_one_or_none()
                if league:
                    success = await ingest_yahoo_leagues(league.owner_id)
                else:
                    return {"status": "error", "message": "League not found"}
        else:
            return {"status": "error", "message": f"Unknown provider: {provider}"}
        
        if success:
            # Update last sync time
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(League).filter(League.id == league_id))
                league = result.scalar_one_or_none()
                if league:
                    league.last_sync_at = datetime.utcnow()
                    await db.commit()
            
            return {"status": "success", "message": f"Synced league {league_id}"}
        else:
            return {"status": "error", "message": f"Failed to sync league {league_id}"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _generate_manual_recap(league_id: int, recap_type: str, week: Optional[int] = None):
    """Generate a manual recap."""
    try:
        if recap_type == "power_rankings":
            await run_power_rankings(league_id, week)
        elif recap_type == "waiver_recap":
            await run_waiver_recap(league_id, week)
        else:
            return {"status": "error", "message": f"Unknown recap type: {recap_type}"}
        
        return {"status": "success", "message": f"Generated {recap_type} for league {league_id}"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _cleanup_old_data():
    """Clean up old data to maintain database performance."""
    results = {"deleted_transactions": 0, "deleted_matchups": 0, "errors": []}
    
    try:
        async with AsyncSessionLocal() as db:
            # Delete transactions older than 2 seasons
            cutoff_date = datetime.utcnow() - timedelta(days=730)  # ~2 years
            
            # Delete old transactions
            result = await db.execute(
                delete(Transaction).filter(Transaction.created_at < cutoff_date)
            )
            results["deleted_transactions"] = result.rowcount
            
            # Delete old matchups (keep current and last season)
            current_year = datetime.now().year
            old_season = current_year - 2
            
            result = await db.execute(
                delete(Matchup).filter(Matchup.season < old_season)
            )
            results["deleted_matchups"] = result.rowcount
            
            await db.commit()
            
            print(f"Cleanup complete: {results}")
            
    except Exception as e:
        error_msg = f"Error during cleanup: {str(e)}"
        print(error_msg)
        results["errors"].append(error_msg)
    
    return results


async def _health_check():
    """Perform health check of the system."""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": "unknown",
        "redis": "unknown",
        "active_leagues": 0,
        "status": "healthy"
    }
    
    try:
        # Check database connectivity
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(League).filter(League.is_active == True))
            leagues = result.scalars().all()
            health_status["active_leagues"] = len(leagues)
            health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis (Celery broker) - implicit if this task is running
    health_status["redis"] = "healthy"
    
    return health_status
