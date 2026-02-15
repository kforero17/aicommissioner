"""Two-phase LLM planning: JSON plan -> Python rendering.

This approach makes validation trivial and avoids hallucination rants.
The LLM produces structured JSON that we validate, then Python renders.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class SectionType(str, Enum):
    """Types of sections in a recap."""
    INTRO = "intro"
    RANKINGS = "rankings"
    MATCHUPS = "matchups"
    HIGHLIGHTS = "highlights"
    TRANSACTIONS = "transactions"
    STORYLINES = "storylines"
    OUTRO = "outro"


@dataclass
class TeamBlurb:
    """A blurb about a specific team, keyed by team name."""
    team_name: str
    tone: str           # "praise", "roast", "neutral", "sympathy"
    blurb: str          # 1-2 sentences max
    emphasis: bool      # Should this be highlighted?


@dataclass
class MatchupBlurb:
    """A blurb about a specific matchup, keyed by matchup ID."""
    matchup_id: int
    winner_team: str
    loser_team: str
    tone: str
    blurb: str


@dataclass
class Section:
    """A section in the recap plan."""
    section_type: SectionType
    title: Optional[str]
    intro_line: Optional[str]
    team_blurbs: list[TeamBlurb]
    matchup_blurbs: list[MatchupBlurb]


@dataclass
class RecapPlan:
    """Complete plan for a recap, produced by LLM planner."""
    opening_hook: str           # Attention-grabbing first line
    sections: list[Section]     # Ordered sections to render
    closing_line: str           # Sign-off line
    theme: Optional[str]        # Optional theme for the week (e.g., "upset week", "scoring explosion")


class LLMPlanner:
    """Two-phase LLM planner for recaps.

    Phase 1: LLM produces structured JSON plan
    Phase 2: Python renders the plan into final text

    This makes validation trivial and prevents hallucination rants.
    """

    def build_planner_prompt(
        self,
        recap_type: str,
        facts_json: str,
        persona_name: str,
        persona_instructions: str,
        valid_team_names: list[str],
        valid_matchup_ids: Optional[list[int]] = None,
        sport: str = "football",
    ) -> str:
        """Build prompt for the planner phase.

        The LLM returns JSON only - no prose.
        """
        team_list = ", ".join(f'"{t}"' for t in valid_team_names)
        matchup_list = ", ".join(str(m) for m in (valid_matchup_ids or []))

        return f"""You are a fantasy {sport} recap planner. Return ONLY valid JSON, no other text.

TASK: Create a structured plan for a {recap_type} recap.

PERSONA: {persona_name}
{persona_instructions}

VALID TEAM NAMES (use ONLY these exact names):
[{team_list}]

{"VALID MATCHUP IDS: [" + matchup_list + "]" if valid_matchup_ids else ""}

FACTS TO USE:
```json
{facts_json}
```

Return a JSON object with this EXACT structure:
{{
  "opening_hook": "One attention-grabbing sentence about this week",
  "theme": "optional theme like 'upset week' or 'scoring explosion' or null",
  "sections": [
    {{
      "section_type": "highlights",
      "title": "Optional section title or null",
      "intro_line": "Optional intro sentence or null",
      "team_blurbs": [
        {{
          "team_name": "EXACT team name from valid list",
          "tone": "praise|roast|neutral|sympathy",
          "blurb": "1-3 sentences. MUST include at least one player name with their points scored (e.g., 'Shai dropped 35.8 pts against a projected 22.0'). For top/bottom teams, include 2-3 players.",
          "emphasis": true
        }}
      ],
      "matchup_blurbs": []
    }}
  ],
  "closing_line": "Sign-off line in persona voice"
}}

RULES:
1. team_name MUST be an exact match from the valid team names list
2. matchup_id MUST be from the valid matchup IDs list (if used)
3. All statistics in blurbs MUST come from the facts
4. Keep blurbs concise: 1-3 sentences maximum
5. Return ONLY the JSON object, no explanation or markdown
6. Every team_blurb MUST reference at least one player with their actual points scored
7. For top-ranked and bottom-ranked teams, reference 2-3 players with stats

Produce 3-5 sections with 2-4 team_blurbs each.
"""

    def parse_plan(self, llm_output: str) -> Optional[RecapPlan]:
        """Parse LLM output into RecapPlan.

        Returns None if parsing fails.
        """
        try:
            # Strip markdown code blocks if present
            cleaned = llm_output.strip()
            if cleaned.startswith("```"):
                # Remove ```json and trailing ```
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)

            data = json.loads(cleaned)

            sections = []
            for s in data.get("sections", []):
                team_blurbs = [
                    TeamBlurb(
                        team_name=tb["team_name"],
                        tone=tb.get("tone", "neutral"),
                        blurb=tb["blurb"],
                        emphasis=tb.get("emphasis", False),
                    )
                    for tb in s.get("team_blurbs", [])
                ]

                matchup_blurbs = [
                    MatchupBlurb(
                        matchup_id=mb["matchup_id"],
                        winner_team=mb.get("winner_team", ""),
                        loser_team=mb.get("loser_team", ""),
                        tone=mb.get("tone", "neutral"),
                        blurb=mb["blurb"],
                    )
                    for mb in s.get("matchup_blurbs", [])
                ]

                sections.append(Section(
                    section_type=SectionType(s.get("section_type", "highlights")),
                    title=s.get("title"),
                    intro_line=s.get("intro_line"),
                    team_blurbs=team_blurbs,
                    matchup_blurbs=matchup_blurbs,
                ))

            return RecapPlan(
                opening_hook=data.get("opening_hook", ""),
                sections=sections,
                closing_line=data.get("closing_line", ""),
                theme=data.get("theme"),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM plan: {e}")
            return None

    def validate_plan(
        self,
        plan: RecapPlan,
        valid_team_names: set[str],
        valid_matchup_ids: Optional[set[int]] = None
    ) -> tuple[bool, list[str]]:
        """Validate plan against known facts.

        Returns (is_valid, warnings).
        """
        warnings = []

        # Check team names
        for section in plan.sections:
            for blurb in section.team_blurbs:
                if blurb.team_name not in valid_team_names:
                    warnings.append(f"Unknown team: {blurb.team_name}")

            for blurb in section.matchup_blurbs:
                if valid_matchup_ids and blurb.matchup_id not in valid_matchup_ids:
                    warnings.append(f"Unknown matchup ID: {blurb.matchup_id}")

        # Check plan has content
        if not plan.opening_hook:
            warnings.append("Missing opening hook")

        if not plan.sections:
            warnings.append("No sections in plan")

        total_blurbs = sum(
            len(s.team_blurbs) + len(s.matchup_blurbs)
            for s in plan.sections
        )
        if total_blurbs == 0:
            warnings.append("No blurbs in plan")

        is_valid = len(warnings) == 0
        return is_valid, warnings

    def render_plan(
        self,
        plan: RecapPlan,
        facts: Any,
        recap_type: str
    ) -> str:
        """Render validated plan into final text.

        This is where Python controls the structure and format.
        """
        lines: list[str] = []

        # Opening hook
        if plan.opening_hook:
            lines.append(plan.opening_hook)
            lines.append("")

        # Theme callout
        if plan.theme:
            lines.append(f"Theme: {plan.theme.upper()}")
            lines.append("")

        # Sections
        for section in plan.sections:
            # Section title
            if section.title:
                lines.append(section.title.upper())
                lines.append("-" * 40)

            # Intro line
            if section.intro_line:
                lines.append(section.intro_line)
                lines.append("")

            # Team blurbs
            for blurb in section.team_blurbs:
                prefix = "* " if blurb.emphasis else "- "
                lines.append(f"{prefix}{blurb.team_name}: {blurb.blurb}")

            # Matchup blurbs
            for blurb in section.matchup_blurbs:
                lines.append(f"- {blurb.winner_team} vs {blurb.loser_team}: {blurb.blurb}")

            lines.append("")

        # Closing
        if plan.closing_line:
            lines.append(plan.closing_line)

        return "\n".join(lines)


def create_planner() -> LLMPlanner:
    """Factory function to create a planner instance."""
    return LLMPlanner()
