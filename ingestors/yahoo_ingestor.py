"""Yahoo Fantasy API data ingestor for normalizing fantasy league data."""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import AsyncSessionLocal
from models.user import User
from models.league import League, ProviderType, LeagueType
from models.roster import Roster
from models.matchup import Matchup
from models.transaction import Transaction, TransactionType, TransactionStatus
from config import settings


class YahooAPI:
    """Yahoo Fantasy API client for data retrieval."""
    
    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_user_leagues(self, game_key: str = "nfl") -> List[Dict[str, Any]]:
        """Get all leagues for the authenticated user."""
        # Get current year's game
        current_year = datetime.now().year
        game_id = f"{current_year if game_key == 'nfl' else game_key}"
        
        response = await self.client.get(
            f"{self.BASE_URL}/users;use_login=1/games;game_keys={game_id}/leagues"
        )
        response.raise_for_status()
        
        # Parse XML response (Yahoo returns XML)
        # For simplicity, we'll assume JSON conversion is handled elsewhere
        # In a real implementation, you'd use an XML parser like xmltodict
        return self._parse_yahoo_response(response.text)
    
    async def get_league(self, league_key: str) -> Dict[str, Any]:
        """Get league information."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_key}")
        response.raise_for_status()
        return self._parse_yahoo_response(response.text)
    
    async def get_teams(self, league_key: str) -> List[Dict[str, Any]]:
        """Get all teams in a league."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_key}/teams")
        response.raise_for_status()
        return self._parse_yahoo_response(response.text)
    
    async def get_scoreboard(self, league_key: str, week: int) -> List[Dict[str, Any]]:
        """Get matchups/scoreboard for a specific week."""
        response = await self.client.get(
            f"{self.BASE_URL}/league/{league_key}/scoreboard;week={week}"
        )
        response.raise_for_status()
        return self._parse_yahoo_response(response.text)
    
    async def get_transactions(self, league_key: str, transaction_type: str = "add,drop,trade") -> List[Dict[str, Any]]:
        """Get transactions for a league."""
        response = await self.client.get(
            f"{self.BASE_URL}/league/{league_key}/transactions;types={transaction_type}"
        )
        response.raise_for_status()
        return self._parse_yahoo_response(response.text)
    
    async def get_standings(self, league_key: str) -> List[Dict[str, Any]]:
        """Get league standings."""
        response = await self.client.get(f"{self.BASE_URL}/league/{league_key}/standings")
        response.raise_for_status()
        return self._parse_yahoo_response(response.text)
    
    def _parse_yahoo_response(self, xml_text: str) -> Dict[str, Any]:
        """
        Parse Yahoo's XML response to dict.
        This is a placeholder - in a real implementation, you'd use xmltodict or similar.
        """
        # For now, return empty dict - you'll need to implement XML parsing
        # Yahoo's API returns XML, not JSON
        return {}


async def ingest_yahoo_leagues(user_id: int) -> bool:
    """
    Ingest all Yahoo leagues for a user.
    
    Args:
        user_id: Internal user ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as db:
            # Get user with Yahoo tokens
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user or not user.yahoo_access_token:
                print(f"User {user_id} not found or no Yahoo access token")
                return False
            
            # Check if token is expired and refresh if needed
            if user.yahoo_token_expires_at and user.yahoo_token_expires_at <= datetime.utcnow():
                success = await _refresh_yahoo_token(db, user)
                if not success:
                    print(f"Failed to refresh Yahoo token for user {user_id}")
                    return False
            
            api = YahooAPI(user.yahoo_access_token)
            
            try:
                # Get user's leagues
                leagues_data = await api.get_user_leagues("nfl")  # Default to NFL
                
                for league_data in leagues_data:
                    league_key = league_data.get('league_key')
                    if not league_key:
                        continue
                    
                    # Process each league
                    await _ingest_yahoo_league(api, db, user, league_key, league_data)
                
                await db.commit()
                return True
                
            finally:
                await api.close()
                
    except Exception as e:
        print(f"Error ingesting Yahoo leagues for user {user_id}: {e}")
        return False


async def _ingest_yahoo_league(
    api: YahooAPI,
    db: AsyncSession,
    user: User,
    league_key: str,
    league_data: Dict[str, Any]
):
    """Ingest a single Yahoo league."""
    # Find or create league record
    result = await db.execute(
        select(League).filter(
            League.provider == ProviderType.YAHOO,
            League.provider_league_id == league_key,
            League.owner_id == user.id
        )
    )
    league = result.scalar_one_or_none()
    
    if not league:
        # Get more detailed league info
        detailed_league_data = await api.get_league(league_key)
        
        league = League(
            provider=ProviderType.YAHOO,
            provider_league_id=league_key,
            owner_id=user.id,
            name=league_data.get('name', f'League {league_key}'),
            league_type=_map_yahoo_sport_to_league_type(league_data.get('game_code', 'nfl')),
            season=league_data.get('season', datetime.now().year),
            week=league_data.get('current_week', 1),
            num_teams=league_data.get('num_teams', 0),
            scoring_type=_determine_yahoo_scoring_type(detailed_league_data.get('settings', {})),
        )
        db.add(league)
        await db.flush()  # Get the ID
    else:
        # Update existing league
        league.name = league_data.get('name', league.name)
        league.week = league_data.get('current_week', league.week)
        league.num_teams = league_data.get('num_teams', league.num_teams)
    
    # Ingest teams/rosters
    await _ingest_yahoo_teams(api, db, league, league_key)
    
    # Ingest matchups for current and recent weeks
    current_week = league.week or 1
    for week in range(max(1, current_week - 2), current_week + 1):
        try:
            await _ingest_yahoo_matchups(api, db, league, league_key, week)
        except Exception as e:
            print(f"Error ingesting Yahoo matchups for week {week}: {e}")
            continue
    
    # Ingest transactions
    try:
        await _ingest_yahoo_transactions(api, db, league, league_key)
    except Exception as e:
        print(f"Error ingesting Yahoo transactions: {e}")
    
    # Update last sync time
    league.last_sync_at = datetime.utcnow()


async def _ingest_yahoo_teams(
    api: YahooAPI,
    db: AsyncSession,
    league: League,
    league_key: str
):
    """Ingest team/roster data from Yahoo."""
    teams_data = await api.get_teams(league_key)
    standings_data = await api.get_standings(league_key)
    
    # Create standings lookup
    standings_lookup = {}
    for standing in standings_data:
        team_key = standing.get('team_key')
        if team_key:
            standings_lookup[team_key] = standing
    
    for team_data in teams_data:
        team_key = team_data.get('team_key')
        if not team_key:
            continue
        
        # Find or create roster
        result = await db.execute(
            select(Roster).filter(
                Roster.league_id == league.id,
                Roster.provider_roster_id == team_key
            )
        )
        roster = result.scalar_one_or_none()
        
        if not roster:
            roster = Roster(
                league_id=league.id,
                provider_roster_id=team_key,
                provider_owner_id=team_data.get('owner_guid'),
            )
            db.add(roster)
        
        # Update roster data
        roster.team_name = team_data.get('name')
        roster.owner_name = team_data.get('manager', {}).get('nickname')
        
        # Get standings data
        standing = standings_lookup.get(team_key, {})
        outcome_totals = standing.get('outcome_totals', {})
        
        roster.wins = int(outcome_totals.get('wins', 0))
        roster.losses = int(outcome_totals.get('losses', 0))
        roster.ties = int(outcome_totals.get('ties', 0))
        roster.points_for = float(standing.get('points_for', 0))
        roster.points_against = float(standing.get('points_against', 0))
        
        # Store current roster (would need separate API call for detailed roster)
        # For now, just store the team key
        roster.starters = json.dumps([team_key])


async def _ingest_yahoo_matchups(
    api: YahooAPI,
    db: AsyncSession,
    league: League,
    league_key: str,
    week: int
):
    """Ingest matchup data for a specific week."""
    try:
        scoreboard_data = await api.get_scoreboard(league_key, week)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Week doesn't exist yet
            return
        raise
    
    for matchup_data in scoreboard_data:
        teams = matchup_data.get('teams', [])
        if len(teams) != 2:
            continue  # Skip bye weeks or invalid matchups
        
        team1, team2 = teams[0], teams[1]
        provider_matchup_id = f"{league_key}_{week}_{team1.get('team_key')}_{team2.get('team_key')}"
        
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
        matchup.team1_roster_id = team1.get('team_key')
        matchup.team1_points = float(team1.get('team_points', {}).get('total', 0))
        matchup.team1_projected = float(team1.get('team_projected_points', {}).get('total', 0))
        
        matchup.team2_roster_id = team2.get('team_key')
        matchup.team2_points = float(team2.get('team_points', {}).get('total', 0))
        matchup.team2_projected = float(team2.get('team_projected_points', {}).get('total', 0))
        
        # Determine winner
        if matchup.team1_points > 0 or matchup.team2_points > 0:
            matchup.is_complete = True
            if matchup.team1_points > matchup.team2_points:
                matchup.winner_roster_id = matchup.team1_roster_id
                matchup.margin_of_victory = matchup.team1_points - matchup.team2_points
            elif matchup.team2_points > matchup.team1_points:
                matchup.winner_roster_id = matchup.team2_roster_id
                matchup.margin_of_victory = matchup.team2_points - matchup.team1_points


async def _ingest_yahoo_transactions(
    api: YahooAPI,
    db: AsyncSession,
    league: League,
    league_key: str
):
    """Ingest transaction data from Yahoo."""
    transactions_data = await api.get_transactions(league_key)
    
    for trans_data in transactions_data:
        transaction_key = trans_data.get('transaction_key')
        if not transaction_key:
            continue
        
        # Find or create transaction
        result = await db.execute(
            select(Transaction).filter(
                Transaction.league_id == league.id,
                Transaction.provider_transaction_id == transaction_key
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            transaction = Transaction(
                league_id=league.id,
                provider_transaction_id=transaction_key,
                week=trans_data.get('week', 1),
            )
            db.add(transaction)
        
        # Map transaction type
        trans_type = trans_data.get('type', 'add/drop')
        if 'trade' in trans_type.lower():
            transaction.transaction_type = TransactionType.TRADE
        elif 'add' in trans_type.lower():
            transaction.transaction_type = TransactionType.ADD
        elif 'drop' in trans_type.lower():
            transaction.transaction_type = TransactionType.DROP
        else:
            transaction.transaction_type = TransactionType.WAIVER
        
        # Set status based on Yahoo status
        status = trans_data.get('status', 'successful')
        if status == 'successful':
            transaction.status = TransactionStatus.COMPLETED
        elif status == 'pending':
            transaction.status = TransactionStatus.PENDING
        else:
            transaction.status = TransactionStatus.FAILED
        
        # Get team involved
        players = trans_data.get('players', [])
        if players:
            # Find the team that made the transaction
            for player in players:
                if player.get('transaction_data'):
                    transaction.roster_id = player['transaction_data'].get('destination_team_key')
                    break
        
        # Store player data as JSON
        transaction.players_added = json.dumps([
            p for p in players if p.get('transaction_data', {}).get('type') == 'add'
        ])
        transaction.players_dropped = json.dumps([
            p for p in players if p.get('transaction_data', {}).get('type') == 'drop'
        ])
        
        # Processing time
        if trans_data.get('timestamp'):
            transaction.processed_at = datetime.fromtimestamp(int(trans_data['timestamp']))


async def _refresh_yahoo_token(db: AsyncSession, user: User) -> bool:
    """Refresh Yahoo OAuth token."""
    if not user.yahoo_refresh_token:
        return False
    
    try:
        # Make refresh token request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.login.yahoo.com/oauth2/get_token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": user.yahoo_refresh_token,
                    "client_id": settings.yahoo_client_id,
                    "client_secret": settings.yahoo_client_secret,
                }
            )
            
            if response.status_code == 200:
                token_data = response.json()
                user.yahoo_access_token = token_data['access_token']
                if 'refresh_token' in token_data:
                    user.yahoo_refresh_token = token_data['refresh_token']
                if 'expires_in' in token_data:
                    user.yahoo_token_expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
                
                await db.commit()
                return True
    
    except Exception as e:
        print(f"Error refreshing Yahoo token: {e}")
    
    return False


def _map_yahoo_sport_to_league_type(game_code: str) -> LeagueType:
    """Map Yahoo game code to our LeagueType enum."""
    game_map = {
        'nfl': LeagueType.FOOTBALL,
        'nba': LeagueType.BASKETBALL,
        'mlb': LeagueType.BASEBALL,
        'nhl': LeagueType.HOCKEY,
    }
    return game_map.get(game_code.lower(), LeagueType.FOOTBALL)


def _determine_yahoo_scoring_type(settings: Dict[str, Any]) -> str:
    """Determine scoring type from Yahoo league settings."""
    if not settings:
        return "standard"
    
    # Yahoo scoring type detection would be based on their specific settings
    # This is a placeholder implementation
    scoring_type = settings.get('scoring_type', 'standard')
    if 'ppr' in scoring_type.lower():
        return "ppr"
    elif 'half' in scoring_type.lower():
        return "half_ppr"
    else:
        return "standard"


# Background task function
async def run_yahoo_ingestion(user_id: int):
    """Background task to run Yahoo ingestion."""
    success = await ingest_yahoo_leagues(user_id)
    if success:
        print(f"Successfully ingested Yahoo leagues for user {user_id}")
    else:
        print(f"Failed to ingest Yahoo leagues for user {user_id}")
