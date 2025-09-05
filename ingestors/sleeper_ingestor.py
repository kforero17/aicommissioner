"""Sleeper API data ingestor for normalizing fantasy league data."""
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import AsyncSessionLocal
from models.league import League, ProviderType, LeagueType
from models.roster import Roster
from models.matchup import Matchup
from models.transaction import Transaction, TransactionType, TransactionStatus
from config import settings


class SleeperAPI:
    """Sleeper API client for data retrieval."""
    
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_league(self, league_id: str) -> Dict[str, Any]:
        """Get league information."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_rosters(self, league_id: str) -> List[Dict[str, Any]]:
        """Get all rosters in a league."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_id}/rosters")
        response.raise_for_status()
        return response.json()
    
    async def get_users(self, league_id: str) -> List[Dict[str, Any]]:
        """Get all users in a league."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_id}/users")
        response.raise_for_status()
        return response.json()
    
    async def get_matchups(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """Get matchups for a specific week."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_id}/matchups/{week}")
        response.raise_for_status()
        return response.json()
    
    async def get_transactions(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """Get transactions for a specific week."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_id}/transactions/{week}")
        response.raise_for_status()
        return response.json()
    
    async def get_traded_picks(self, league_id: str) -> List[Dict[str, Any]]:
        """Get traded draft picks."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_id}/traded_picks")
        response.raise_for_status()
        return response.json()


async def ingest_sleeper_league(league_id: str) -> bool:
    """
    Ingest all data for a Sleeper league.
    
    Args:
        league_id: Sleeper league ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    api = SleeperAPI()
    
    try:
        async with AsyncSessionLocal() as db:
            # Get or create league record
            result = await db.execute(
                select(League).filter(
                    League.provider == ProviderType.SLEEPER,
                    League.provider_league_id == league_id
                )
            )
            league = result.scalar_one_or_none()
            
            # Fetch league data from Sleeper
            league_data = await api.get_league(league_id)
            
            if not league:
                # Create new league record if it doesn't exist
                # This happens when someone adds a Sleeper league ID
                league = League(
                    provider=ProviderType.SLEEPER,
                    provider_league_id=league_id,
                    name=league_data.get('name', f'League {league_id}'),
                    league_type=_map_sport_to_league_type(league_data.get('sport', 'nfl')),
                    season=league_data.get('season', datetime.now().year),
                    week=league_data.get('settings', {}).get('leg', 1),
                    num_teams=league_data.get('total_rosters', 0),
                    scoring_type=_determine_scoring_type(league_data.get('scoring_settings', {})),
                    owner_id=1,  # This will need to be set properly based on who added the league
                )
                db.add(league)
                await db.flush()  # Get the ID
            else:
                # Update existing league
                league.name = league_data.get('name', league.name)
                league.week = league_data.get('settings', {}).get('leg', league.week)
                league.num_teams = league_data.get('total_rosters', league.num_teams)
                league.scoring_type = _determine_scoring_type(league_data.get('scoring_settings', {}))
            
            # Ingest rosters
            await _ingest_sleeper_rosters(api, db, league, league_id)
            
            # Ingest matchups for current and recent weeks
            current_week = league.week or 1
            for week in range(max(1, current_week - 2), current_week + 1):
                try:
                    await _ingest_sleeper_matchups(api, db, league, league_id, week)
                except Exception as e:
                    print(f"Error ingesting matchups for week {week}: {e}")
                    continue
            
            # Ingest recent transactions
            for week in range(max(1, current_week - 1), current_week + 1):
                try:
                    await _ingest_sleeper_transactions(api, db, league, league_id, week)
                except Exception as e:
                    print(f"Error ingesting transactions for week {week}: {e}")
                    continue
            
            # Update last sync time
            league.last_sync_at = datetime.utcnow()
            
            await db.commit()
            return True
            
    except Exception as e:
        print(f"Error ingesting Sleeper league {league_id}: {e}")
        return False
    finally:
        await api.close()


async def _ingest_sleeper_rosters(
    api: SleeperAPI, 
    db: AsyncSession, 
    league: League, 
    league_id: str
):
    """Ingest roster data from Sleeper."""
    rosters_data = await api.get_rosters(league_id)
    users_data = await api.get_users(league_id)
    
    # Create user lookup
    user_lookup = {user['user_id']: user for user in users_data}
    
    for roster_data in rosters_data:
        roster_id = str(roster_data['roster_id'])
        owner_id = roster_data.get('owner_id')
        user_info = user_lookup.get(owner_id, {}) if owner_id else {}
        
        # Find or create roster
        result = await db.execute(
            select(Roster).filter(
                Roster.league_id == league.id,
                Roster.provider_roster_id == roster_id
            )
        )
        roster = result.scalar_one_or_none()
        
        if not roster:
            roster = Roster(
                league_id=league.id,
                provider_roster_id=roster_id,
                provider_owner_id=owner_id,
            )
            db.add(roster)
        
        # Update roster data
        roster.team_name = user_info.get('metadata', {}).get('team_name') or user_info.get('display_name')
        roster.owner_name = user_info.get('display_name')
        roster.wins = roster_data.get('settings', {}).get('wins', 0)
        roster.losses = roster_data.get('settings', {}).get('losses', 0)
        roster.ties = roster_data.get('settings', {}).get('ties', 0)
        roster.points_for = float(roster_data.get('settings', {}).get('fpts', 0))
        roster.points_against = float(roster_data.get('settings', {}).get('fpts_against', 0))
        
        # Store roster composition as JSON
        roster.starters = json.dumps(roster_data.get('starters', []))
        roster.bench = json.dumps(roster_data.get('players', []))
        roster.ir = json.dumps(roster_data.get('reserve', []))
        
        # FAAB budget
        roster.faab_budget = roster_data.get('settings', {}).get('waiver_budget_used', 0)


async def _ingest_sleeper_matchups(
    api: SleeperAPI,
    db: AsyncSession,
    league: League,
    league_id: str,
    week: int
):
    """Ingest matchup data for a specific week."""
    try:
        matchups_data = await api.get_matchups(league_id, week)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Week doesn't exist yet
            return
        raise
    
    # Group matchups by matchup_id
    matchup_groups = {}
    for matchup in matchups_data:
        matchup_id = matchup.get('matchup_id')
        if matchup_id is None:
            continue  # Bye week
        
        if matchup_id not in matchup_groups:
            matchup_groups[matchup_id] = []
        matchup_groups[matchup_id].append(matchup)
    
    for matchup_id, teams in matchup_groups.items():
        if len(teams) != 2:
            continue  # Skip if not a valid matchup
        
        team1, team2 = teams[0], teams[1]
        provider_matchup_id = f"{league_id}_{week}_{matchup_id}"
        
        # Find or create matchup
        result = await db.execute(
            select(Matchup).filter(
                Matchup.league_id == league.id,
                Matchup.provider_matchup_id == provider_matchup_id
            )
        )
        matchup = result.scalar_one_or_none()
        
        if not matchup:
            matchup = Matchup(
                league_id=league.id,
                provider_matchup_id=provider_matchup_id,
                week=week,
                season=league.season,
            )
            db.add(matchup)
        
        # Update matchup data
        matchup.team1_roster_id = str(team1['roster_id'])
        matchup.team1_points = float(team1.get('points', 0))
        matchup.team1_projected = float(team1.get('points_projected', 0))
        
        matchup.team2_roster_id = str(team2['roster_id'])
        matchup.team2_points = float(team2.get('points', 0))
        matchup.team2_projected = float(team2.get('points_projected', 0))
        
        # Determine winner if matchup is complete
        if team1.get('points') is not None and team2.get('points') is not None:
            matchup.is_complete = True
            if team1['points'] > team2['points']:
                matchup.winner_roster_id = str(team1['roster_id'])
                matchup.margin_of_victory = team1['points'] - team2['points']
            elif team2['points'] > team1['points']:
                matchup.winner_roster_id = str(team2['roster_id'])
                matchup.margin_of_victory = team2['points'] - team1['points']


async def _ingest_sleeper_transactions(
    api: SleeperAPI,
    db: AsyncSession,
    league: League,
    league_id: str,
    week: int
):
    """Ingest transaction data for a specific week."""
    try:
        transactions_data = await api.get_transactions(league_id, week)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Week doesn't exist yet
            return
        raise
    
    for trans_data in transactions_data:
        transaction_id = str(trans_data['transaction_id'])
        
        # Find or create transaction
        result = await db.execute(
            select(Transaction).filter(
                Transaction.league_id == league.id,
                Transaction.provider_transaction_id == transaction_id
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            transaction = Transaction(
                league_id=league.id,
                provider_transaction_id=transaction_id,
                week=week,
            )
            db.add(transaction)
        
        # Map transaction type
        trans_type = trans_data.get('type', 'waiver')
        if trans_type == 'waiver':
            transaction.transaction_type = TransactionType.WAIVER
        elif trans_type == 'free_agent':
            transaction.transaction_type = TransactionType.FREE_AGENT
        elif trans_type == 'trade':
            transaction.transaction_type = TransactionType.TRADE
        else:
            transaction.transaction_type = TransactionType.ADD
        
        # Set status
        status_map = {
            'complete': TransactionStatus.COMPLETED,
            'failed': TransactionStatus.FAILED,
            'pending': TransactionStatus.PENDING,
        }
        transaction.status = status_map.get(trans_data.get('status', 'complete'), TransactionStatus.COMPLETED)
        
        # Set roster ID (main roster involved)
        if trans_data.get('roster_ids'):
            transaction.roster_id = str(trans_data['roster_ids'][0])
        
        # Store player data as JSON
        if trans_data.get('adds'):
            transaction.players_added = json.dumps(trans_data['adds'])
        if trans_data.get('drops'):
            transaction.players_dropped = json.dumps(trans_data['drops'])
        
        # FAAB bid
        if trans_data.get('waiver_budget'):
            for roster_id, bid in trans_data['waiver_budget'].items():
                if roster_id == transaction.roster_id:
                    transaction.faab_bid = bid
                    break
        
        # Processing time
        if trans_data.get('created'):
            transaction.processed_at = datetime.fromtimestamp(trans_data['created'] / 1000)


def _map_sport_to_league_type(sport: str) -> LeagueType:
    """Map Sleeper sport to our LeagueType enum."""
    sport_map = {
        'nfl': LeagueType.FOOTBALL,
        'nba': LeagueType.BASKETBALL,
        'mlb': LeagueType.BASEBALL,
        'nhl': LeagueType.HOCKEY,
    }
    return sport_map.get(sport.lower(), LeagueType.FOOTBALL)


def _determine_scoring_type(scoring_settings: Dict[str, Any]) -> str:
    """Determine scoring type from Sleeper scoring settings."""
    if not scoring_settings:
        return "standard"
    
    # Check for PPR scoring
    rec_points = scoring_settings.get('rec', 0)
    if rec_points >= 1:
        return "ppr"
    elif rec_points > 0:
        return "half_ppr"
    else:
        return "standard"


# Background task function
async def run_sleeper_ingestion(league_id: str):
    """Background task to run Sleeper ingestion."""
    success = await ingest_sleeper_league(league_id)
    if success:
        print(f"Successfully ingested Sleeper league {league_id}")
    else:
        print(f"Failed to ingest Sleeper league {league_id}")
