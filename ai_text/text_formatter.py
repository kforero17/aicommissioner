"""Text formatting and rendering for fantasy sports recaps."""
from typing import Dict, Optional, Any
from datetime import datetime
import asyncio

import openai
from anthropic import Anthropic

from config import settings
from ai_text.summary_generator import WeeklySummary
from ai_text.llm_handler import LLMHandler, RecapResult


class TextFormatter:
    """Format structured summaries into readable text."""

    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

        # Initialize LLM handler with robust error handling
        self.llm_handler = LLMHandler(
            openai_client=self.openai_client,
            anthropic_client=self.anthropic_client,
            deterministic_fallback=self.render_deterministic
        )
    
    def render_deterministic(self, summary: WeeklySummary, style: str = "standard") -> str:
        """
        Fast, deterministic rendering without AI (zero cost).
        
        Args:
            summary: Weekly summary data
            style: Formatting style ("standard", "emoji", "formal", "casual")
            
        Returns:
            Formatted text ready for publishing
        """
        if style == "emoji":
            return self._render_emoji_style(summary)
        elif style == "formal":
            return self._render_formal_style(summary)
        elif style == "casual":
            return self._render_casual_style(summary)
        else:
            return self._render_standard_style(summary)
    
    async def generate_recap(
        self,
        summary: WeeklySummary,
        style: str = "standard",
        persona: Optional[str] = None,
        provider: str = "openai"
    ) -> RecapResult:
        """
        Generate recap with robust LLM error handling.

        This is the new primary method for generating recaps with complete
        error handling, circuit breaker, retries, and deterministic fallback.

        Args:
            summary: Weekly summary data
            style: Base style template for deterministic rendering
            persona: AI persona ("witty", "professional", "roastmaster", "hype")
            provider: AI provider ("openai" or "anthropic")

        Returns:
            RecapResult with text and metadata (mode, warnings, latency, etc.)
        """
        return await self.llm_handler.generate_recap(summary, style, persona, provider)

    async def render_llm(
        self,
        summary: WeeklySummary,
        style: str = "standard",
        persona: Optional[str] = None,
        provider: str = "openai"
    ) -> str:
        """
        AI-powered rendering with personality and style.

        DEPRECATED: Use generate_recap() instead for robust error handling.
        This method is maintained for backward compatibility but now uses
        the robust LLM handler under the hood.

        Args:
            summary: Weekly summary data
            style: Base style template
            persona: AI persona ("witty", "professional", "roastmaster", "hype")
            provider: AI provider ("openai" or "anthropic")

        Returns:
            AI-generated formatted text (or deterministic fallback)
        """
        result = await self.llm_handler.generate_recap(summary, style, persona, provider)
        return result.text
    
    def _render_standard_style(self, summary: WeeklySummary) -> str:
        """Standard, clean recap format."""
        lines = []
        
        # Header
        lines.append(f"📊 {summary.league_name} - Week {summary.week} Recap")
        lines.append("=" * 40)
        lines.append("")
        
        # Weekly highlights
        lines.append("🏆 WEEKLY HIGHLIGHTS")
        lines.append(f"• High Score: {summary.highest_scorer.team_name} ({summary.highest_scorer.points_scored:.1f} pts)")
        lines.append(f"• Low Score: {summary.lowest_scorer.team_name} ({summary.lowest_scorer.points_scored:.1f} pts)")
        lines.append(f"• Biggest Blowout: {summary.biggest_blowout[0].team_name} over {summary.biggest_blowout[1].team_name} by {summary.biggest_blowout[0].margin:.1f}")
        lines.append(f"• Closest Game: {summary.closest_matchup[0].team_name} vs {summary.closest_matchup[1].team_name} ({summary.closest_matchup[0].margin:.1f} pt margin)")
        lines.append("")
        
        # Power Rankings
        lines.append("📈 POWER RANKINGS")
        for i, team in enumerate(summary.power_rankings[:5], 1):
            movement = self._format_movement(team.movement)
            lines.append(f"{i}. {team.team_name} ({team.record}) {movement}")
        
        if summary.biggest_climber:
            lines.append(f"📈 Biggest Climber: {summary.biggest_climber.team_name} (+{summary.biggest_climber.movement})")
        if summary.biggest_fall:
            lines.append(f"📉 Biggest Fall: {summary.biggest_fall.team_name} ({summary.biggest_fall.movement})")
        lines.append("")
        
        # Waiver Wire Activity
        if summary.transactions:
            lines.append("💰 WAIVER WIRE ACTIVITY")
            lines.append(f"• Total FAAB Spent: ${summary.total_faab_spent}")
            if summary.most_active_trader:
                lines.append(f"• Most Active: {summary.most_active_trader}")
            
            # Top transactions
            for trans in summary.transactions[:3]:
                lines.append(f"• {trans.owner_name}: {trans.notes}")
            lines.append("")
        
        # League Stats
        lines.append("📊 LEAGUE STATS")
        lines.append(f"• League Average: {summary.average_score:.1f} pts")
        lines.append(f"• Total Points: {summary.total_points:.1f}")
        lines.append("")
        
        # Playoff Picture
        lines.append("🏈 PLAYOFF PICTURE")
        for i, team in enumerate(summary.playoff_picture, 1):
            lines.append(f"{i}. {team}")
        
        return "\n".join(lines)
    
    def _render_emoji_style(self, summary: WeeklySummary) -> str:
        """Fun emoji-heavy format."""
        lines = []
        
        lines.append(f"🏈 {summary.league_name} Week {summary.week} 🏈")
        lines.append("🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥")
        lines.append("")
        
        # Highlights with emojis
        lines.append(f"👑 WEEK {summary.week} CHAMPION")
        lines.append(f"{summary.highest_scorer.team_name} 💪 {summary.highest_scorer.points_scored:.1f} pts")
        lines.append("")
        
        lines.append(f"💩 TOILET BOWL WINNER")
        lines.append(f"{summary.lowest_scorer.team_name} 😢 {summary.lowest_scorer.points_scored:.1f} pts")
        lines.append("")
        
        lines.append(f"💀 BIGGEST MASSACRE")
        lines.append(f"{summary.biggest_blowout[0].team_name} destroyed {summary.biggest_blowout[1].team_name}")
        lines.append(f"Margin: {summary.biggest_blowout[0].margin:.1f} pts 💥")
        lines.append("")
        
        # Power Rankings with emojis
        lines.append("👑 POWER RANKINGS 👑")
        emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, team in enumerate(summary.power_rankings[:5]):
            emoji = emojis[i] if i < len(emojis) else f"{i+1}️⃣"
            movement_emoji = "📈" if team.movement > 0 else "📉" if team.movement < 0 else "➡️"
            lines.append(f"{emoji} {team.team_name} {team.record} {movement_emoji}")
        lines.append("")
        
        # Transactions with emojis
        if summary.transactions:
            lines.append("💰 WAIVER WIRE MADNESS 💰")
            lines.append(f"Total FAAB: ${summary.total_faab_spent} 💸")
            for trans in summary.transactions[:3]:
                if trans.faab_spent and trans.faab_spent > 50:
                    lines.append(f"🤑 {trans.owner_name}: {trans.notes}")
                else:
                    lines.append(f"💰 {trans.owner_name}: {trans.notes}")
        
        return "\n".join(lines)
    
    def _render_formal_style(self, summary: WeeklySummary) -> str:
        """Professional, formal format."""
        lines = []
        
        lines.append(f"{summary.league_name}")
        lines.append(f"Week {summary.week} Fantasy Football Report")
        lines.append(f"Season {summary.season}")
        lines.append("-" * 50)
        lines.append("")
        
        lines.append("EXECUTIVE SUMMARY")
        lines.append(f"The {summary.league_name} completed Week {summary.week} of the {summary.season} season.")
        lines.append(f"League average scoring was {summary.average_score:.1f} points per team.")
        lines.append(f"Total league points scored: {summary.total_points:.1f}")
        lines.append("")
        
        lines.append("WEEKLY PERFORMANCE ANALYSIS")
        lines.append(f"Highest Scoring Team: {summary.highest_scorer.team_name} ({summary.highest_scorer.points_scored:.1f} points)")
        lines.append(f"Lowest Scoring Team: {summary.lowest_scorer.team_name} ({summary.lowest_scorer.points_scored:.1f} points)")
        lines.append(f"Most Dominant Victory: {summary.biggest_blowout[0].team_name} defeated {summary.biggest_blowout[1].team_name} by {summary.biggest_blowout[0].margin:.1f} points")
        lines.append("")
        
        lines.append("CURRENT STANDINGS AND POWER RANKINGS")
        for i, team in enumerate(summary.power_rankings, 1):
            lines.append(f"{i}. {team.team_name} - Record: {team.record}, Points For: {team.points_for:.1f}")
        lines.append("")
        
        if summary.transactions:
            lines.append("ROSTER TRANSACTION SUMMARY")
            lines.append(f"Total Free Agent Acquisition Budget Spent: ${summary.total_faab_spent}")
            lines.append(f"Number of Transactions: {len(summary.transactions)}")
            if summary.most_active_trader:
                lines.append(f"Most Active Manager: {summary.most_active_trader}")
        
        return "\n".join(lines)
    
    def _render_casual_style(self, summary: WeeklySummary) -> str:
        """Casual, conversational format."""
        lines = []
        
        lines.append(f"Yo {summary.league_name}! Week {summary.week} is in the books 📚")
        lines.append("")
        
        lines.append("Here's what went down...")
        lines.append("")
        
        lines.append(f"🔥 {summary.highest_scorer.owner_name} went OFF this week!")
        lines.append(f"Their squad {summary.highest_scorer.team_name} put up {summary.highest_scorer.points_scored:.1f} points. Absolutely unreal.")
        lines.append("")
        
        lines.append(f"😬 Meanwhile, {summary.lowest_scorer.owner_name} had a rough week...")
        lines.append(f"{summary.lowest_scorer.team_name} only managed {summary.lowest_scorer.points_scored:.1f} points. Ouch.")
        lines.append("")
        
        lines.append(f"💀 {summary.biggest_blowout[0].owner_name} absolutely DESTROYED {summary.biggest_blowout[1].owner_name}")
        lines.append(f"We're talking a {summary.biggest_blowout[0].margin:.1f} point beatdown. Someone call 911.")
        lines.append("")
        
        lines.append("Current power rankings (don't @ me):")
        for i, team in enumerate(summary.power_rankings[:5], 1):
            movement = ""
            if team.movement > 0:
                movement = f" (up {team.movement})"
            elif team.movement < 0:
                movement = f" (down {abs(team.movement)})"
            lines.append(f"{i}. {team.team_name} {team.record}{movement}")
        lines.append("")
        
        if summary.transactions:
            lines.append("Waiver wire was BUSY this week:")
            lines.append(f"Y'all spent ${summary.total_faab_spent} total on free agents 💸")
            for trans in summary.transactions[:3]:
                lines.append(f"• {trans.notes}")
        
        return "\n".join(lines)
    
    def _format_movement(self, movement: int) -> str:
        """Format power ranking movement."""
        if movement > 0:
            return f"(↑{movement})"
        elif movement < 0:
            return f"(↓{abs(movement)})"
        else:
            return "(→)"

    def get_circuit_status(self) -> dict:
        """Get circuit breaker status for monitoring.

        Returns:
            Dictionary with circuit breaker status for each provider
        """
        return self.llm_handler.get_circuit_status()
