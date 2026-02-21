"""Waiver Recap Generator implementing Facts-First, LLM-Last pattern.

This generator creates waiver wire recaps by:
1. Extracting transaction facts from WeeklySummary
2. Rendering deterministically with templates (always works)
3. Optionally enhancing with LLM using facts as JSON input
4. Validating LLM output against facts to prevent hallucination
"""
import json
import logging
import re
import time
from collections import Counter
from dataclasses import asdict
from typing import Optional, Any

from ai_text.summary_generator import WeeklySummary
from recaps.generators.base import BaseGenerator, GeneratorResult, RenderingMode
from recaps.generators.facts_pack import WaiverFactsPack, TransactionFact, WaiverStoryPick
from recaps.generators.llm_planner import LLMPlanner, RecapPlan, create_planner
from recaps.prompts.personas import get_persona

logger = logging.getLogger(__name__)


class WaiverRecapGenerator(BaseGenerator):
    """Generator for waiver wire recaps.

    Implements the Facts-First, LLM-Last pattern for waiver recaps:
    - extract_facts() converts WeeklySummary transactions to immutable WaiverFactsPack
    - render_deterministic() creates template-based output (always available)
    - build_llm_prompt() passes facts as JSON to LLM with strict hallucination guards
    - _validate_llm_output() checks LLM output against facts pack

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

    async def extract_facts(self, summary: WeeklySummary) -> WaiverFactsPack:
        """Extract waiver facts from WeeklySummary.

        Converts mutable transaction data into immutable TransactionFact tuples
        and calculates derived statistics like big spenders, story picks, and
        positional breakdowns.

        Args:
            summary: The weekly summary containing transaction data

        Returns:
            Immutable WaiverFactsPack with all transaction facts
        """
        # Collect all player names and FAAB values for validation
        all_player_names: list[str] = []
        all_faab_values: list[int] = []
        all_team_names: set[str] = set()

        # Position counters
        qb_adds = 0
        rb_adds = 0
        wr_adds = 0
        te_adds = 0
        dst_adds = 0
        k_adds = 0

        # Convert transactions to immutable facts with auto-generated IDs
        transactions_list: list[TransactionFact] = []
        for idx, t in enumerate(summary.transactions):
            # Collect player names
            all_player_names.extend(t.players_added)
            all_player_names.extend(t.players_dropped)

            # Collect team names
            all_team_names.add(t.team_name)

            # Collect FAAB values (only non-zero values)
            if t.faab_spent is not None and t.faab_spent > 0:
                all_faab_values.append(t.faab_spent)

            # Count positional adds (best-effort detection)
            for player in t.players_added:
                position = self._detect_position(player)
                if position == "QB":
                    qb_adds += 1
                elif position == "RB":
                    rb_adds += 1
                elif position == "WR":
                    wr_adds += 1
                elif position == "TE":
                    te_adds += 1
                elif position == "DST":
                    dst_adds += 1
                elif position == "K":
                    k_adds += 1

            transactions_list.append(
                TransactionFact(
                    transaction_id=idx,
                    team_name=t.team_name,
                    owner_name=t.owner_name,
                    transaction_type=t.transaction_type,
                    players_added=tuple(t.players_added),
                    players_dropped=tuple(t.players_dropped),
                    faab_spent=t.faab_spent,
                    timestamp=None,  # Not available in current WeeklySummary
                )
            )

        transactions = tuple(transactions_list)

        # Identify big spenders (FAAB >= 20)
        big_spenders = tuple(
            t for t in transactions
            if t.faab_spent is not None and t.faab_spent >= 20
        )

        # Derive story picks
        biggest_spend = self._derive_biggest_spend(transactions)
        bargain_hunter = self._derive_bargain_hunter(transactions)
        most_active = self._derive_most_active(transactions)

        return WaiverFactsPack(
            league_name=summary.league_name,
            week=summary.week,
            season=summary.season,
            sport=summary.sport,
            transactions=transactions,
            total_faab_spent=summary.total_faab_spent,
            transaction_count=len(transactions),
            most_active_trader=summary.most_active_trader,
            big_spenders=big_spenders,
            biggest_spend=biggest_spend,
            bargain_hunter=bargain_hunter,
            most_active=most_active,
            qb_adds=qb_adds,
            rb_adds=rb_adds,
            wr_adds=wr_adds,
            te_adds=te_adds,
            dst_adds=dst_adds,
            k_adds=k_adds,
            all_team_names=tuple(sorted(all_team_names)),
            all_player_names=tuple(all_player_names),
            all_faab_values=tuple(sorted(set(all_faab_values))),
        )

    def _detect_position(self, player_name: str) -> Optional[str]:
        """Detect player position from name (best-effort).

        This is a heuristic approach since player position data may not
        be available in the player name string. Returns None if position
        cannot be determined.

        Args:
            player_name: The player's name string

        Returns:
            Position code (QB, RB, WR, TE, DST, K) or None if not detectable
        """
        # Check for D/ST pattern (team defenses)
        player_lower = player_name.lower()
        if "d/st" in player_lower or "defense" in player_lower or "dst" in player_lower:
            return "DST"

        # Position might be in parentheses or after a dash
        # e.g., "Patrick Mahomes (QB)" or "Patrick Mahomes - QB"
        position_patterns = [
            r'\(([A-Z]{1,3})\)',  # (QB), (RB), etc.
            r'-\s*([A-Z]{1,3})\s*$',  # - QB at end
            r',\s*([A-Z]{1,3})\s*$',  # , QB at end
        ]

        for pattern in position_patterns:
            match = re.search(pattern, player_name)
            if match:
                pos = match.group(1).upper()
                if pos in ("QB", "RB", "WR", "TE", "K", "DEF", "DST"):
                    return "DST" if pos == "DEF" else pos

        return None

    def _derive_biggest_spend(
        self, transactions: tuple[TransactionFact, ...]
    ) -> Optional[WaiverStoryPick]:
        """Find the highest FAAB bid.

        Args:
            transactions: Tuple of all transaction facts

        Returns:
            WaiverStoryPick for the biggest spender or None if no FAAB transactions
        """
        faab_transactions = [
            t for t in transactions
            if t.faab_spent is not None and t.faab_spent > 0
        ]
        if not faab_transactions:
            return None

        biggest = max(faab_transactions, key=lambda t: t.faab_spent or 0)
        player = biggest.players_added[0] if biggest.players_added else "unknown"

        return WaiverStoryPick(
            transaction_id=biggest.transaction_id,
            team_name=biggest.team_name,
            owner_name=biggest.owner_name,
            reason=f"Spent ${biggest.faab_spent} on {player}",
            stat=f"${biggest.faab_spent}",
        )

    def _derive_bargain_hunter(
        self, transactions: tuple[TransactionFact, ...]
    ) -> Optional[WaiverStoryPick]:
        """Find someone who won with a $1-5 bid.

        Args:
            transactions: Tuple of all transaction facts

        Returns:
            WaiverStoryPick for the bargain hunter or None if no bargain bids
        """
        bargains = [
            t for t in transactions
            if t.faab_spent is not None
            and 1 <= t.faab_spent <= 5
            and t.players_added
        ]
        if not bargains:
            return None

        # Pick the lowest successful bid
        bargain = min(bargains, key=lambda t: t.faab_spent or 0)
        player = bargain.players_added[0]

        return WaiverStoryPick(
            transaction_id=bargain.transaction_id,
            team_name=bargain.team_name,
            owner_name=bargain.owner_name,
            reason=f"Snagged {player} for just ${bargain.faab_spent}",
            stat=f"${bargain.faab_spent}",
        )

    def _derive_most_active(
        self, transactions: tuple[TransactionFact, ...]
    ) -> Optional[WaiverStoryPick]:
        """Find the team with the most transactions.

        Args:
            transactions: Tuple of all transaction facts

        Returns:
            WaiverStoryPick for the most active team or None if < 2 transactions
        """
        if not transactions:
            return None

        counts = Counter(t.owner_name for t in transactions)
        most_active_owner, count = counts.most_common(1)[0]

        if count < 2:  # Only highlight if they made multiple moves
            return None

        # Find one of their transactions for the ID
        txn = next(t for t in transactions if t.owner_name == most_active_owner)

        return WaiverStoryPick(
            transaction_id=txn.transaction_id,
            team_name=txn.team_name,
            owner_name=most_active_owner,
            reason=f"Made {count} transactions this week",
            stat=f"{count} moves",
        )

    def render_deterministic(self, facts: WaiverFactsPack) -> tuple[str, str]:
        """Render waiver recap deterministically using templates.

        Creates a structured, publication-ready waiver report with:
        - Summary stats (FAAB spent, transaction count)
        - Story picks section (big spender, bargain hunter, busiest manager)
        - All transactions listing
        - Positional breakdown

        Args:
            facts: The immutable WaiverFactsPack

        Returns:
            Tuple of (title, content)
        """
        title = f"Waiver Report - {facts.league_name} Week {facts.week}"

        lines: list[str] = []

        # Header
        lines.append(f"Waiver Report - {facts.league_name} Week {facts.week}")
        lines.append("")

        # Summary section
        lines.append("WAIVER SUMMARY")
        lines.append("-" * 46)
        lines.append(f"Total FAAB Spent: ${facts.total_faab_spent}")
        lines.append(f"Transactions: {facts.transaction_count}")
        if facts.most_active_trader:
            lines.append(f"Most Active: {facts.most_active_trader}")
        lines.append("")

        # Story picks section
        has_stories = any([
            facts.biggest_spend,
            facts.bargain_hunter,
            facts.most_active,
        ])

        if has_stories:
            lines.append("THIS WEEK'S MOVES")
            lines.append("-" * 46)

            if facts.biggest_spend:
                bs = facts.biggest_spend
                lines.append(f"BIG SPENDER: {bs.owner_name}")
                lines.append(f"   {bs.reason} ({bs.stat})")
                lines.append("")

            if facts.bargain_hunter:
                bh = facts.bargain_hunter
                lines.append(f"BARGAIN HUNTER: {bh.owner_name}")
                lines.append(f"   {bh.reason} ({bh.stat})")
                lines.append("")

            if facts.most_active:
                ma = facts.most_active
                lines.append(f"BUSIEST MANAGER: {ma.owner_name}")
                lines.append(f"   {ma.reason} ({ma.stat})")
                lines.append("")

        # All transactions section
        if facts.transactions:
            lines.append("ALL TRANSACTIONS")
            lines.append("-" * 46)
            for t in facts.transactions:
                action = self._format_transaction_action(t)
                faab_text = f" (${t.faab_spent})" if t.faab_spent else ""
                lines.append(f"  {t.owner_name}: {action}{faab_text}")
            lines.append("")

        # Positional breakdown section
        has_positional_data = any([
            facts.qb_adds, facts.rb_adds, facts.wr_adds,
            facts.te_adds, facts.dst_adds, facts.k_adds,
        ])

        if has_positional_data:
            lines.append("POSITION BREAKDOWN")
            lines.append("-" * 46)
            position_parts = []
            if facts.qb_adds:
                position_parts.append(f"QB: {facts.qb_adds}")
            if facts.rb_adds:
                position_parts.append(f"RB: {facts.rb_adds}")
            if facts.wr_adds:
                position_parts.append(f"WR: {facts.wr_adds}")
            if facts.te_adds:
                position_parts.append(f"TE: {facts.te_adds}")
            if facts.dst_adds:
                position_parts.append(f"D/ST: {facts.dst_adds}")
            if facts.k_adds:
                position_parts.append(f"K: {facts.k_adds}")
            lines.append(" | ".join(position_parts))
            lines.append("")

        # Activity commentary
        lines.append(self._get_activity_commentary(facts))

        content = "\n".join(lines)
        return title, content

    def _format_transaction_action(self, t: TransactionFact) -> str:
        """Format a transaction into a readable action string.

        Args:
            t: The transaction fact to format

        Returns:
            Human-readable description of the transaction
        """
        added = ", ".join(t.players_added) if t.players_added else None
        dropped = ", ".join(t.players_dropped) if t.players_dropped else None

        if t.transaction_type == "trade":
            return f"Traded {dropped or '?'} for {added or '?'}"
        elif t.transaction_type == "waiver":
            if added and dropped:
                return f"+{added} / -{dropped}"
            elif added:
                return f"+{added}"
            elif dropped:
                return f"-{dropped}"
            return "waiver claim"
        elif t.transaction_type == "add" or t.transaction_type == "free_agent":
            return f"+{added}" if added else "free agent add"
        elif t.transaction_type == "drop":
            return f"-{dropped}" if dropped else "dropped player"
        else:
            # Generic fallback
            if added and dropped:
                return f"+{added} / -{dropped}"
            elif added:
                return f"+{added}"
            elif dropped:
                return f"-{dropped}"
            return t.transaction_type

    def _get_activity_commentary(self, facts: WaiverFactsPack) -> str:
        """Generate commentary based on activity level.

        Args:
            facts: The waiver facts pack

        Returns:
            Commentary string about activity level
        """
        if facts.total_faab_spent > 100:
            return "Hot waiver wire this week. Managers opened their wallets."
        elif facts.total_faab_spent > 50:
            return "Decent waiver activity. Some teams making moves."
        elif facts.transaction_count > 0:
            return "Quiet week on the waiver wire."
        else:
            return "Complete silence on waivers. Everyone content?"

    def build_llm_prompt(self, facts: WaiverFactsPack, persona: str) -> str:
        """Build LLM prompt with facts as JSON.

        Creates a prompt that:
        - Includes strict rules about only using provided facts
        - Provides persona styling instructions
        - Includes the complete facts pack as JSON
        - Guides the LLM on formatting and length

        Args:
            facts: The immutable WaiverFactsPack
            persona: The desired writing persona/style

        Returns:
            Complete prompt string for the LLM
        """
        facts_json = json.dumps(asdict(facts), indent=2, default=str)

        pickup_context = ""
        if facts.big_spenders:
            lines_ctx = ["NOTABLE PICKUPS:"]
            for t in facts.big_spenders[:5]:
                added = ", ".join(t.players_added) if t.players_added else "?"
                dropped = ", ".join(t.players_dropped) if t.players_dropped else "none"
                lines_ctx.append(f'- "{t.team_name}" picked up {added} (${t.faab_spent} FAAB), dropped {dropped}')
            pickup_context = "\n" + "\n".join(lines_ctx) + "\n"

        return f"""You are a fantasy {facts.sport} commissioner writing a Waiver Wire recap.

CRITICAL RULES:
1. You may ONLY reference facts from the JSON below
2. DO NOT invent player names, FAAB amounts, or team names
3. Every transaction detail MUST come from the facts pack
4. If information isn't in the facts, don't mention it
5. FAAB values must exactly match those in the facts
6. Player names must match those in all_player_names
7. Team names must match those in all_team_names

FACTS PACK:
```json
{facts_json}
```
{pickup_context}
Write a waiver wire recap that:
- Opens with an engaging title/header about waiver activity
- Highlights the story picks (biggest_spend, bargain_hunter, most_active)
- Comments on overall activity level and total FAAB spent
- Optionally roasts or praises specific moves
- Mentions interesting positional trends if notable
- Uses the persona style throughout
- Is 150-300 words
- Is formatted for a group chat message (not markdown)

DO NOT use asterisks for bold. Use emojis sparingly for emphasis.
"""

    def build_planner_prompt(
        self,
        facts: WaiverFactsPack,
        persona: str
    ) -> str:
        """Build prompt for two-phase planner.

        Creates a prompt that instructs the LLM to return only structured JSON
        describing the recap plan. The JSON will be parsed and validated before
        Python renders the final text.

        Args:
            facts: The WaiverFactsPack extracted from the summary
            persona: The desired writing persona/style name

        Returns:
            Complete prompt string for the LLM planner phase
        """
        persona_obj = get_persona(persona)
        facts_json = json.dumps(asdict(facts), indent=2, default=str)

        return self.planner.build_planner_prompt(
            recap_type="Waiver Wire",
            facts_json=facts_json,
            persona_name=persona_obj.name,
            persona_instructions=persona_obj.instructions,
            valid_team_names=list(facts.all_team_names),
            valid_matchup_ids=None,
            sport=facts.sport,
        )

    def render_from_plan(
        self,
        plan: RecapPlan,
        facts: WaiverFactsPack
    ) -> str:
        """Render validated plan with facts.

        This method takes a validated RecapPlan and renders it into the final
        text output. Python controls the structure and format, ensuring consistency
        while incorporating the LLM-generated blurbs.

        Args:
            plan: The validated RecapPlan from the LLM
            facts: The WaiverFactsPack for fact-based rendering

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

        # Always include summary section (from facts)
        lines.append("WAIVER SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total FAAB Spent: ${facts.total_faab_spent}")
        lines.append(f"Transactions: {facts.transaction_count}")
        if facts.most_active_trader:
            lines.append(f"Most Active: {facts.most_active_trader}")
        lines.append("")

        # Render plan sections with team blurbs
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

            lines.append("")

        # Include transactions summary
        if facts.transactions:
            lines.append("ALL TRANSACTIONS")
            lines.append("-" * 40)
            for t in facts.transactions:
                action = self._format_transaction_action(t)
                faab_text = f" (${t.faab_spent})" if t.faab_spent else ""
                lines.append(f"  {t.owner_name}: {action}{faab_text}")
            lines.append("")

        # Closing
        if plan.closing_line:
            lines.append(plan.closing_line)

        return "\n".join(lines)

    def _validate_llm_output(
        self,
        output: str,
        facts: WaiverFactsPack
    ) -> tuple[bool, list[str]]:
        """Validate LLM output against facts pack.

        Checks that the LLM output only contains data from the facts pack,
        focusing on strict FAAB value validation while being lenient on
        player names (which are harder to validate).

        Args:
            output: The LLM-generated text to validate
            facts: The WaiverFactsPack used to generate the output

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings: list[str] = []

        # Extract FAAB values from output ($XX pattern)
        faab_in_output = re.findall(r'\$(\d+)', output)
        for faab_str in faab_in_output:
            faab = int(faab_str)
            # Only validate non-zero FAAB values
            if faab > 0 and faab not in facts.all_faab_values:
                # Also allow total_faab_spent as a valid value
                if faab != facts.total_faab_spent:
                    warnings.append(f"FAAB ${faab} not found in transactions")

        # Check player names (case-insensitive partial match)
        # We look for player names in the output but don't warn
        # since partial references are common and hard to validate
        output_lower = output.lower()
        mentioned_players: list[str] = []
        for player in facts.all_player_names:
            # Check if last name appears (most common reference)
            parts = player.split()
            if len(parts) > 1:
                last_name = parts[-1].lower()
                if last_name in output_lower and len(last_name) > 3:
                    mentioned_players.append(player)
            elif player.lower() in output_lower:
                mentioned_players.append(player)

        # Log mentioned players for debugging but don't warn
        if mentioned_players:
            logger.debug(
                "Players mentioned in LLM output",
                extra={"mentioned_players": mentioned_players[:10]}
            )

        # If too many FAAB warnings, consider invalid
        is_valid = len(warnings) < 3

        if warnings:
            logger.warning(
                "Waiver LLM output validation warnings",
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
        llm_handler: Optional[Any] = None,
        league_context: Optional[dict] = None,
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
            league_context: Optional league metadata for system prompt

        Returns:
            GeneratorResult with the generated recap and metadata
        """
        start_time = time.time()
        warnings: list[str] = []

        # Step 1: Extract facts
        facts = await self.extract_facts(summary)
        facts_dict = self._facts_to_dict(facts)

        logger.debug(
            "Waiver facts extracted for recap generation",
            extra={
                "generator": self.__class__.__name__,
                "league": summary.league_name,
                "week": summary.week,
                "transaction_count": facts.transaction_count,
                "total_faab": facts.total_faab_spent,
            }
        )

        # Step 2: Generate deterministic version (always available as fallback)
        det_title, det_content = self.render_deterministic(facts)

        # Build system prompt if persona is provided
        system_prompt = None
        if persona:
            from ai_text.llm_handler import build_system_prompt
            from ai_text.sports_news import fetch_sports_news
            sport = league_context.get("sport", "football") if league_context else "football"
            news = fetch_sports_news(sport)
            system_prompt = build_system_prompt(persona, league_context, news)

        # Step 3: Attempt two-phase LLM if enabled
        if use_llm and llm_handler and persona and self._use_two_phase_llm():
            try:
                # Phase 1: Get JSON plan from LLM
                planner_prompt = self.build_planner_prompt(facts, persona)
                llm_json = await self._call_llm_for_plan(llm_handler, planner_prompt, system_prompt)

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
                                "Two-phase LLM waiver recap generated successfully",
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
                llm_result = await self._call_llm(llm_handler, prompt, persona, system_prompt)

                if llm_result:
                    # Validate LLM output
                    is_valid, validation_warnings = self._validate_llm_output(
                        llm_result, facts
                    )
                    warnings.extend(validation_warnings)

                    if not is_valid:
                        logger.warning(
                            "Waiver LLM output failed validation, falling back to deterministic",
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
                        "Traditional LLM waiver recap generated and validated successfully",
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
            "Waiver deterministic recap generated",
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
