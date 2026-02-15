"""Weekly Recap Generator implementing Facts-First, LLM-Last pattern.

The weekly recap is the most story-heavy recap type. The LLM can really
shine with persona here, but it must choose from pre-computed story
primitives rather than inventing narratives.

This generator:
1. Extracts matchup results and computes story primitives from WeeklySummary
2. Renders deterministically with templates (always works as fallback)
3. Builds LLM prompts with strict rules about using only pre-computed stories
4. Validates LLM output against facts to prevent hallucination
"""
import json
import re
import time
import logging
from dataclasses import asdict
from typing import Optional, Any
from statistics import median

from ai_text.summary_generator import WeeklySummary, WeeklyPerformance
from recaps.generators.base import BaseGenerator, GeneratorResult, RenderingMode
from recaps.generators.facts_pack import (
    WeeklyRecapFactsPack,
    MatchupResultFact,
    WeeklyStoryPrimitive,
    PlayerFact,
    TeamRosterHighlights,
)
from recaps.generators.llm_planner import LLMPlanner, RecapPlan, create_planner
from recaps.prompts.personas import get_persona

logger = logging.getLogger(__name__)


class WeeklyRecapGenerator(BaseGenerator):
    """Generator for weekly recaps.

    The weekly recap is story-heavy - this is where persona really shines.
    But we keep it honest by computing 'story primitives' that the LLM
    must choose from. No inventing new narratives.

    Implements the Facts-First, LLM-Last pattern:
    - extract_facts(): Converts WeeklySummary to immutable WeeklyRecapFactsPack
    - render_deterministic(): Template-based output that always works
    - build_llm_prompt(): Structured prompt with story primitives for LLM enhancement
    - _validate_llm_output(): Checks LLM output against facts pack

    Supports two-phase LLM generation:
    - Phase 1: LLM produces structured JSON plan
    - Phase 2: Python validates and renders the plan
    """

    def __init__(self):
        """Initialize the generator with a planner instance."""
        self.planner = create_planner()

    def _use_two_phase_llm(self) -> bool:
        """Enable two-phase LLM for this generator."""
        return True

    async def extract_facts(self, summary: WeeklySummary) -> WeeklyRecapFactsPack:
        """Extract weekly recap facts from WeeklySummary.

        Transforms the mutable WeeklySummary into an immutable WeeklyRecapFactsPack
        containing matchup results, computed story primitives, and validation data.

        Args:
            summary: The weekly summary data from the league

        Returns:
            A frozen WeeklyRecapFactsPack dataclass with all recap facts
        """
        # Build matchup results
        matchups: list[MatchupResultFact] = []
        all_scores: list[float] = []
        all_margins: list[float] = []
        all_team_names: set[str] = set()

        # Group performances into matchups (process only winners to avoid duplicates)
        matchup_id = 0
        for perf in summary.performances:
            if not perf.win:
                continue  # Process only winners to avoid duplicates

            # Find the loser
            loser = next(
                (p for p in summary.performances
                 if p.team_name == perf.opponent_name),
                None
            )
            if not loser:
                continue

            # Determine if upset (lower projected team won)
            was_upset = perf.points_projected < loser.points_projected

            matchup = MatchupResultFact(
                matchup_id=matchup_id,
                winner_team=perf.team_name,
                winner_owner=perf.owner_name,
                winner_score=round(perf.points_scored, 2),
                winner_projected=round(perf.points_projected, 2),
                loser_team=loser.team_name,
                loser_owner=loser.owner_name,
                loser_score=round(loser.points_scored, 2),
                loser_projected=round(loser.points_projected, 2),
                margin=round(perf.margin, 2),
                combined_score=round(perf.points_scored + loser.points_scored, 2),
                was_upset=was_upset,
                projection_beat=round(perf.points_scored - perf.points_projected, 2),
            )
            matchups.append(matchup)
            matchup_id += 1

            all_scores.extend([perf.points_scored, loser.points_scored])
            all_margins.append(perf.margin)
            all_team_names.add(perf.team_name)
            all_team_names.add(loser.team_name)

        matchups_tuple = tuple(matchups)

        # Calculate league stats
        scores_list = [p.points_scored for p in summary.performances]
        total_pts = round(summary.total_points, 2)
        avg_score = round(summary.average_score, 2)
        median_score = round(median(scores_list), 2) if scores_list else 0.0
        high_score = round(max(scores_list), 2) if scores_list else 0.0
        low_score = round(min(scores_list), 2) if scores_list else 0.0

        # Identify key matchups
        game_of_week = min(matchups, key=lambda m: m.margin) if matchups else None
        blowout_of_week = max(matchups, key=lambda m: m.margin) if matchups else None
        highest_scoring = max(matchups, key=lambda m: m.combined_score) if matchups else None

        # Team of week / Dud of week
        team_of_week = summary.highest_scorer.team_name if summary.highest_scorer else None
        team_of_week_score = round(summary.highest_scorer.points_scored, 2) if summary.highest_scorer else None
        dud_of_week = summary.lowest_scorer.team_name if summary.lowest_scorer else None
        dud_of_week_score = round(summary.lowest_scorer.points_scored, 2) if summary.lowest_scorer else None

        # Upsets
        upsets = tuple(m for m in matchups if m.was_upset)
        upset_count = len(upsets)

        # Generate story primitives
        story_primitives = self._generate_story_primitives(
            matchups_tuple, summary, avg_score
        )

        roster_highlights, mvp_of_week, bust_of_week = self._extract_roster_highlights(summary)

        return WeeklyRecapFactsPack(
            league_name=summary.league_name,
            week=summary.week,
            season=summary.season,
            sport=summary.sport,
            matchups=matchups_tuple,
            total_points=total_pts,
            average_score=avg_score,
            median_score=median_score,
            high_score=high_score,
            low_score=low_score,
            story_primitives=story_primitives,
            game_of_week=game_of_week,
            blowout_of_week=blowout_of_week,
            highest_scoring_matchup=highest_scoring,
            team_of_week=team_of_week,
            team_of_week_score=team_of_week_score,
            dud_of_week=dud_of_week,
            dud_of_week_score=dud_of_week_score,
            roster_highlights=roster_highlights,
            mvp_of_week=mvp_of_week,
            bust_of_week=bust_of_week,
            upset_count=upset_count,
            upsets=upsets,
            all_team_names=tuple(sorted(all_team_names)),
            all_scores=tuple(round(s, 2) for s in sorted(set(all_scores))),
            all_margins=tuple(round(m, 2) for m in sorted(set(all_margins))),
        )

    def _generate_story_primitives(
        self,
        matchups: tuple[MatchupResultFact, ...],
        summary: WeeklySummary,
        avg_score: float
    ) -> tuple[WeeklyStoryPrimitive, ...]:
        """Generate pre-computed story hooks for LLM to use.

        These are the 'building blocks' of narratives - computed facts
        that the LLM can weave into a story but cannot invent.

        Story types generated:
        - explosion: Score significantly above average (>30%)
        - collapse: Score significantly below average (<70%)
        - upset: Lower projected team won
        - nail_biter: Margin < 5 points
        - blowout: Margin > 40 points
        - projection_smash: Exceeded projection by > 20
        - projection_bust: Below projection by > 20
        - shootout: Highest scoring matchup

        Args:
            matchups: Tuple of all matchup results
            summary: The weekly summary data
            avg_score: League average score for the week

        Returns:
            Tuple of WeeklyStoryPrimitive instances
        """
        primitives: list[WeeklyStoryPrimitive] = []

        # 1. Explosion: Score significantly above average
        for perf in summary.performances:
            if perf.points_scored > avg_score * 1.3:  # 30% above average
                primitives.append(WeeklyStoryPrimitive(
                    story_type="explosion",
                    headline=f"{perf.team_name} Explodes",
                    team_name=perf.team_name,
                    owner_name=perf.owner_name,
                    description=f"Put up a monster {perf.points_scored:.1f} points, {(perf.points_scored - avg_score):.1f} above the league average.",
                    key_stat=f"{perf.points_scored:.1f} pts",
                ))

        # 2. Collapse: Score significantly below average
        for perf in summary.performances:
            if perf.points_scored < avg_score * 0.7:  # 30% below average
                primitives.append(WeeklyStoryPrimitive(
                    story_type="collapse",
                    headline=f"{perf.team_name} No-Shows",
                    team_name=perf.team_name,
                    owner_name=perf.owner_name,
                    description=f"Limped to {perf.points_scored:.1f} points, {(avg_score - perf.points_scored):.1f} below the league average.",
                    key_stat=f"{perf.points_scored:.1f} pts",
                ))

        # 3. Upsets
        for matchup in matchups:
            if matchup.was_upset:
                proj_diff = matchup.loser_projected - matchup.winner_projected
                primitives.append(WeeklyStoryPrimitive(
                    story_type="upset",
                    headline=f"{matchup.winner_team} Pulls the Upset",
                    team_name=matchup.winner_team,
                    owner_name=matchup.winner_owner,
                    description=f"Was projected {proj_diff:.1f} points lower but won by {matchup.margin:.1f}.",
                    key_stat=f"+{matchup.margin:.1f} margin",
                ))

        # 4. Nail-biters (margin < 5)
        for matchup in matchups:
            if matchup.margin < 5:
                primitives.append(WeeklyStoryPrimitive(
                    story_type="nail_biter",
                    headline=f"Heart-Stopper: {matchup.winner_team} vs {matchup.loser_team}",
                    team_name=matchup.winner_team,
                    owner_name=matchup.winner_owner,
                    description=f"Won by just {matchup.margin:.2f} points in a game that came down to the wire.",
                    key_stat=f"{matchup.margin:.2f} margin",
                ))

        # 5. Blowouts (margin > 40)
        for matchup in matchups:
            if matchup.margin > 40:
                primitives.append(WeeklyStoryPrimitive(
                    story_type="blowout",
                    headline=f"{matchup.winner_team} Dominates",
                    team_name=matchup.winner_team,
                    owner_name=matchup.winner_owner,
                    description=f"Crushed {matchup.loser_team} by {matchup.margin:.1f} points.",
                    key_stat=f"+{matchup.margin:.1f}",
                ))

        # 6. Projection beat (exceeded projection by > 20)
        for perf in summary.performances:
            beat = perf.points_scored - perf.points_projected
            if beat > 20:
                primitives.append(WeeklyStoryPrimitive(
                    story_type="projection_smash",
                    headline=f"{perf.team_name} Exceeds Expectations",
                    team_name=perf.team_name,
                    owner_name=perf.owner_name,
                    description=f"Was projected for {perf.points_projected:.1f} but delivered {perf.points_scored:.1f}.",
                    key_stat=f"+{beat:.1f} vs proj",
                ))

        # 7. Projection miss (below projection by > 20)
        for perf in summary.performances:
            miss = perf.points_projected - perf.points_scored
            if miss > 20:
                primitives.append(WeeklyStoryPrimitive(
                    story_type="projection_bust",
                    headline=f"{perf.team_name} Disappoints",
                    team_name=perf.team_name,
                    owner_name=perf.owner_name,
                    description=f"Was projected for {perf.points_projected:.1f} but only managed {perf.points_scored:.1f}.",
                    key_stat=f"-{miss:.1f} vs proj",
                ))

        # 8. Highest scoring matchup
        if matchups:
            best = max(matchups, key=lambda m: m.combined_score)
            primitives.append(WeeklyStoryPrimitive(
                story_type="shootout",
                headline=f"Shootout: {best.winner_team} vs {best.loser_team}",
                team_name=best.winner_team,
                owner_name=best.winner_owner,
                description=f"Combined for {best.combined_score:.1f} points in the week's highest-scoring affair.",
                key_stat=f"{best.combined_score:.1f} combined",
            ))

        for perf in summary.performances:
            if not perf.roster_data:
                continue
            try:
                players = json.loads(perf.roster_data)
            except (json.JSONDecodeError, TypeError):
                continue
            for p in players:
                if p.get('started') and p.get('points', 0) >= 40:
                    primitives.append(WeeklyStoryPrimitive(
                        story_type="player_explosion",
                        headline=f"{p['name']} Goes Off for {perf.team_name}",
                        team_name=perf.team_name,
                        owner_name=perf.owner_name,
                        description=f"{p['name']} ({p.get('position', '?')}) dropped {p['points']:.1f} points.",
                        key_stat=f"{p['points']:.1f} pts",
                    ))

        for perf in summary.performances:
            if not perf.roster_data:
                continue
            try:
                players = json.loads(perf.roster_data)
            except (json.JSONDecodeError, TypeError):
                continue
            for p in players:
                if (p.get('started') and p.get('projected') is not None
                        and p['projected'] >= 15 and p.get('points', 0) < 5):
                    primitives.append(WeeklyStoryPrimitive(
                        story_type="player_dud",
                        headline=f"{p['name']} No-Shows for {perf.team_name}",
                        team_name=perf.team_name,
                        owner_name=perf.owner_name,
                        description=f"{p['name']} ({p.get('position', '?')}) projected {p['projected']:.1f} but scored just {p['points']:.1f}.",
                        key_stat=f"{p['points']:.1f} pts (proj {p['projected']:.1f})",
                    ))

        return tuple(primitives)

    def _extract_roster_highlights(
        self,
        summary: WeeklySummary,
    ) -> tuple[
        Optional[tuple[TeamRosterHighlights, ...]],
        Optional[PlayerFact],
        Optional[tuple[str, PlayerFact]],
    ]:
        highlights: list[TeamRosterHighlights] = []
        league_mvp: Optional[PlayerFact] = None
        league_mvp_team: Optional[str] = None
        league_bust: Optional[tuple[str, PlayerFact]] = None

        for perf in summary.performances:
            if not perf.roster_data:
                continue

            try:
                players = json.loads(perf.roster_data)
            except (json.JSONDecodeError, TypeError):
                continue

            if not players:
                continue

            starters = [p for p in players if p.get('started')]
            bench = [p for p in players if not p.get('started')]

            if not starters:
                continue

            top_starter = max(starters, key=lambda p: p.get('points', 0))
            top_scorer_fact = PlayerFact(
                name=top_starter['name'],
                position=top_starter.get('position', ''),
                points=top_starter.get('points', 0),
                projected=top_starter.get('projected'),
                started=True,
            )

            biggest_bust_fact = None
            if any(p.get('projected') is not None for p in starters):
                busts = [
                    p for p in starters
                    if p.get('projected') is not None
                    and p['points'] - p['projected'] <= -5
                ]
                if busts:
                    worst = min(busts, key=lambda p: p['points'] - p['projected'])
                    biggest_bust_fact = PlayerFact(
                        name=worst['name'],
                        position=worst.get('position', ''),
                        points=worst.get('points', 0),
                        projected=worst.get('projected'),
                        started=True,
                    )

            best_bench_fact = None
            bench_total = sum(p.get('points', 0) for p in bench)
            if bench:
                top_bench = max(bench, key=lambda p: p.get('points', 0))
                if top_bench.get('points', 0) > 0:
                    best_bench_fact = PlayerFact(
                        name=top_bench['name'],
                        position=top_bench.get('position', ''),
                        points=top_bench.get('points', 0),
                        projected=top_bench.get('projected'),
                        started=False,
                    )

            highlights.append(TeamRosterHighlights(
                team_name=perf.team_name,
                owner_name=perf.owner_name,
                top_scorer=top_scorer_fact,
                biggest_bust=biggest_bust_fact,
                best_bench=best_bench_fact,
                bench_points_total=round(bench_total, 2),
            ))

            if league_mvp is None or top_starter.get('points', 0) > league_mvp.points:
                league_mvp = top_scorer_fact
                league_mvp_team = perf.team_name

            if biggest_bust_fact:
                if league_bust is None or (biggest_bust_fact.projected and biggest_bust_fact.points - biggest_bust_fact.projected < (league_bust[1].points - (league_bust[1].projected or 0))):
                    league_bust = (perf.team_name, biggest_bust_fact)

        return (
            tuple(highlights) if highlights else None,
            league_mvp,
            league_bust,
        )

    def render_deterministic(self, facts: WeeklyRecapFactsPack) -> tuple[str, str]:
        """Render weekly recap deterministically using templates.

        Creates a structured, publication-ready weekly recap with:
        - Matchup results section with upset tags
        - Week highlights (team of week, dud of week, game of week)
        - Storylines section derived from story primitives
        - League stats section

        This serves as both the primary output for non-LLM mode and
        the fallback when LLM generation fails.

        Args:
            facts: The immutable WeeklyRecapFactsPack

        Returns:
            Tuple of (title, content)
        """
        title = f"Week {facts.week} Recap - {facts.league_name}"

        lines: list[str] = []
        lines.append(f"Week {facts.week} Recap - {facts.league_name}")
        lines.append("")

        # Results section
        lines.append("MATCHUP RESULTS")
        lines.append("-" * 46)

        for m in facts.matchups:
            result_line = f"{m.winner_team} {m.winner_score:.1f} def. {m.loser_team} {m.loser_score:.1f}"
            upset_tag = " [UPSET]" if m.was_upset else ""
            lines.append(f"  {result_line}{upset_tag}")

        lines.append("")

        # Highlights section
        lines.append("WEEK HIGHLIGHTS")
        lines.append("-" * 46)

        if facts.team_of_week and facts.team_of_week_score:
            lines.append(f"TEAM OF THE WEEK: {facts.team_of_week}")
            lines.append(f"   {facts.team_of_week_score:.1f} points")
            lines.append("")

        if facts.dud_of_week and facts.dud_of_week_score:
            lines.append(f"DUD OF THE WEEK: {facts.dud_of_week}")
            lines.append(f"   {facts.dud_of_week_score:.1f} points")
            lines.append("")

        if facts.game_of_week:
            gow = facts.game_of_week
            lines.append(f"GAME OF THE WEEK: {gow.winner_team} vs {gow.loser_team}")
            lines.append(f"   Won by {gow.margin:.2f} points")
            lines.append("")

        if facts.blowout_of_week and facts.blowout_of_week.margin > 30:
            bow = facts.blowout_of_week
            lines.append(f"BLOWOUT OF THE WEEK: {bow.winner_team} over {bow.loser_team}")
            lines.append(f"   Won by {bow.margin:.1f} points")
            lines.append("")

        if facts.upset_count > 0:
            lines.append(f"UPSETS: {facts.upset_count}")
            for upset in facts.upsets[:3]:  # Limit to 3
                lines.append(f"   - {upset.winner_team} over {upset.loser_team}")
            lines.append("")

        # Story primitives section - select interesting stories
        interesting_stories = [
            p for p in facts.story_primitives
            if p.story_type in ("explosion", "collapse", "nail_biter", "blowout")
        ][:4]  # Top 4 stories

        if interesting_stories:
            lines.append("STORYLINES")
            lines.append("-" * 46)
            for story in interesting_stories:
                lines.append(f"{story.headline}")
                lines.append(f"   {story.description}")
                lines.append("")

        # Stats section
        lines.append("LEAGUE STATS")
        lines.append("-" * 46)
        lines.append(f"Average Score: {facts.average_score:.1f}")
        lines.append(f"High Score: {facts.high_score:.1f}")
        lines.append(f"Low Score: {facts.low_score:.1f}")
        lines.append(f"Total Points: {facts.total_points:.1f}")

        if facts.mvp_of_week or facts.bust_of_week:
            lines.append("")
            lines.append("PLAYER HIGHLIGHTS")
            lines.append("-" * 46)
            if facts.mvp_of_week:
                mvp = facts.mvp_of_week
                lines.append(f"MVP: {mvp.name} ({mvp.position}) - {mvp.points:.1f} pts")
            if facts.bust_of_week:
                team, bust = facts.bust_of_week
                proj = f" (proj {bust.projected:.1f})" if bust.projected else ""
                lines.append(f"Bust: {bust.name} ({bust.position}) - {bust.points:.1f} pts{proj}")

        content = "\n".join(lines)
        return title, content

    def _format_player_highlights_for_prompt(self, facts: WeeklyRecapFactsPack) -> str:
        lines: list[str] = []

        if facts.mvp_of_week:
            mvp = facts.mvp_of_week
            proj = f" (projected: {mvp.projected:.1f})" if mvp.projected else ""
            lines.append(f"MVP OF THE WEEK: {mvp.name} ({mvp.position}) — {mvp.points:.1f} pts{proj}")

        if facts.bust_of_week:
            team, bust = facts.bust_of_week
            proj = f" (projected: {bust.projected:.1f})" if bust.projected else ""
            lines.append(f"BUST OF THE WEEK: {bust.name} ({bust.position}) — {bust.points:.1f} pts for \"{team}\"{proj}")

        if facts.roster_highlights:
            lines.append("")
            lines.append("PER-TEAM STANDOUTS:")
            for i, rh in enumerate(facts.roster_highlights, 1):
                star = rh.top_scorer
                star_proj = f" (proj {star.projected:.1f})" if star.projected else ""
                lines.append(f"{i}. \"{rh.team_name}\" (owner: {rh.owner_name})")
                lines.append(f"   Star: {star.name} ({star.position}) — {star.points:.1f} pts{star_proj}")
                if rh.biggest_bust:
                    bust = rh.biggest_bust
                    miss = f", missed by {bust.points - bust.projected:.1f}" if bust.projected else ""
                    proj_str = f" (proj {bust.projected:.1f}{miss})" if bust.projected else ""
                    lines.append(f"   Bust: {bust.name} ({bust.position}) — {bust.points:.1f} pts{proj_str}")
                if rh.best_bench:
                    bench = rh.best_bench
                    lines.append(f"   Best Bench: {bench.name} ({bench.position}) — {bench.points:.1f} pts (left on bench!)")
                lines.append(f"   Bench Total: {rh.bench_points_total:.1f} pts")

        if not lines:
            return ""

        return (
            "\nPLAYER HIGHLIGHTS (reference these for specific commentary):\n"
            + "\n".join(lines)
            + "\n\nYou MUST include at least one stat (pts scored, projected) every time you mention a player. "
            "Never reference a player without their numbers.\n"
        )

    def build_llm_prompt(self, facts: WeeklyRecapFactsPack, persona: str) -> str:
        """Build LLM prompt with facts and story primitives.

        Creates a structured prompt that:
        - Includes strict rules about using ONLY provided story primitives
        - Provides persona styling instructions
        - Includes the complete facts pack as JSON
        - Emphasizes that the LLM must PICK stories, not invent them

        Args:
            facts: The immutable WeeklyRecapFactsPack
            persona: The desired writing persona/style

        Returns:
            Complete prompt string for the LLM
        """
        persona_obj = get_persona(persona)
        facts_json = json.dumps(asdict(facts), indent=2, default=str)

        stories_text = "\n".join(
            f"- [{p.story_type.upper()}] {p.headline}: {p.description} ({p.key_stat})"
            for p in facts.story_primitives
        )

        tone_examples = "\n".join(f'- "{ex}"' for ex in persona_obj.tone_examples)

        player_section = self._format_player_highlights_for_prompt(facts)

        return f"""You are a fantasy {facts.sport} commissioner writing an engaging Weekly Recap.

CRITICAL RULES:
1. You may ONLY use facts from the JSON below
2. You MUST choose stories from the STORY PRIMITIVES provided
3. DO NOT invent new narratives, statistics, or matchup results
4. Every score, margin, and team name MUST come from the facts
5. The story primitives are pre-computed - use them, don't make up new ones
6. When mentioning ANY player, ALWAYS include their points scored (and projected points if available)
7. For interesting matchups (upsets, blowouts, nail-biters), mention 2-3 players with full stats
8. For average matchups, mention at least 1 player with stats

PERSONA: {persona_obj.name}
{persona_obj.instructions}

TONE EXAMPLES:
{tone_examples}

PRE-COMPUTED STORY PRIMITIVES (choose from these for your narrative):
{stories_text}
{player_section}
FULL FACTS PACK:
```json
{facts_json}
```

EXAMPLE OF GOOD BLURB (for style reference only — do not copy):
"The upset of the week goes to Fantasy Fiends, who stormed back thanks to CJ McCollum's 42.3 pts (projected just 28.1) and a clutch 18.7 from Jaylen Brown. Meanwhile, the Couch Potatoes got torched — their 'star' D. Henry managed just 6.1 pts on an 18.0 projection."

Write an engaging weekly recap that:
- Opens with a hook about the week's action
- Highlights 2-3 key storylines from the STORY PRIMITIVES
- Mentions the team of the week and any notable performances
- MUST cite specific stats (points, projected) when mentioning any player — never mention a player without numbers
- For key matchups (upsets, blowouts, nail-biters): cite 2-3 players with full stat lines
- For other matchups: cite at least 1 player with stats
- Uses the persona style throughout
- Is 300-600 words
- Is formatted for a group chat message (not markdown)

DO NOT use asterisks for bold. Use emojis sparingly for emphasis.
Remember: Pick stories from the primitives, don't invent new ones!
"""

    def build_planner_prompt(
        self,
        facts: WeeklyRecapFactsPack,
        persona: str
    ) -> str:
        """Build prompt for two-phase planner.

        Creates a prompt that instructs the LLM to return only structured JSON
        describing the recap plan. The JSON will be parsed and validated before
        Python renders the final text.

        Args:
            facts: The WeeklyRecapFactsPack extracted from the summary
            persona: The desired writing persona/style name

        Returns:
            Complete prompt string for the LLM planner phase
        """
        persona_obj = get_persona(persona)
        facts_json = json.dumps(asdict(facts), indent=2, default=str)

        # Extract matchup IDs for validation
        matchup_ids = [m.matchup_id for m in facts.matchups]

        return self.planner.build_planner_prompt(
            recap_type="Weekly Recap",
            facts_json=facts_json,
            persona_name=persona_obj.name,
            persona_instructions=persona_obj.instructions,
            valid_team_names=list(facts.all_team_names),
            valid_matchup_ids=matchup_ids,
            sport=facts.sport,
        )

    def render_from_plan(
        self,
        plan: RecapPlan,
        facts: WeeklyRecapFactsPack
    ) -> str:
        """Render validated plan with facts.

        This method takes a validated RecapPlan and renders it into the final
        text output. Python controls the structure and format, ensuring consistency
        while incorporating the LLM-generated blurbs.

        Args:
            plan: The validated RecapPlan from the LLM
            facts: The WeeklyRecapFactsPack for fact-based rendering

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

        # Always include matchup results (from facts)
        lines.append("MATCHUP RESULTS")
        lines.append("-" * 40)

        for m in facts.matchups:
            result_line = f"{m.winner_team} {m.winner_score:.1f} def. {m.loser_team} {m.loser_score:.1f}"
            upset_tag = " [UPSET]" if m.was_upset else ""

            # Find any matchup blurb for this matchup
            blurb = self._find_matchup_blurb(plan, m.matchup_id)

            lines.append(f"  {result_line}{upset_tag}")
            if blurb:
                lines.append(f"     -> {blurb}")

        lines.append("")

        # Render plan sections with team/matchup blurbs
        for section in plan.sections:
            if section.title:
                lines.append(section.title.upper())
                lines.append("-" * 40)

            if section.intro_line:
                lines.append(section.intro_line)
                lines.append("")

            for tb in section.team_blurbs:
                if tb.team_name not in facts.all_team_names:
                    continue  # Skip invalid teams
                prefix = "* " if tb.emphasis else "- "
                lines.append(f"{prefix}{tb.team_name}: {tb.blurb}")

            for mb in section.matchup_blurbs:
                lines.append(f"- {mb.winner_team} vs {mb.loser_team}: {mb.blurb}")

            lines.append("")

        # Include stats section
        lines.append("LEAGUE STATS")
        lines.append("-" * 40)
        lines.append(f"Average Score: {facts.average_score:.1f}")
        lines.append(f"High Score: {facts.high_score:.1f}")
        lines.append(f"Low Score: {facts.low_score:.1f}")
        lines.append(f"Total Points: {facts.total_points:.1f}")
        lines.append("")

        # Closing
        if plan.closing_line:
            lines.append(plan.closing_line)

        return "\n".join(lines)

    def _find_matchup_blurb(
        self,
        plan: RecapPlan,
        matchup_id: int
    ) -> Optional[str]:
        """Find a blurb for a specific matchup in the plan.

        Searches through all sections in the plan to find a blurb for
        the given matchup ID.

        Args:
            plan: The RecapPlan to search
            matchup_id: The matchup ID to find a blurb for

        Returns:
            The blurb text if found, None otherwise
        """
        for section in plan.sections:
            for blurb in section.matchup_blurbs:
                if blurb.matchup_id == matchup_id:
                    return blurb.blurb
        return None

    def _validate_llm_output(
        self,
        output: str,
        facts: WeeklyRecapFactsPack
    ) -> tuple[bool, list[str]]:
        """Validate LLM output against facts pack.

        Checks that the LLM output only contains data from the facts pack,
        focusing on:
        - Scores (must match values in all_scores)
        - Margins (must match values in all_margins)

        Args:
            output: The LLM-generated text to validate
            facts: The WeeklyRecapFactsPack used to generate the output

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings: list[str] = []

        # Extract scores from output (looking for X.X or XXX.X patterns)
        score_pattern = r'\b(\d{2,3}\.\d{1,2})\b'
        scores_in_output = re.findall(score_pattern, output)

        for score_str in scores_in_output:
            score = float(score_str)
            # Check if this score exists in facts (with tolerance)
            if not any(abs(score - fact_score) < 0.1 for fact_score in facts.all_scores):
                # Also check against total_points, average_score, etc.
                special_values = [
                    facts.total_points, facts.average_score,
                    facts.median_score, facts.high_score, facts.low_score
                ]
                if facts.team_of_week_score:
                    special_values.append(facts.team_of_week_score)
                if facts.dud_of_week_score:
                    special_values.append(facts.dud_of_week_score)

                # Check combined scores from matchups
                combined_scores = [m.combined_score for m in facts.matchups]
                all_valid_scores = list(facts.all_scores) + special_values + combined_scores

                if not any(abs(score - valid) < 0.1 for valid in all_valid_scores):
                    warnings.append(f"Score {score} not found in facts")

        # Extract margins from output (looking for "by X.X" patterns)
        margin_pattern = r'by\s+(\d+\.?\d*)'
        margins_in_output = re.findall(margin_pattern, output)

        for margin_str in margins_in_output:
            margin = float(margin_str)
            if margin > 5:  # Only check significant margins
                if not any(abs(margin - fact_margin) < 0.1 for fact_margin in facts.all_margins):
                    warnings.append(f"Margin {margin} not found in facts")

        is_valid = len(warnings) < 3

        if warnings:
            logger.warning(
                "Weekly recap LLM output validation warnings",
                extra={
                    "warning_count": len(warnings),
                    "warnings": warnings[:5],
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
        """Generate weekly recap with two-phase LLM.

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

        facts = await self.extract_facts(summary)
        facts_dict = self._facts_to_dict(facts)

        logger.debug(
            "Weekly recap facts extracted",
            extra={
                "generator": self.__class__.__name__,
                "league": summary.league_name,
                "week": summary.week,
                "matchup_count": len(facts.matchups),
                "story_count": len(facts.story_primitives),
            }
        )

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
                        matchup_ids = {m.matchup_id for m in facts.matchups}
                        is_valid, validation_warnings = self.planner.validate_plan(
                            plan,
                            set(facts.all_team_names),
                            matchup_ids
                        )
                        warnings.extend(validation_warnings)

                        if is_valid:
                            # Phase 2: Render with Python
                            content = self.render_from_plan(plan, facts)

                            latency_ms = int((time.time() - start_time) * 1000)

                            logger.info(
                                "Two-phase LLM weekly recap generated successfully",
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
                    is_valid, validation_warnings = self._validate_llm_output(llm_result, facts)
                    warnings.extend(validation_warnings)

                    if not is_valid:
                        logger.warning(
                            "LLM output failed validation, falling back to deterministic",
                            extra={
                                "generator": self.__class__.__name__,
                                "warnings": validation_warnings,
                            }
                        )
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

                    latency_ms = int((time.time() - start_time) * 1000)

                    logger.info(
                        "Traditional LLM weekly recap generated and validated successfully",
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

        latency_ms = int((time.time() - start_time) * 1000)
        mode = RenderingMode.FALLBACK if (use_llm and persona) else RenderingMode.DETERMINISTIC

        logger.info(
            "Weekly recap deterministic output generated",
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
