"""Power Rankings Generator implementing Facts-First, LLM-Last pattern.

This module provides the PowerRankingsGenerator class that:
1. Extracts power rankings facts from WeeklySummary
2. Renders a deterministic text output (always works)
3. Builds an LLM prompt with facts as JSON for enhanced output
4. Validates LLM output against facts to prevent hallucination
5. Supports two-phase LLM: JSON plan -> Python rendering
"""
import json
import logging
import re
import time
from dataclasses import asdict
from typing import Optional, Any

from ai_text.summary_generator import WeeklySummary, WeeklyPerformance
from recaps.generators.base import BaseGenerator, GeneratorResult, RenderingMode
from recaps.generators.facts_pack import (
    PowerRankingsFactsPack,
    PowerRankingFact,
    MatchupFact,
    StoryPick,
)
from recaps.generators.llm_planner import LLMPlanner, RecapPlan, create_planner
from recaps.prompts.personas import get_persona

logger = logging.getLogger(__name__)


class PowerRankingsGenerator(BaseGenerator):
    """Generator for power rankings recaps.

    Implements the Facts-First, LLM-Last pattern:
    - extract_facts(): Converts WeeklySummary to immutable PowerRankingsFactsPack
    - render_deterministic(): Template-based output that always works
    - build_llm_prompt(): Structured prompt with facts as JSON for LLM enhancement

    Supports two-phase LLM generation:
    - Phase 1: LLM produces structured JSON plan
    - Phase 2: Python renders the plan into final text
    """

    def __init__(self):
        """Initialize the generator with a planner instance."""
        self.planner = create_planner()

    def _use_two_phase_llm(self) -> bool:
        """Enable two-phase LLM for this generator."""
        return True

    async def extract_facts(self, summary: WeeklySummary) -> PowerRankingsFactsPack:
        """Extract power rankings facts from WeeklySummary.

        Transforms the mutable WeeklySummary into an immutable PowerRankingsFactsPack
        containing all facts needed for the power rankings recap, including derived
        story picks and validation data.

        Args:
            summary: The weekly summary data from the league

        Returns:
            A frozen PowerRankingsFactsPack dataclass with all ranking facts
        """
        # Build lookup for weekly performance by team name
        perf_by_team: dict[str, WeeklyPerformance] = {
            p.team_name: p for p in summary.performances
        }

        # Calculate season ranks (by record, then points for)
        sorted_by_standings = sorted(
            summary.power_rankings,
            key=lambda pr: (
                self._parse_record(pr.record)[0],  # wins
                pr.points_for,
            ),
            reverse=True,
        )
        season_rank_map = {pr.team_name: i + 1 for i, pr in enumerate(sorted_by_standings)}

        # Collect all numbers for validation
        all_numbers: list[float] = []

        # Convert power rankings to immutable facts
        rankings_list: list[PowerRankingFact] = []
        for pr in summary.power_rankings:
            wins, losses, ties = self._parse_record(pr.record)
            perf = perf_by_team.get(pr.team_name)
            last_week_pts = round(perf.points_scored, 2) if perf else 0.0
            streak = self._calculate_streak(perf) if perf else ""

            ranking_fact = PowerRankingFact(
                rank=pr.rank,
                team_name=pr.team_name,
                owner_name=pr.owner_name,
                record=pr.record,
                wins=wins,
                losses=losses,
                ties=ties,
                power_score=round(pr.power_score, 2),
                movement=pr.movement,
                trend=pr.trend,
                points_for=round(pr.points_for, 2),
                points_against=round(pr.points_against, 2),
                last_week_points=last_week_pts,
                season_rank=season_rank_map.get(pr.team_name, pr.rank),
                streak=streak,
            )
            rankings_list.append(ranking_fact)

            # Collect numbers for validation
            all_numbers.extend([
                float(pr.rank),
                float(wins),
                float(losses),
                float(ties),
                round(pr.power_score, 2),
                float(abs(pr.movement)),
                round(pr.points_for, 2),
                round(pr.points_against, 2),
                last_week_pts,
                float(season_rank_map.get(pr.team_name, pr.rank)),
            ])

        rankings = tuple(rankings_list)

        # Extract biggest climber (team with largest positive rank change)
        biggest_climber: Optional[PowerRankingFact] = None
        if summary.biggest_climber:
            bc = summary.biggest_climber
            bc_perf = perf_by_team.get(bc.team_name)
            bc_wins, bc_losses, bc_ties = self._parse_record(bc.record)
            biggest_climber = PowerRankingFact(
                rank=bc.rank,
                team_name=bc.team_name,
                owner_name=bc.owner_name,
                record=bc.record,
                wins=bc_wins,
                losses=bc_losses,
                ties=bc_ties,
                power_score=round(bc.power_score, 2),
                movement=bc.movement,
                trend=bc.trend,
                points_for=round(bc.points_for, 2),
                points_against=round(bc.points_against, 2),
                last_week_points=round(bc_perf.points_scored, 2) if bc_perf else 0.0,
                season_rank=season_rank_map.get(bc.team_name, bc.rank),
                streak=self._calculate_streak(bc_perf) if bc_perf else "",
            )

        # Extract biggest faller (team with largest negative rank change)
        biggest_faller: Optional[PowerRankingFact] = None
        if summary.biggest_fall:
            bf = summary.biggest_fall
            bf_perf = perf_by_team.get(bf.team_name)
            bf_wins, bf_losses, bf_ties = self._parse_record(bf.record)
            biggest_faller = PowerRankingFact(
                rank=bf.rank,
                team_name=bf.team_name,
                owner_name=bf.owner_name,
                record=bf.record,
                wins=bf_wins,
                losses=bf_losses,
                ties=bf_ties,
                power_score=round(bf.power_score, 2),
                movement=bf.movement,
                trend=bf.trend,
                points_for=round(bf.points_for, 2),
                points_against=round(bf.points_against, 2),
                last_week_points=round(bf_perf.points_scored, 2) if bf_perf else 0.0,
                season_rank=season_rank_map.get(bf.team_name, bf.rank),
                streak=self._calculate_streak(bf_perf) if bf_perf else "",
            )

        # Create matchup fact for highest scorer
        highest_scorer: Optional[MatchupFact] = None
        if summary.highest_scorer:
            hs = summary.highest_scorer
            highest_scorer = MatchupFact(
                winner_team=hs.team_name,
                winner_owner=hs.owner_name,
                winner_score=round(hs.points_scored, 2),
                loser_team=hs.opponent_name,
                loser_owner="",  # Not available in WeeklyPerformance
                loser_score=round(hs.opponent_points, 2),
                margin=round(hs.margin, 2),
            )
            all_numbers.extend([
                round(hs.points_scored, 2),
                round(hs.opponent_points, 2),
                round(hs.margin, 2),
            ])

        # Create matchup fact for biggest blowout
        biggest_blowout: Optional[MatchupFact] = None
        if summary.biggest_blowout:
            winner, loser = summary.biggest_blowout
            biggest_blowout = MatchupFact(
                winner_team=winner.team_name,
                winner_owner=winner.owner_name,
                winner_score=round(winner.points_scored, 2),
                loser_team=loser.team_name,
                loser_owner=loser.owner_name,
                loser_score=round(loser.points_scored, 2),
                margin=round(winner.margin, 2),
            )
            all_numbers.extend([
                round(winner.points_scored, 2),
                round(loser.points_scored, 2),
                round(winner.margin, 2),
            ])

        # Create matchup fact for closest matchup
        closest_matchup: Optional[MatchupFact] = None
        if summary.closest_matchup:
            winner, loser = summary.closest_matchup
            closest_matchup = MatchupFact(
                winner_team=winner.team_name,
                winner_owner=winner.owner_name,
                winner_score=round(winner.points_scored, 2),
                loser_team=loser.team_name,
                loser_owner=loser.owner_name,
                loser_score=round(loser.points_scored, 2),
                margin=round(winner.margin, 2),
            )
            all_numbers.extend([
                round(winner.points_scored, 2),
                round(loser.points_scored, 2),
                round(winner.margin, 2),
            ])

        # Extract lowest scorer info
        lowest_scorer_team: Optional[str] = None
        lowest_scorer_points: Optional[float] = None
        if summary.lowest_scorer:
            lowest_scorer_team = summary.lowest_scorer.team_name
            lowest_scorer_points = round(summary.lowest_scorer.points_scored, 2)
            all_numbers.append(lowest_scorer_points)

        # Add stats to numbers
        avg_score = round(summary.average_score, 2)
        total_pts = round(summary.total_points, 2)
        all_numbers.extend([avg_score, total_pts])

        # Derive story picks
        team_of_week = self._derive_team_of_week(summary, rankings)
        top_riser = self._derive_top_riser(rankings)
        biggest_fall_story = self._derive_biggest_fall(rankings)
        fraud_watch = self._derive_fraud_watch(summary, rankings)

        # Collect all team names for validation
        all_team_names = tuple(pr.team_name for pr in rankings)

        return PowerRankingsFactsPack(
            league_name=summary.league_name,
            week=summary.week,
            season=summary.season,
            rankings=rankings,
            biggest_climber=biggest_climber,
            biggest_faller=biggest_faller,
            highest_scorer=highest_scorer,
            lowest_scorer_team=lowest_scorer_team,
            lowest_scorer_points=lowest_scorer_points,
            biggest_blowout=biggest_blowout,
            closest_matchup=closest_matchup,
            average_score=avg_score,
            total_points=total_pts,
            team_of_week=team_of_week,
            top_riser=top_riser,
            biggest_fall=biggest_fall_story,
            fraud_watch=fraud_watch,
            all_team_names=all_team_names,
            all_numbers=tuple(all_numbers),
        )

    def _parse_record(self, record: str) -> tuple[int, int, int]:
        """Parse a record string into wins, losses, ties.

        Args:
            record: Record string like "5-2" or "5-2-1"

        Returns:
            Tuple of (wins, losses, ties)
        """
        parts = record.split("-")
        wins = int(parts[0]) if len(parts) > 0 else 0
        losses = int(parts[1]) if len(parts) > 1 else 0
        ties = int(parts[2]) if len(parts) > 2 else 0
        return wins, losses, ties

    def _calculate_streak(self, perf: Optional[WeeklyPerformance]) -> str:
        """Calculate streak string based on this week's result.

        For a full streak calculation, we would need historical data.
        This returns a simple W/L indicator for the current week.

        Args:
            perf: The weekly performance data

        Returns:
            Streak string like "W1" or "L1", or "" if unknown
        """
        if not perf:
            return ""
        # Since we only have current week data, we return W1/L1
        # A full implementation would track historical results
        return "W1" if perf.win else "L1"

    def _derive_team_of_week(
        self,
        summary: WeeklySummary,
        rankings: tuple[PowerRankingFact, ...]
    ) -> Optional[StoryPick]:
        """Derive team of the week (highest scorer this week).

        Args:
            summary: The weekly summary data
            rankings: Tuple of power ranking facts

        Returns:
            StoryPick for team of the week or None
        """
        if not summary.highest_scorer:
            return None

        hs = summary.highest_scorer
        # Find the ranking entry for this team
        ranking = next((r for r in rankings if r.team_name == hs.team_name), None)

        return StoryPick(
            team_name=hs.team_name,
            owner_name=hs.owner_name,
            reason=f"Led the league with {round(hs.points_scored, 1)} points",
            stat=f"{round(hs.points_scored, 1)} pts",
        )

    def _derive_top_riser(
        self,
        rankings: tuple[PowerRankingFact, ...]
    ) -> Optional[StoryPick]:
        """Derive top riser (biggest rank improvement).

        Args:
            rankings: Tuple of power ranking facts

        Returns:
            StoryPick for top riser or None
        """
        climbers = [r for r in rankings if r.movement > 0]
        if not climbers:
            return None

        top = max(climbers, key=lambda r: r.movement)
        return StoryPick(
            team_name=top.team_name,
            owner_name=top.owner_name,
            reason=f"Jumped {top.movement} spots to #{top.rank}",
            stat=f"+{top.movement} spots",
        )

    def _derive_biggest_fall(
        self,
        rankings: tuple[PowerRankingFact, ...]
    ) -> Optional[StoryPick]:
        """Derive biggest fall (biggest rank drop).

        Args:
            rankings: Tuple of power ranking facts

        Returns:
            StoryPick for biggest fall or None
        """
        fallers = [r for r in rankings if r.movement < 0]
        if not fallers:
            return None

        worst = min(fallers, key=lambda r: r.movement)
        return StoryPick(
            team_name=worst.team_name,
            owner_name=worst.owner_name,
            reason=f"Dropped {abs(worst.movement)} spots to #{worst.rank}",
            stat=f"{worst.movement} spots",
        )

    def _derive_fraud_watch(
        self,
        summary: WeeklySummary,
        rankings: tuple[PowerRankingFact, ...]
    ) -> Optional[StoryPick]:
        """Derive fraud watch (high rank but recent struggles).

        Fraud watch criteria:
        - Rank <= 4 (top 4 team)
        - Lost this week
        - Negative point differential this week

        Args:
            summary: The weekly summary data
            rankings: Tuple of power ranking facts

        Returns:
            StoryPick for fraud watch or None
        """
        # Build lookup for performances
        perf_by_team = {p.team_name: p for p in summary.performances}

        # Find top 4 teams that lost and had negative point differential
        fraud_candidates: list[tuple[PowerRankingFact, WeeklyPerformance]] = []

        for r in rankings:
            if r.rank > 4:
                continue
            perf = perf_by_team.get(r.team_name)
            if not perf:
                continue
            # Lost this week AND negative point differential
            point_diff = perf.points_scored - perf.opponent_points
            if not perf.win and point_diff < 0:
                fraud_candidates.append((r, perf))

        if not fraud_candidates:
            return None

        # Pick the highest-ranked fraud (most embarrassing)
        fraud, perf = min(fraud_candidates, key=lambda x: x[0].rank)
        point_diff = perf.points_scored - perf.opponent_points

        return StoryPick(
            team_name=fraud.team_name,
            owner_name=fraud.owner_name,
            reason=f"Ranked #{fraud.rank} but lost by {abs(round(point_diff, 1))} points",
            stat=f"{round(perf.points_scored, 1)} pts (L)",
        )

    def render_deterministic(self, facts: PowerRankingsFactsPack) -> tuple[str, str]:
        """Render power rankings deterministically using templates.

        Produces a consistent, well-formatted output that does not depend
        on any external services. This serves as both the primary output
        for non-LLM mode and the fallback when LLM generation fails.

        The output is designed to be publication-ready without LLM enhancement.

        Args:
            facts: The PowerRankingsFactsPack extracted from the summary

        Returns:
            Tuple of (title, content) for the recap
        """
        title = f"Power Rankings - {facts.league_name} Week {facts.week}"

        lines: list[str] = []

        # Header
        lines.append(f"Power Rankings - {facts.league_name} Week {facts.week}")
        lines.append("")
        lines.append("THE RANKINGS")
        lines.append("-" * 46)

        # Rankings table with enhanced formatting
        for pr in facts.rankings:
            # Trend emoji
            trend_emoji = {
                "up": "^",
                "down": "v",
                "same": "-",
            }.get(pr.trend, "-")

            # Streak display (only show if non-empty)
            streak_str = f" [{pr.streak}]" if pr.streak else ""

            # Movement string
            if pr.movement > 0:
                movement_str = f"+{pr.movement} spots"
            elif pr.movement < 0:
                movement_str = f"{pr.movement} spots"
            else:
                movement_str = "--"

            # Main ranking line
            lines.append(
                f"{pr.rank}. {trend_emoji} {pr.team_name} ({pr.owner_name}){streak_str}"
            )
            # Stats line (indented)
            lines.append(
                f"   {pr.record} | {pr.last_week_points:.1f} pts | {movement_str}"
            )
            lines.append("")

        # Story picks section
        has_stories = any([
            facts.team_of_week,
            facts.top_riser,
            facts.biggest_fall,
            facts.fraud_watch,
        ])

        if has_stories:
            lines.append("THIS WEEK'S STORIES")
            lines.append("-" * 46)

            if facts.team_of_week:
                tow = facts.team_of_week
                lines.append(f"TEAM OF THE WEEK: {tow.team_name}")
                lines.append(f"   {tow.reason} ({tow.stat})")
                lines.append("")

            if facts.top_riser:
                tr = facts.top_riser
                lines.append(f"BIGGEST RISER: {tr.team_name}")
                lines.append(f"   {tr.reason} ({tr.stat})")
                lines.append("")

            if facts.biggest_fall:
                bf = facts.biggest_fall
                lines.append(f"BIGGEST FALL: {bf.team_name}")
                lines.append(f"   {bf.reason} ({bf.stat})")
                lines.append("")

            if facts.fraud_watch:
                fw = facts.fraud_watch
                lines.append(f"FRAUD WATCH: {fw.team_name}")
                lines.append(f"   {fw.reason} ({fw.stat})")
                lines.append("")

        # Week stats section
        lines.append(f"WEEK {facts.week} STATS")
        lines.append("-" * 46)
        lines.append(f"League Average: {facts.average_score:.1f} pts")

        if facts.highest_scorer:
            hs = facts.highest_scorer
            lines.append(f"High Score: {hs.winner_team} ({hs.winner_score:.1f})")

        if facts.lowest_scorer_team and facts.lowest_scorer_points is not None:
            lines.append(
                f"Low Score: {facts.lowest_scorer_team} ({facts.lowest_scorer_points:.1f})"
            )

        content = "\n".join(lines)
        return title, content

    def build_llm_prompt(self, facts: PowerRankingsFactsPack, persona: str) -> str:
        """Build LLM prompt with facts as JSON.

        Creates a structured prompt that instructs the LLM to generate an
        enhanced power rankings recap using ONLY the facts provided in the
        JSON payload. The prompt includes strict rules to prevent hallucination.

        Args:
            facts: The PowerRankingsFactsPack to include in the prompt
            persona: The desired writing persona/style name

        Returns:
            Complete prompt string for the LLM
        """
        persona_obj = get_persona(persona)
        facts_json = json.dumps(asdict(facts), indent=2, default=str)

        tone_examples = "\n".join(f'- "{ex}"' for ex in persona_obj.tone_examples)

        return f"""You are a fantasy football commissioner writing a Power Rankings recap.

CRITICAL RULES:
1. You may ONLY reference facts from the JSON below
2. DO NOT invent statistics, scores, or player names
3. Every team name, record, and score MUST come from the facts pack
4. If information is not in the facts, do not mention it
5. Never make up matchup results or player performances

PERSONA: {persona_obj.name}
{persona_obj.instructions}

TONE EXAMPLES:
{tone_examples}

FACTS PACK:
```json
{facts_json}
```

Write a power rankings recap that:
- Opens with an engaging title/header
- Highlights the top teams and notable movements
- Mentions the week's biggest winner/loser if interesting
- Uses the persona style throughout
- Is 200-400 words
- Is formatted for a group chat message (not markdown)

DO NOT use asterisks for bold. Use emojis sparingly for emphasis.
"""

    def build_planner_prompt(
        self,
        facts: PowerRankingsFactsPack,
        persona: str
    ) -> str:
        """Build prompt for two-phase planner.

        Creates a prompt that instructs the LLM to return only structured JSON
        describing the recap plan. The JSON will be parsed and validated before
        Python renders the final text.

        Args:
            facts: The PowerRankingsFactsPack extracted from the summary
            persona: The desired writing persona/style name

        Returns:
            Complete prompt string for the LLM planner phase
        """
        persona_obj = get_persona(persona)
        facts_json = json.dumps(asdict(facts), indent=2, default=str)

        return self.planner.build_planner_prompt(
            recap_type="Power Rankings",
            facts_json=facts_json,
            persona_name=persona_obj.name,
            persona_instructions=persona_obj.instructions,
            valid_team_names=list(facts.all_team_names),
            valid_matchup_ids=None,
        )

    def render_from_plan(
        self,
        plan: RecapPlan,
        facts: PowerRankingsFactsPack
    ) -> str:
        """Render validated plan with facts.

        This method takes a validated RecapPlan and renders it into the final
        text output. Python controls the structure and format, ensuring consistency
        while incorporating the LLM-generated blurbs.

        Args:
            plan: The validated RecapPlan from the LLM
            facts: The PowerRankingsFactsPack for fact-based rendering

        Returns:
            The rendered recap text
        """
        lines: list[str] = []

        # Opening hook from plan
        if plan.opening_hook:
            lines.append(plan.opening_hook)
            lines.append("")

        # Theme callout
        if plan.theme:
            lines.append(f"Theme: {plan.theme.upper()}")
            lines.append("")

        # Always include the rankings table (from facts, not LLM)
        lines.append("THE RANKINGS")
        lines.append("-" * 40)

        for pr in facts.rankings:
            trend = {"up": "^", "down": "v", "same": "-"}.get(pr.trend, "-")
            if pr.movement > 0:
                movement = f"+{pr.movement}"
            elif pr.movement < 0:
                movement = str(pr.movement)
            else:
                movement = "--"

            # Find any blurb for this team
            blurb = self._find_team_blurb(plan, pr.team_name)

            lines.append(f"{pr.rank}. {trend} {pr.team_name} ({pr.owner_name})")
            lines.append(f"   {pr.record} | {pr.last_week_points:.1f} pts | {movement}")
            if blurb:
                lines.append(f"   -> {blurb}")
            lines.append("")

        # Render plan sections
        for section in plan.sections:
            if section.title:
                lines.append(section.title.upper())
                lines.append("-" * 40)

            if section.intro_line:
                lines.append(section.intro_line)

            for tb in section.team_blurbs:
                if tb.team_name not in [pr.team_name for pr in facts.rankings]:
                    continue  # Skip invalid teams
                prefix = "* " if tb.emphasis else "- "
                lines.append(f"{prefix}{tb.team_name}: {tb.blurb}")

            lines.append("")

        # Closing
        if plan.closing_line:
            lines.append(plan.closing_line)

        return "\n".join(lines)

    def _find_team_blurb(
        self,
        plan: RecapPlan,
        team_name: str
    ) -> Optional[str]:
        """Find a blurb for a specific team in the plan.

        Searches through all sections in the plan to find an emphasized blurb
        for the given team name. Only returns emphasized blurbs to highlight
        the most important commentary.

        Args:
            plan: The RecapPlan to search
            team_name: The team name to find a blurb for

        Returns:
            The blurb text if found, None otherwise
        """
        for section in plan.sections:
            for blurb in section.team_blurbs:
                if blurb.team_name == team_name and blurb.emphasis:
                    return blurb.blurb
        return None

    def _validate_llm_output(
        self,
        output: str,
        facts: PowerRankingsFactsPack
    ) -> tuple[bool, list[str]]:
        """Validate LLM output against facts pack.

        Checks that the LLM output only contains data from the facts pack,
        helping detect hallucinated statistics or scores.

        Args:
            output: The LLM-generated text to validate
            facts: The PowerRankingsFactsPack used to generate the output

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings: list[str] = []

        # Extract numbers from output (integers and decimals)
        numbers_in_output = re.findall(r'\d+\.?\d*', output)

        for num_str in numbers_in_output:
            try:
                num = float(num_str)
            except ValueError:
                continue

            # Skip small integers (1-20) as they could be rankings, counts, etc.
            if num < 20:
                continue

            # Check if this number (or close to it) exists in facts.all_numbers
            # Allow tolerance of 0.1 for rounding differences
            if not any(abs(num - fact_num) < 0.1 for fact_num in facts.all_numbers):
                warnings.append(f"Number {num} not found in facts")

        # If too many warnings, consider invalid
        is_valid = len(warnings) < 3

        if warnings:
            logger.warning(
                "LLM output validation warnings",
                extra={
                    "warning_count": len(warnings),
                    "warnings": warnings[:5],  # Limit logged warnings
                    "is_valid": is_valid,
                }
            )

        return is_valid, warnings

    async def generate(
        self,
        summary: WeeklySummary,
        persona: Optional[str] = None,
        use_llm: bool = True,
        llm_handler: Optional[Any] = None
    ) -> GeneratorResult:
        """Generate a recap using the facts-first pattern with two-phase LLM.

        Overrides the base generate() method to support two-phase LLM generation:
        - Phase 1: LLM produces structured JSON plan
        - Phase 2: Python validates and renders the plan

        If two-phase LLM fails, falls back to traditional LLM, then deterministic.

        Flow:
        1. Extract facts from summary
        2. Generate deterministic version (always available as fallback)
        3. If two-phase LLM enabled, attempt planner -> renderer flow
        4. If traditional LLM requested, attempt with validation
        5. Fall back to deterministic if all LLM attempts fail

        Args:
            summary: The weekly summary data
            persona: Writing persona for LLM generation
            use_llm: Whether to attempt LLM generation
            llm_handler: Handler for LLM API calls

        Returns:
            GeneratorResult with the generated recap and metadata
        """
        start_time = time.time()
        warnings: list[str] = []

        # Step 1: Extract facts
        facts = await self.extract_facts(summary)
        facts_dict = self._facts_to_dict(facts)

        logger.debug(
            "Facts extracted for recap generation",
            extra={
                "generator": self.__class__.__name__,
                "league": summary.league_name,
                "week": summary.week,
            }
        )

        # Step 2: Generate deterministic version (always available as fallback)
        det_title, det_content = self.render_deterministic(facts)

        # Step 3: Attempt two-phase LLM if enabled
        if use_llm and llm_handler and persona and self._use_two_phase_llm():
            try:
                # Phase 1: Get JSON plan from LLM
                planner_prompt = self.build_planner_prompt(facts, persona)
                llm_json = await self._call_llm_for_plan(llm_handler, planner_prompt)

                if llm_json:
                    # Parse the plan
                    plan = self.planner.parse_plan(llm_json)

                    if plan:
                        # Validate the plan
                        is_valid, validation_warnings = self.planner.validate_plan(
                            plan,
                            set(facts.all_team_names),
                            None
                        )
                        warnings.extend(validation_warnings)

                        if is_valid:
                            # Phase 2: Render with Python
                            content = self.render_from_plan(plan, facts)

                            latency_ms = int((time.time() - start_time) * 1000)

                            logger.info(
                                "Two-phase LLM recap generated successfully",
                                extra={
                                    "generator": self.__class__.__name__,
                                    "persona": persona,
                                    "latency_ms": latency_ms,
                                    "rendering_mode": RenderingMode.LLM.value,
                                    "two_phase": True,
                                }
                            )

                            return GeneratorResult(
                                title=det_title,
                                content=content,
                                rendering_mode=RenderingMode.LLM,
                                warnings=warnings,
                                metadata={
                                    "facts_pack": facts_dict,
                                    "plan": asdict(plan) if plan else None,
                                    "two_phase_llm": True,
                                },
                                latency_ms=latency_ms,
                                llm_provider="openai"
                            )
                        else:
                            logger.warning(
                                "Plan validation failed, trying traditional LLM",
                                extra={"warnings": validation_warnings}
                            )
                    else:
                        warnings.append("Failed to parse LLM plan")
                        logger.warning("Failed to parse LLM plan, trying traditional LLM")
            except Exception as e:
                logger.warning(
                    f"Two-phase LLM failed: {e}",
                    extra={
                        "generator": self.__class__.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                warnings.append(f"Two-phase LLM planning failed: {str(e)}")

        # Step 4: Fall back to traditional LLM if two-phase failed or not enabled
        if use_llm and llm_handler and persona:
            try:
                prompt = self.build_llm_prompt(facts, persona)
                llm_result = await self._call_llm(llm_handler, prompt, persona)

                if llm_result:
                    # Validate LLM output
                    is_valid, validation_warnings = self._validate_llm_output(
                        llm_result, facts
                    )
                    warnings.extend(validation_warnings)

                    if not is_valid:
                        logger.warning(
                            "LLM output failed validation, falling back to deterministic",
                            extra={
                                "generator": self.__class__.__name__,
                                "warnings": validation_warnings,
                            }
                        )
                        # Fall back to deterministic
                        latency_ms = int((time.time() - start_time) * 1000)
                        return GeneratorResult(
                            title=det_title,
                            content=det_content,
                            rendering_mode=RenderingMode.FALLBACK,
                            warnings=warnings,
                            metadata={"facts_pack": facts_dict},
                            latency_ms=latency_ms,
                            llm_provider="openai"
                        )

                    # LLM output is valid
                    latency_ms = int((time.time() - start_time) * 1000)

                    logger.info(
                        "Traditional LLM recap generated and validated successfully",
                        extra={
                            "generator": self.__class__.__name__,
                            "persona": persona,
                            "latency_ms": latency_ms,
                            "rendering_mode": RenderingMode.LLM.value,
                            "two_phase": False,
                        }
                    )

                    return GeneratorResult(
                        title=self._extract_title(llm_result) or det_title,
                        content=llm_result,
                        rendering_mode=RenderingMode.LLM,
                        warnings=warnings,
                        metadata={
                            "facts_pack": facts_dict,
                            "two_phase_llm": False,
                        },
                        latency_ms=latency_ms,
                        llm_provider="openai"
                    )
            except Exception as e:
                logger.warning(
                    f"Traditional LLM generation failed: {e}",
                    extra={
                        "generator": self.__class__.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                warnings.append(f"LLM failed: {str(e)}, using deterministic fallback")

        # Return deterministic result
        latency_ms = int((time.time() - start_time) * 1000)
        mode = RenderingMode.FALLBACK if (use_llm and persona) else RenderingMode.DETERMINISTIC

        logger.info(
            "Deterministic recap generated",
            extra={
                "generator": self.__class__.__name__,
                "latency_ms": latency_ms,
                "rendering_mode": mode.value,
                "had_llm_attempt": use_llm and persona is not None,
            }
        )

        return GeneratorResult(
            title=det_title,
            content=det_content,
            rendering_mode=mode,
            warnings=warnings,
            metadata={"facts_pack": facts_dict},
            latency_ms=latency_ms,
            llm_provider=None
        )
