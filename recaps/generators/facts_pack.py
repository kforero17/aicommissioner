"""Immutable fact dataclasses for the Facts-First, LLM-Last architecture.

These frozen dataclasses represent the structured facts that are:
1. Extracted from WeeklySummary data
2. Passed to deterministic rendering templates
3. Serialized as JSON for LLM prompts

Using frozen=True ensures immutability, and tuples instead of lists
ensures the collections cannot be modified after creation.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TeamFact:
    """Immutable fact about a team.

    Attributes:
        team_name: Display name of the team
        owner_name: Name of the team owner/manager
        record: Win-loss record string (e.g., "5-2" or "5-2-1")
        points_for: Total points scored this season
        points_against: Total points allowed this season
    """
    team_name: str
    owner_name: str
    record: str
    points_for: float
    points_against: float


@dataclass(frozen=True)
class MatchupFact:
    """Immutable fact about a matchup result.

    Attributes:
        winner_team: Name of the winning team
        winner_owner: Name of the winning team's owner
        winner_score: Points scored by the winner
        loser_team: Name of the losing team
        loser_owner: Name of the losing team's owner
        loser_score: Points scored by the loser
        margin: Point differential (winner_score - loser_score)
    """
    winner_team: str
    winner_owner: str
    winner_score: float
    loser_team: str
    loser_owner: str
    loser_score: float
    margin: float


@dataclass(frozen=True)
class PowerRankingFact:
    """Immutable fact about a power ranking entry.

    Attributes:
        rank: Current power ranking position (1 = best)
        team_name: Display name of the team
        owner_name: Name of the team owner/manager
        record: Win-loss record string (e.g., "5-2" or "5-2-1")
        wins: Number of wins
        losses: Number of losses
        ties: Number of ties
        power_score: Calculated power score value
        movement: Change in rank from previous week (+/- positions)
        trend: Direction indicator ("up", "down", "same")
        points_for: Season total points scored
        points_against: Season total points against
        last_week_points: Points scored this week
        season_rank: Standings position (by record/PF)
        streak: Current win/loss streak (e.g., "W3", "L2", "")
    """
    rank: int
    team_name: str
    owner_name: str
    record: str
    wins: int
    losses: int
    ties: int
    power_score: float
    movement: int
    trend: str
    points_for: float
    points_against: float
    last_week_points: float
    season_rank: int
    streak: str


@dataclass(frozen=True)
class TransactionFact:
    """Immutable fact about a transaction.

    Attributes:
        transaction_id: Unique identifier for the transaction
        team_name: Name of the team making the transaction
        owner_name: Name of the team owner
        transaction_type: Type of transaction (waiver, trade, add, drop, free_agent)
        players_added: Tuple of player names added
        players_dropped: Tuple of player names dropped
        faab_spent: FAAB dollars spent (None if not applicable)
        timestamp: ISO timestamp of the transaction (None if not available)
    """
    transaction_id: int
    team_name: str
    owner_name: str
    transaction_type: str
    players_added: tuple[str, ...]
    players_dropped: tuple[str, ...]
    faab_spent: Optional[int]
    timestamp: Optional[str]


@dataclass(frozen=True)
class StoryPick:
    """A highlighted team for the recap narrative.

    Story picks are derived narrative hooks that highlight interesting
    teams based on their weekly performance or ranking changes.

    Attributes:
        team_name: Display name of the highlighted team
        owner_name: Name of the team owner/manager
        reason: Short explanation for the pick
        stat: Key stat backing the pick
    """
    team_name: str
    owner_name: str
    reason: str
    stat: str


@dataclass(frozen=True)
class WaiverStoryPick:
    """A highlighted transaction for the waiver recap narrative.

    Waiver story picks are derived narrative hooks that highlight interesting
    transactions based on FAAB spending, activity level, or notable pickups.

    Attributes:
        transaction_id: ID of the highlighted transaction
        team_name: Display name of the team
        owner_name: Name of the team owner/manager
        reason: Short explanation for the pick
        stat: Key stat backing the pick
    """
    transaction_id: int
    team_name: str
    owner_name: str
    reason: str
    stat: str


@dataclass(frozen=True)
class PowerRankingsFactsPack:
    """Immutable facts pack for power rankings recap.

    Contains all facts needed to generate a power rankings recap,
    including the full rankings, notable movements, week results,
    and derived story picks for narrative hooks.

    Attributes:
        league_name: Name of the fantasy league
        week: Week number for this recap
        season: Season year
        rankings: Tuple of all power ranking entries
        biggest_climber: Team with largest positive rank change
        biggest_faller: Team with largest negative rank change
        highest_scorer: Matchup fact for the week's highest scorer
        lowest_scorer_team: Name of the lowest scoring team
        lowest_scorer_points: Points scored by the lowest scorer
        biggest_blowout: Matchup with largest margin of victory
        closest_matchup: Matchup with smallest margin of victory
        average_score: League average score for the week
        total_points: Total points scored across all teams
        team_of_week: Highest scorer this week
        top_riser: Biggest rank improvement
        biggest_fall: Biggest rank drop
        fraud_watch: High rank but recent struggles
        all_team_names: Every valid team name for LLM validation
        all_numbers: Every number in the facts for LLM validation
    """
    league_name: str
    week: int
    season: int

    # Rankings
    rankings: tuple[PowerRankingFact, ...]

    # Notable movements
    biggest_climber: Optional[PowerRankingFact]
    biggest_faller: Optional[PowerRankingFact]

    # Week results
    highest_scorer: Optional[MatchupFact]
    lowest_scorer_team: Optional[str]
    lowest_scorer_points: Optional[float]
    biggest_blowout: Optional[MatchupFact]
    closest_matchup: Optional[MatchupFact]

    # Stats
    average_score: float
    total_points: float

    # Story picks (derived narrative hooks)
    team_of_week: Optional[StoryPick]
    top_riser: Optional[StoryPick]
    biggest_fall: Optional[StoryPick]
    fraud_watch: Optional[StoryPick]

    # Validation data (for LLM output checking)
    all_team_names: tuple[str, ...]
    all_numbers: tuple[float, ...]


@dataclass(frozen=True)
class WaiverFactsPack:
    """Immutable facts pack for waiver recap.

    Contains all facts needed to generate a waiver wire recap,
    including all transactions, spending statistics, story picks,
    positional analysis, and validation data.

    Attributes:
        league_name: Name of the fantasy league
        week: Week number for this recap
        season: Season year
        transactions: Tuple of all transaction facts
        total_faab_spent: Total FAAB dollars spent this week
        transaction_count: Number of transactions this week
        most_active_trader: Owner with most transactions (if any)
        big_spenders: Transactions with FAAB >= 20
        biggest_spend: Story pick for highest FAAB bid
        bargain_hunter: Story pick for lowest successful FAAB bid ($1-5)
        most_active: Story pick for team with most transactions
        qb_adds: Number of QB additions
        rb_adds: Number of RB additions
        wr_adds: Number of WR additions
        te_adds: Number of TE additions
        dst_adds: Number of D/ST additions
        k_adds: Number of K additions
        all_team_names: All valid team names for LLM validation
        all_player_names: All valid player names for LLM validation
        all_faab_values: All valid FAAB values for LLM validation
    """
    league_name: str
    week: int
    season: int

    # Transactions
    transactions: tuple[TransactionFact, ...]

    # Stats
    total_faab_spent: int
    transaction_count: int
    most_active_trader: Optional[str]

    # Big spenders (FAAB >= 20)
    big_spenders: tuple[TransactionFact, ...]

    # Story picks (derived narrative hooks)
    biggest_spend: Optional[WaiverStoryPick]
    bargain_hunter: Optional[WaiverStoryPick]
    most_active: Optional[WaiverStoryPick]

    # Positional analysis
    qb_adds: int
    rb_adds: int
    wr_adds: int
    te_adds: int
    dst_adds: int
    k_adds: int

    # Validation data (for LLM output checking)
    all_team_names: tuple[str, ...]
    all_player_names: tuple[str, ...]
    all_faab_values: tuple[int, ...]


@dataclass(frozen=True)
class MatchupResultFact:
    """Immutable fact about a single matchup result.

    Attributes:
        matchup_id: Unique identifier for this matchup within the week
        winner_team: Name of the winning team
        winner_owner: Name of the winning team's owner
        winner_score: Points scored by the winner
        winner_projected: Projected points for the winner
        loser_team: Name of the losing team
        loser_owner: Name of the losing team's owner
        loser_score: Points scored by the loser
        loser_projected: Projected points for the loser
        margin: Point differential (winner_score - loser_score)
        combined_score: Total points in matchup (winner + loser)
        was_upset: True if underdog (lower projected) won
        projection_beat: How much winner exceeded their projection
    """
    matchup_id: int
    winner_team: str
    winner_owner: str
    winner_score: float
    winner_projected: float
    loser_team: str
    loser_owner: str
    loser_score: float
    loser_projected: float
    margin: float
    combined_score: float
    was_upset: bool
    projection_beat: float


@dataclass(frozen=True)
class WeeklyStoryPrimitive:
    """A pre-computed story hook for the LLM to use.

    These are the 'building blocks' of narratives - the LLM can
    reference these but shouldn't invent new stories. Story primitives
    ensure that narrative elements are grounded in actual facts.

    Attributes:
        story_type: Category of story (e.g., "blowout", "nail_biter", "upset", "explosion")
        headline: Short attention-grabbing headline
        team_name: Primary team involved in the story
        owner_name: Owner of the primary team
        description: 1-2 sentence explanation of the story
        key_stat: The number that backs up the story
    """
    story_type: str
    headline: str
    team_name: str
    owner_name: str
    description: str
    key_stat: str


@dataclass(frozen=True)
class WeeklyRecapFactsPack:
    """Immutable facts pack for weekly recap.

    Contains all facts needed for a comprehensive weekly recap,
    including matchup results, story primitives, and validation data.
    The key innovation here is 'story primitives' - pre-computed
    narrative hooks that the LLM must choose from rather than invent.

    Attributes:
        league_name: Name of the fantasy league
        week: Week number for this recap
        season: Season year
        matchups: Tuple of all matchup results
        total_points: Total points scored across all teams
        average_score: League average score for the week
        median_score: Median score for the week
        high_score: Highest individual score
        low_score: Lowest individual score
        story_primitives: Pre-computed story hooks (LLM picks from these)
        game_of_week: Closest margin matchup
        blowout_of_week: Biggest margin matchup
        highest_scoring_matchup: Most combined points matchup
        team_of_week: Highest scorer team name
        team_of_week_score: Highest scorer's points
        dud_of_week: Lowest scorer team name
        dud_of_week_score: Lowest scorer's points
        upset_count: Number of upsets this week
        upsets: Tuple of upset matchups
        all_team_names: Every valid team name for LLM validation
        all_scores: Every score value for LLM validation
        all_margins: Every margin value for LLM validation
    """
    league_name: str
    week: int
    season: int

    # All matchup results
    matchups: tuple[MatchupResultFact, ...]

    # League stats
    total_points: float
    average_score: float
    median_score: float
    high_score: float
    low_score: float

    # Pre-computed story primitives (LLM picks from these)
    story_primitives: tuple[WeeklyStoryPrimitive, ...]

    # Key highlights (always include)
    game_of_week: Optional[MatchupResultFact]
    blowout_of_week: Optional[MatchupResultFact]
    highest_scoring_matchup: Optional[MatchupResultFact]
    team_of_week: Optional[str]
    team_of_week_score: Optional[float]
    dud_of_week: Optional[str]
    dud_of_week_score: Optional[float]

    # Upset tracking
    upset_count: int
    upsets: tuple[MatchupResultFact, ...]

    # Validation data
    all_team_names: tuple[str, ...]
    all_scores: tuple[float, ...]
    all_margins: tuple[float, ...]
