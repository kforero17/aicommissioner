"""AI text generation for fantasy sports recaps and summaries."""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.league import League
from models.roster import Roster
from models.matchup import Matchup
from models.transaction import Transaction


@dataclass
class WeeklyPerformance:
    """Weekly performance data for a team."""
    roster_id: str
    team_name: str
    owner_name: str
    points_scored: float
    points_projected: float
    win: bool
    opponent_name: str
    opponent_points: float
    margin: float


@dataclass
class PowerRankingEntry:
    """Power ranking entry for a team."""
    rank: int
    previous_rank: Optional[int]
    roster_id: str
    team_name: str
    owner_name: str
    record: str
    points_for: float
    points_against: float
    power_score: float
    trend: str  # "up", "down", "same"
    movement: int  # +/- positions


@dataclass
class TransactionSummary:
    """Summary of a transaction for recaps."""
    transaction_type: str
    team_name: str
    owner_name: str
    players_added: List[str]
    players_dropped: List[str]
    faab_spent: Optional[int]
    notes: str


@dataclass
class WeeklySummary:
    """Complete weekly summary data structure."""
    league_name: str
    week: int
    season: int
    
    # Performance data
    performances: List[WeeklyPerformance]
    highest_scorer: WeeklyPerformance
    lowest_scorer: WeeklyPerformance
    biggest_blowout: tuple[WeeklyPerformance, WeeklyPerformance]  # winner, loser
    closest_matchup: tuple[WeeklyPerformance, WeeklyPerformance]
    
    # Power rankings
    power_rankings: List[PowerRankingEntry]
    biggest_climber: Optional[PowerRankingEntry]
    biggest_fall: Optional[PowerRankingEntry]
    
    # Transactions
    transactions: List[TransactionSummary]
    total_faab_spent: int
    most_active_trader: Optional[str]
    
    # League stats
    average_score: float
    total_points: float
    playoff_picture: List[str]  # Team names in playoff positions


class SummaryGenerator:
    """Generate structured summaries from league data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_weekly_summary(
        self, 
        league_id: int, 
        week: int
    ) -> WeeklySummary:
        """Generate a complete weekly summary for a league."""
        # Get league
        result = await self.db.execute(select(League).filter(League.id == league_id))
        league = result.scalar_one_or_none()
        if not league:
            raise ValueError(f"League {league_id} not found")
        
        # Get performances
        performances = await self._get_weekly_performances(league_id, week)
        
        # Calculate performance stats
        highest_scorer = max(performances, key=lambda p: p.points_scored)
        lowest_scorer = min(performances, key=lambda p: p.points_scored)
        
        # Find biggest blowout and closest matchup
        blowouts = [(p, next((p2 for p2 in performances if p2.roster_id != p.roster_id and p2.opponent_name == p.team_name), None)) 
                   for p in performances if p.win]
        blowouts = [(p1, p2) for p1, p2 in blowouts if p2 is not None]
        
        biggest_blowout = max(blowouts, key=lambda x: x[0].margin) if blowouts else (performances[0], performances[1])
        closest_matchup = min(blowouts, key=lambda x: x[0].margin) if blowouts else (performances[0], performances[1])
        
        # Get power rankings
        power_rankings = await self._calculate_power_rankings(league_id, week)
        
        # Find biggest movements
        climbers = [pr for pr in power_rankings if pr.movement > 0]
        fallers = [pr for pr in power_rankings if pr.movement < 0]
        
        biggest_climber = max(climbers, key=lambda pr: pr.movement) if climbers else None
        biggest_fall = max(fallers, key=lambda pr: abs(pr.movement)) if fallers else None
        
        # Get transactions
        transactions = await self._get_weekly_transactions(league_id, week)
        
        # Calculate transaction stats
        total_faab_spent = sum(t.faab_spent or 0 for t in transactions)
        transaction_counts = {}
        for t in transactions:
            transaction_counts[t.owner_name] = transaction_counts.get(t.owner_name, 0) + 1
        
        most_active_trader = max(transaction_counts.items(), key=lambda x: x[1])[0] if transaction_counts else None
        
        # Calculate league stats
        total_points = sum(p.points_scored for p in performances)
        average_score = total_points / len(performances) if performances else 0
        
        # Get playoff picture (top 6 teams by record, then by points)
        sorted_rankings = sorted(power_rankings, key=lambda pr: pr.rank)
        playoff_picture = [pr.team_name for pr in sorted_rankings[:6]]
        
        return WeeklySummary(
            league_name=league.name,
            week=week,
            season=league.season,
            performances=performances,
            highest_scorer=highest_scorer,
            lowest_scorer=lowest_scorer,
            biggest_blowout=biggest_blowout,
            closest_matchup=closest_matchup,
            power_rankings=power_rankings,
            biggest_climber=biggest_climber,
            biggest_fall=biggest_fall,
            transactions=transactions,
            total_faab_spent=total_faab_spent,
            most_active_trader=most_active_trader,
            average_score=average_score,
            total_points=total_points,
            playoff_picture=playoff_picture
        )
    
    async def _get_weekly_performances(
        self, 
        league_id: int, 
        week: int
    ) -> List[WeeklyPerformance]:
        """Get weekly performance data for all teams."""
        # Get matchups for the week
        result = await self.db.execute(
            select(Matchup).filter(
                Matchup.league_id == league_id,
                Matchup.week == week
            )
        )
        matchups = result.scalars().all()
        
        # Get rosters for team names
        result = await self.db.execute(
            select(Roster).filter(Roster.league_id == league_id)
        )
        rosters = {r.provider_roster_id: r for r in result.scalars().all()}
        
        performances = []
        
        for matchup in matchups:
            if not matchup.team2_roster_id:  # Bye week
                continue
            
            team1_roster = rosters.get(matchup.team1_roster_id)
            team2_roster = rosters.get(matchup.team2_roster_id)
            
            if not team1_roster or not team2_roster:
                continue
            
            # Team 1 performance
            team1_win = matchup.winner_roster_id == matchup.team1_roster_id
            performances.append(WeeklyPerformance(
                roster_id=matchup.team1_roster_id,
                team_name=team1_roster.team_name or f"Team {matchup.team1_roster_id}",
                owner_name=team1_roster.owner_name or "Unknown",
                points_scored=matchup.team1_points or 0,
                points_projected=matchup.team1_projected or 0,
                win=team1_win,
                opponent_name=team2_roster.team_name or f"Team {matchup.team2_roster_id}",
                opponent_points=matchup.team2_points or 0,
                margin=abs((matchup.team1_points or 0) - (matchup.team2_points or 0))
            ))
            
            # Team 2 performance
            team2_win = matchup.winner_roster_id == matchup.team2_roster_id
            performances.append(WeeklyPerformance(
                roster_id=matchup.team2_roster_id,
                team_name=team2_roster.team_name or f"Team {matchup.team2_roster_id}",
                owner_name=team2_roster.owner_name or "Unknown",
                points_scored=matchup.team2_points or 0,
                points_projected=matchup.team2_projected or 0,
                win=team2_win,
                opponent_name=team1_roster.team_name or f"Team {matchup.team1_roster_id}",
                opponent_points=matchup.team1_points or 0,
                margin=abs((matchup.team2_points or 0) - (matchup.team1_points or 0))
            ))
        
        return performances
    
    async def _calculate_power_rankings(
        self, 
        league_id: int, 
        week: int
    ) -> List[PowerRankingEntry]:
        """Calculate power rankings for teams."""
        # Get all rosters
        result = await self.db.execute(
            select(Roster).filter(Roster.league_id == league_id)
        )
        rosters = result.scalars().all()
        
        rankings = []
        
        for roster in rosters:
            # Calculate power score (points for + win% * 100)
            total_games = roster.wins + roster.losses + roster.ties
            win_percentage = roster.wins / total_games if total_games > 0 else 0
            power_score = roster.points_for + (win_percentage * 100)
            
            # Create ranking entry
            current_rank = roster.power_rank or len(rosters)
            previous_rank = roster.power_rank_previous
            
            rankings.append(PowerRankingEntry(
                rank=current_rank,
                previous_rank=previous_rank,
                roster_id=roster.provider_roster_id,
                team_name=roster.team_name or f"Team {roster.provider_roster_id}",
                owner_name=roster.owner_name or "Unknown",
                record=f"{roster.wins}-{roster.losses}" + (f"-{roster.ties}" if roster.ties > 0 else ""),
                points_for=roster.points_for,
                points_against=roster.points_against,
                power_score=power_score,
                trend="same",
                movement=0
            ))
        
        # Sort by power score and assign ranks
        rankings.sort(key=lambda r: r.power_score, reverse=True)
        
        for i, ranking in enumerate(rankings):
            new_rank = i + 1
            old_rank = ranking.previous_rank or new_rank
            
            ranking.rank = new_rank
            ranking.movement = old_rank - new_rank  # Positive = moved up
            
            if ranking.movement > 0:
                ranking.trend = "up"
            elif ranking.movement < 0:
                ranking.trend = "down"
            else:
                ranking.trend = "same"
        
        return rankings
    
    async def _get_weekly_transactions(
        self, 
        league_id: int, 
        week: int
    ) -> List[TransactionSummary]:
        """Get transaction summaries for the week."""
        # Get transactions for the week
        result = await self.db.execute(
            select(Transaction).filter(
                Transaction.league_id == league_id,
                Transaction.week == week
            )
        )
        transactions = result.scalars().all()
        
        # Get rosters for team names
        result = await self.db.execute(
            select(Roster).filter(Roster.league_id == league_id)
        )
        rosters = {r.provider_roster_id: r for r in result.scalars().all()}
        
        summaries = []
        
        for transaction in transactions:
            roster = rosters.get(transaction.roster_id)
            team_name = roster.team_name if roster else f"Team {transaction.roster_id}"
            owner_name = roster.owner_name if roster else "Unknown"
            
            # Parse player data
            players_added = []
            players_dropped = []
            
            if transaction.players_added:
                try:
                    added_data = json.loads(transaction.players_added)
                    players_added = [self._format_player_name(p) for p in added_data]
                except (json.JSONDecodeError, TypeError):
                    players_added = ["Unknown Player"]
            
            if transaction.players_dropped:
                try:
                    dropped_data = json.loads(transaction.players_dropped)
                    players_dropped = [self._format_player_name(p) for p in dropped_data]
                except (json.JSONDecodeError, TypeError):
                    players_dropped = ["Unknown Player"]
            
            # Generate notes
            notes = self._generate_transaction_notes(
                transaction.transaction_type.value,
                players_added,
                players_dropped,
                transaction.faab_bid
            )
            
            summaries.append(TransactionSummary(
                transaction_type=transaction.transaction_type.value,
                team_name=team_name,
                owner_name=owner_name,
                players_added=players_added,
                players_dropped=players_dropped,
                faab_spent=transaction.faab_bid,
                notes=notes
            ))
        
        return summaries
    
    def _format_player_name(self, player_data: Any) -> str:
        """Format player name from API data."""
        if isinstance(player_data, dict):
            return player_data.get('name', player_data.get('full_name', 'Unknown Player'))
        elif isinstance(player_data, str):
            return player_data
        else:
            return "Unknown Player"
    
    def _generate_transaction_notes(
        self, 
        transaction_type: str, 
        added: List[str], 
        dropped: List[str], 
        faab: Optional[int]
    ) -> str:
        """Generate descriptive notes for a transaction."""
        if transaction_type == "trade":
            return f"Traded {', '.join(dropped)} for {', '.join(added)}"
        elif transaction_type == "waiver":
            faab_text = f" for ${faab}" if faab else ""
            return f"Picked up {', '.join(added)}{faab_text}, dropped {', '.join(dropped)}"
        elif transaction_type == "add":
            return f"Added {', '.join(added)}"
        elif transaction_type == "drop":
            return f"Dropped {', '.join(dropped)}"
        else:
            return f"{transaction_type.title()}: +{', '.join(added)} -{', '.join(dropped)}"
