"""Yahoo Fantasy API data ingestor for normalizing fantasy league data."""
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

import httpx
import xmltodict
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
        # Bypass SSL verification in debug mode (corporate network)
        verify_ssl = not settings.debug
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"},
            verify=verify_ssl
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_user_leagues(self, game_key: str = "nfl") -> List[Dict[str, Any]]:
        """Get all leagues for the authenticated user across all seasons."""
        # Use game_codes instead of game_keys to get ALL seasons for a sport
        # This returns leagues from 2023, 2024, 2025, etc.
        response = await self.client.get(
            f"{self.BASE_URL}/users;use_login=1/games;game_codes={game_key}/leagues",
            params={"format": "json"}
        )
        response.raise_for_status()
        
        # Parse response based on content type
        content_type = response.headers.get('content-type', '')
        leagues = []
        
        try:
            if 'json' in content_type:
                data = response.json()
                leagues = self._extract_leagues_from_json(data)
            else:
                # Parse XML response
                parsed = self._parse_yahoo_response(response.text)
                leagues = self._extract_leagues_from_xml(parsed)
        except Exception as e:
            print(f"Error parsing Yahoo leagues response: {e}")
            print(f"Response content: {response.text[:500]}")
            
        return leagues
    
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
        """Parse Yahoo's XML response to dict using xmltodict."""
        try:
            parsed = xmltodict.parse(xml_text)

            if 'fantasy_content' in parsed:
                return parsed['fantasy_content']

            return parsed
        except Exception as e:
            print(f"Error parsing Yahoo XML response: {e}")
            return {}

    @staticmethod
    def _ensure_list(data: Any) -> List[Dict[str, Any]]:
        """Normalize Yahoo API data to a list of dicts.

        xmltodict returns inconsistent types: single items become dicts,
        multiple items become lists, and malformed data becomes strings.
        This normalizes everything to a list of dicts for safe iteration.
        """
        if data is None:
            return []
        if isinstance(data, str):
            return []
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    @staticmethod
    def _safe_get(data: Any, key: str, default: Any = None) -> Any:
        """Safely get a value from data that might not be a dict."""
        if isinstance(data, dict):
            return data.get(key, default)
        return default
    
    def _extract_leagues_from_json(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract league data from Yahoo JSON response."""
        leagues = []
        
        try:
            # Navigate Yahoo's complex JSON structure
            fantasy_content = data.get('fantasy_content', {})
            users = fantasy_content.get('users', {})
            
            # Yahoo uses numeric keys for arrays
            for user_key in users:
                if user_key.isdigit():
                    user_data = users[user_key].get('user', [])
                    if isinstance(user_data, list) and len(user_data) > 1:
                        # User data is array: [basic_info, games_data]
                        games_data = user_data[1].get('games', {})
                        
                        for game_key in games_data:
                            if game_key.isdigit():
                                game_info = games_data[game_key].get('game', [])
                                if isinstance(game_info, list) and len(game_info) > 1:
                                    # Game data is array: [basic_info, leagues_data]
                                    leagues_data = game_info[1].get('leagues', {})
                                    
                                    for league_key in leagues_data:
                                        if league_key.isdigit():
                                            league_info = leagues_data[league_key].get('league', [])
                                            if isinstance(league_info, list):
                                                # Convert array format to dict
                                                league_dict = {}
                                                for item in league_info:
                                                    if isinstance(item, dict):
                                                        league_dict.update(item)
                                                leagues.append(league_dict)
                                            elif isinstance(league_info, dict):
                                                leagues.append(league_info)
        except Exception as e:
            print(f"Error extracting leagues from JSON: {e}")
        
        return leagues
    
    def _extract_leagues_from_xml(self, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract league data from parsed XML response."""
        leagues = []
        
        try:
            # Navigate XML structure
            if 'users' in parsed:
                users = parsed['users']
                if 'user' in users:
                    user_data = users['user']
                    if 'games' in user_data:
                        games = user_data['games']
                        if 'game' in games:
                            game_data = games['game']
                            if 'leagues' in game_data:
                                leagues_data = game_data['leagues']
                                if 'league' in leagues_data:
                                    league_data = leagues_data['league']
                                    # Handle single league or list of leagues
                                    if isinstance(league_data, list):
                                        leagues = league_data
                                    else:
                                        leagues = [league_data]
        except Exception as e:
            print(f"Error extracting leagues from XML: {e}")
        
        return leagues


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
            if user.yahoo_token_expires_at and user.yahoo_token_expires_at <= datetime.now(timezone.utc):
                success = await _refresh_yahoo_token(db, user)
                if not success:
                    print(f"Failed to refresh Yahoo token for user {user_id}")
                    return False
            
            api = YahooAPI(user.yahoo_access_token)
            
            try:
                # Get user's leagues
                print(f"Fetching Yahoo leagues for user {user_id}...")
                leagues_data = await api.get_user_leagues("nfl")  # Default to NFL
                
                print(f"Yahoo API returned {len(leagues_data)} leagues")
                if leagues_data:
                    print(f"Sample league data: {leagues_data[0] if leagues_data else 'None'}")
                
                if not leagues_data:
                    print(f"No Yahoo leagues found for user {user_id}")
                    return True  # Not an error, user might not have leagues
                
                for league_data in leagues_data:
                    # Extract league key - Yahoo uses league_key format like "423.l.12345"
                    league_key = None
                    if isinstance(league_data, dict):
                        league_key = league_data.get('league_key', '')
                        # Also try alternate key names Yahoo might use
                        if not league_key:
                            league_key = league_data.get('league_id', '')
                    
                    if not league_key:
                        print(f"No league key found in data: {league_data}")
                        continue
                    
                    print(f"Processing Yahoo league: {league_key}")
                    
                    # Process each league
                    try:
                        await _ingest_yahoo_league(api, db, user, league_key, league_data)
                    except Exception as e:
                        print(f"Error processing league {league_key}: {e}")
                        continue
                
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
            season=int(league_data.get('season', datetime.now(timezone.utc).year)),
            week=int(league_data.get('current_week', 1)),
            num_teams=int(league_data.get('num_teams', 0)),
            scoring_type=_determine_yahoo_scoring_type(detailed_league_data.get('settings', {})),
        )
        db.add(league)
        await db.flush()  # Get the ID
    else:
        # Update existing league
        league.name = league_data.get('name', league.name)
        league.week = int(league_data.get('current_week', league.week))
        league.num_teams = int(league_data.get('num_teams', league.num_teams))
    
    # Ingest teams/rosters (non-blocking - Yahoo XML parsing may fail)
    try:
        await _ingest_yahoo_teams(api, db, league, league_key)
    except Exception as e:
        print(f"Error ingesting Yahoo teams (non-blocking): {e}")

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
    league.last_sync_at = datetime.now(timezone.utc)


def _extract_teams_from_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract team list from Yahoo's nested XML response structure."""
    league_data = response.get('league', {})
    if isinstance(league_data, list):
        for item in league_data:
            if isinstance(item, dict) and 'teams' in item:
                teams_container = item['teams']
                return YahooAPI._ensure_list(teams_container.get('team'))
    elif isinstance(league_data, dict):
        teams_container = league_data.get('teams', {})
        if isinstance(teams_container, dict):
            return YahooAPI._ensure_list(teams_container.get('team'))
    return YahooAPI._ensure_list(response.get('teams', {}).get('team'))


def _extract_standings_from_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract standings list from Yahoo's nested XML response structure."""
    league_data = response.get('league', {})
    if isinstance(league_data, list):
        for item in league_data:
            if isinstance(item, dict) and 'standings' in item:
                standings_container = item['standings']
                if isinstance(standings_container, dict):
                    teams = standings_container.get('teams', {})
                    if isinstance(teams, dict):
                        return YahooAPI._ensure_list(teams.get('team'))
    elif isinstance(league_data, dict):
        standings_container = league_data.get('standings', {})
        if isinstance(standings_container, dict):
            teams = standings_container.get('teams', {})
            if isinstance(teams, dict):
                return YahooAPI._ensure_list(teams.get('team'))
    return []


async def _ingest_yahoo_teams(
    api: YahooAPI,
    db: AsyncSession,
    league: League,
    league_key: str
):
    """Ingest team/roster data from Yahoo."""
    teams_response = await api.get_teams(league_key)
    standings_response = await api.get_standings(league_key)

    teams_list = _extract_teams_from_response(teams_response)
    standings_list = _extract_standings_from_response(standings_response)

    standings_lookup = {}
    for standing in standings_list:
        team_key = YahooAPI._safe_get(standing, 'team_key')
        if team_key:
            standings_lookup[team_key] = standing

    for team_data in teams_list:
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
        
        roster.team_name = team_data.get('name')
        manager = YahooAPI._safe_get(team_data, 'manager', {})
        roster.owner_name = YahooAPI._safe_get(manager, 'nickname')

        standing = standings_lookup.get(team_key, {})
        outcome_totals = YahooAPI._safe_get(standing, 'outcome_totals', {})

        roster.wins = int(YahooAPI._safe_get(outcome_totals, 'wins', 0))
        roster.losses = int(YahooAPI._safe_get(outcome_totals, 'losses', 0))
        roster.ties = int(YahooAPI._safe_get(outcome_totals, 'ties', 0))
        roster.points_for = float(YahooAPI._safe_get(standing, 'points_for', 0))
        roster.points_against = float(YahooAPI._safe_get(standing, 'points_against', 0))
        
        # Store current roster (would need separate API call for detailed roster)
        # For now, just store the team key
        roster.starters = json.dumps([team_key])


def _extract_matchups_from_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract matchup list from Yahoo's nested scoreboard response."""
    league_data = response.get('league', {})
    if isinstance(league_data, list):
        for item in league_data:
            if isinstance(item, dict) and 'scoreboard' in item:
                scoreboard = item['scoreboard']
                if isinstance(scoreboard, dict):
                    matchups = scoreboard.get('matchups', {})
                    if isinstance(matchups, dict):
                        return YahooAPI._ensure_list(matchups.get('matchup'))
    elif isinstance(league_data, dict):
        scoreboard = league_data.get('scoreboard', {})
        if isinstance(scoreboard, dict):
            matchups = scoreboard.get('matchups', {})
            if isinstance(matchups, dict):
                return YahooAPI._ensure_list(matchups.get('matchup'))
    return []


def _extract_teams_from_matchup(matchup_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract teams list from a matchup dict."""
    teams_container = matchup_data.get('teams', {})
    if isinstance(teams_container, dict):
        return YahooAPI._ensure_list(teams_container.get('team'))
    return YahooAPI._ensure_list(teams_container)


async def _ingest_yahoo_matchups(
    api: YahooAPI,
    db: AsyncSession,
    league: League,
    league_key: str,
    week: int
):
    """Ingest matchup data for a specific week."""
    try:
        scoreboard_response = await api.get_scoreboard(league_key, week)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return
        raise

    matchups_list = _extract_matchups_from_response(scoreboard_response)

    for matchup_data in matchups_list:
        teams = _extract_teams_from_matchup(matchup_data)
        if len(teams) != 2:
            continue

        team1, team2 = teams[0], teams[1]
        team1_key = YahooAPI._safe_get(team1, 'team_key', '')
        team2_key = YahooAPI._safe_get(team2, 'team_key', '')
        provider_matchup_id = f"{league_key}_{week}_{team1_key}_{team2_key}"
        
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
        
        matchup.team1_roster_id = team1_key
        team1_points = YahooAPI._safe_get(team1, 'team_points', {})
        team1_projected = YahooAPI._safe_get(team1, 'team_projected_points', {})
        matchup.team1_points = float(YahooAPI._safe_get(team1_points, 'total', 0))
        matchup.team1_projected = float(YahooAPI._safe_get(team1_projected, 'total', 0))

        matchup.team2_roster_id = team2_key
        team2_points = YahooAPI._safe_get(team2, 'team_points', {})
        team2_projected = YahooAPI._safe_get(team2, 'team_projected_points', {})
        matchup.team2_points = float(YahooAPI._safe_get(team2_points, 'total', 0))
        matchup.team2_projected = float(YahooAPI._safe_get(team2_projected, 'total', 0))
        
        # Determine winner
        if matchup.team1_points > 0 or matchup.team2_points > 0:
            matchup.is_complete = True
            if matchup.team1_points > matchup.team2_points:
                matchup.winner_roster_id = matchup.team1_roster_id
                matchup.margin_of_victory = matchup.team1_points - matchup.team2_points
            elif matchup.team2_points > matchup.team1_points:
                matchup.winner_roster_id = matchup.team2_roster_id
                matchup.margin_of_victory = matchup.team2_points - matchup.team1_points


def _extract_transactions_from_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract transactions list from Yahoo's nested response."""
    league_data = response.get('league', {})
    if isinstance(league_data, list):
        for item in league_data:
            if isinstance(item, dict) and 'transactions' in item:
                trans_container = item['transactions']
                if isinstance(trans_container, dict):
                    return YahooAPI._ensure_list(trans_container.get('transaction'))
    elif isinstance(league_data, dict):
        trans_container = league_data.get('transactions', {})
        if isinstance(trans_container, dict):
            return YahooAPI._ensure_list(trans_container.get('transaction'))
    return []


def _extract_players_from_transaction(trans_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract players list from a transaction dict."""
    players_container = trans_data.get('players', {})
    if isinstance(players_container, dict):
        return YahooAPI._ensure_list(players_container.get('player'))
    return YahooAPI._ensure_list(players_container)


async def _ingest_yahoo_transactions(
    api: YahooAPI,
    db: AsyncSession,
    league: League,
    league_key: str
):
    """Ingest transaction data from Yahoo."""
    transactions_response = await api.get_transactions(league_key)
    transactions_list = _extract_transactions_from_response(transactions_response)

    for trans_data in transactions_list:
        transaction_key = YahooAPI._safe_get(trans_data, 'transaction_key')
        if not transaction_key:
            continue

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
                week=YahooAPI._safe_get(trans_data, 'week', 1),
            )
            db.add(transaction)

        trans_type = str(YahooAPI._safe_get(trans_data, 'type', 'add/drop'))
        if 'trade' in trans_type.lower():
            transaction.transaction_type = TransactionType.TRADE
        elif 'add' in trans_type.lower():
            transaction.transaction_type = TransactionType.ADD
        elif 'drop' in trans_type.lower():
            transaction.transaction_type = TransactionType.DROP
        else:
            transaction.transaction_type = TransactionType.WAIVER

        status = str(YahooAPI._safe_get(trans_data, 'status', 'successful'))
        if status == 'successful':
            transaction.status = TransactionStatus.COMPLETED
        elif status == 'pending':
            transaction.status = TransactionStatus.PENDING
        else:
            transaction.status = TransactionStatus.FAILED

        players = _extract_players_from_transaction(trans_data)
        if players:
            for player in players:
                player_trans_data = YahooAPI._safe_get(player, 'transaction_data', {})
                if player_trans_data:
                    # For ADDs, use destination_team_key; for DROPs, use source_team_key
                    roster_id = YahooAPI._safe_get(player_trans_data, 'destination_team_key')
                    if not roster_id:
                        roster_id = YahooAPI._safe_get(player_trans_data, 'source_team_key')
                    if roster_id:
                        transaction.roster_id = roster_id
                        break

        transaction.players_added = json.dumps([
            p for p in players
            if YahooAPI._safe_get(YahooAPI._safe_get(p, 'transaction_data', {}), 'type') == 'add'
        ])
        transaction.players_dropped = json.dumps([
            p for p in players
            if YahooAPI._safe_get(YahooAPI._safe_get(p, 'transaction_data', {}), 'type') == 'drop'
        ])

        timestamp = YahooAPI._safe_get(trans_data, 'timestamp')
        if timestamp:
            transaction.processed_at = datetime.fromtimestamp(int(timestamp))


async def _refresh_yahoo_token(db: AsyncSession, user: User) -> bool:
    """Refresh Yahoo OAuth token."""
    if not user.yahoo_refresh_token:
        return False
    
    try:
        # Make refresh token request (bypass SSL in debug mode for corporate network)
        verify_ssl = not settings.debug
        async with httpx.AsyncClient(verify=verify_ssl) as client:
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
                    user.yahoo_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data['expires_in'])
                
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
