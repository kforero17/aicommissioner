"""Text formatting and rendering for fantasy sports recaps."""
from typing import Dict, Optional, Any
from datetime import datetime
import asyncio

import openai
from anthropic import Anthropic

from config import settings
from ai_text.summary_generator import WeeklySummary


class TextFormatter:
    """Format structured summaries into readable text."""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
    
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
    
    async def render_llm(
        self, 
        summary: WeeklySummary, 
        style: str = "standard",
        persona: Optional[str] = None,
        provider: str = "openai"
    ) -> str:
        """
        AI-powered rendering with personality and style.
        
        Args:
            summary: Weekly summary data
            style: Base style template
            persona: AI persona ("witty", "professional", "roastmaster", "hype")
            provider: AI provider ("openai" or "anthropic")
            
        Returns:
            AI-generated formatted text
        """
        # Build prompt
        base_text = self.render_deterministic(summary, style)
        prompt = self._build_llm_prompt(summary, base_text, persona or style)
        
        if provider == "anthropic" and self.anthropic_client:
            return await self._render_with_anthropic(prompt)
        elif provider == "openai" and self.openai_client:
            return await self._render_with_openai(prompt)
        else:
            # Fallback to deterministic if AI not available
            return self.render_deterministic(summary, style)
    
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
    
    def _build_llm_prompt(self, summary: WeeklySummary, base_text: str, persona: str) -> str:
        """Build prompt for LLM rendering."""
        persona_instructions = {
            "witty": "Rewrite this fantasy football recap with wit, humor, and clever observations. Use puns, jokes, and playful roasting of teams. Keep it fun and entertaining.",
            "professional": "Rewrite this fantasy football recap in a professional sports journalism style. Use proper analysis, statistics, and formal language.",
            "roastmaster": "Rewrite this fantasy football recap with savage roasts and trash talk. Really go after the losing teams and bad performances. Be brutal but funny.",
            "hype": "Rewrite this fantasy football recap with maximum energy and excitement. Use lots of caps, exclamation points, and hype up everything. Make it feel like a sports center highlight reel.",
            "analyst": "Rewrite this fantasy football recap with deep fantasy analysis and insights. Focus on trends, predictions, and strategic observations."
        }
        
        instruction = persona_instructions.get(persona, "Rewrite this fantasy football recap in an engaging, entertaining style.")
        
        return f"""
{instruction}

Keep the same factual information but make it more engaging. The recap should be 200-400 words and formatted for a group chat message.

Original recap:
{base_text}

Rewritten recap:
"""
    
    async def _render_with_openai(self, prompt: str) -> str:
        """Render text using OpenAI."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a fantasy football expert who writes engaging recaps for league group chats."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error with OpenAI rendering: {e}")
            return "Error generating AI recap"
    
    async def _render_with_anthropic(self, prompt: str) -> str:
        """Render text using Anthropic Claude."""
        try:
            message = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.8,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            print(f"Error with Anthropic rendering: {e}")
            return "Error generating AI recap"
