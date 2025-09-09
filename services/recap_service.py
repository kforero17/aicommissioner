"""Main service for generating and publishing fantasy sports recaps."""
import json
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import AsyncSessionLocal
from models.league import League
from ai_text.summary_generator import SummaryGenerator
from ai_text.text_formatter import TextFormatter
from publishers.groupme_publisher import GroupMePublisher
from publishers.email_publisher import EmailPublisher


class RecapService:
    """Service for generating and publishing fantasy sports recaps."""
    
    def __init__(self):
        self.formatter = TextFormatter()
        self.groupme_publisher = GroupMePublisher()
        self.email_publisher = EmailPublisher()
    
    async def close(self):
        """Clean up resources."""
        await self.groupme_publisher.close()
    
    def _get_league_member_emails(self, league: League) -> List[str]:
        """Parse and return league member emails from JSON string."""
        if not league.league_member_emails:
            return []
        
        try:
            emails = json.loads(league.league_member_emails)
            if isinstance(emails, list):
                return [email for email in emails if email and isinstance(email, str)]
            return []
        except (json.JSONDecodeError, TypeError):
            print(f"Invalid email format for league {league.id}")
            return []
    
    async def _publish_to_channels(
        self, 
        league: League, 
        recap_text: str, 
        recap_type: str = "Weekly Recap"
    ) -> dict:
        """
        Publish recap to all configured channels (GroupMe and Email).
        
        Returns:
            dict: Status of each publishing attempt
        """
        results = {"groupme": False, "email": False}
        
        # Publish to GroupMe if configured
        if league.groupme_bot_id:
            try:
                success = await self.groupme_publisher.send_long_message(
                    league.groupme_bot_id, 
                    recap_text
                )
                results["groupme"] = success
                if success:
                    print(f"Published {recap_type.lower()} to GroupMe for league {league.id}")
                else:
                    print(f"Failed to publish {recap_type.lower()} to GroupMe for league {league.id}")
            except Exception as e:
                print(f"Error publishing to GroupMe for league {league.id}: {e}")
        
        # Publish to Email if configured
        if league.enable_email_recaps:
            member_emails = self._get_league_member_emails(league)
            if member_emails:
                try:
                    success = await self.email_publisher.send_recap_email(
                        to_emails=member_emails,
                        league_name=league.name,
                        week=league.week or 1,
                        recap_text=recap_text,
                        recap_type=recap_type
                    )
                    results["email"] = success
                    if success:
                        print(f"Published {recap_type.lower()} to {len(member_emails)} email recipients for league {league.id}")
                    else:
                        print(f"Failed to publish {recap_type.lower()} via email for league {league.id}")
                except Exception as e:
                    print(f"Error publishing to email for league {league.id}: {e}")
            else:
                print(f"No email addresses configured for league {league.id}")
        
        return results
    
    async def generate_power_rankings_recap(
        self, 
        league_id: int, 
        week: Optional[int] = None,
        publish: bool = True
    ) -> str:
        """
        Generate and optionally publish a power rankings recap.
        
        Args:
            league_id: League ID
            week: Week number (uses current week if None)
            publish: Whether to publish to GroupMe
            
        Returns:
            Generated recap text
        """
        async with AsyncSessionLocal() as db:
            # Get league
            result = await db.execute(select(League).filter(League.id == league_id))
            league = result.scalar_one_or_none()
            
            if not league:
                raise ValueError(f"League {league_id} not found")
            
            if not league.enable_power_rankings:
                raise ValueError(f"Power rankings disabled for league {league_id}")
            
            # Use current week if not specified
            if week is None:
                week = league.week or 1
            
            # Generate summary
            generator = SummaryGenerator(db)
            summary = await generator.generate_weekly_summary(league_id, week)
            
            # Format text
            if league.enable_llm_rendering and league.ai_persona_style:
                recap_text = await self.formatter.render_llm(
                    summary, 
                    style="standard",
                    persona=league.ai_persona_style
                )
            else:
                recap_text = self.formatter.render_deterministic(summary, "standard")
            
            # Add header for power rankings focus
            header = f"🏆 POWER RANKINGS - {league.name} Week {week}\n\n"
            recap_text = header + recap_text
            
            # Publish if requested
            if publish:
                await self._publish_to_channels(league, recap_text, "Power Rankings")
            
            return recap_text
    
    async def generate_waiver_recap(
        self, 
        league_id: int, 
        week: Optional[int] = None,
        publish: bool = True
    ) -> str:
        """
        Generate and optionally publish a waiver wire recap.
        
        Args:
            league_id: League ID
            week: Week number (uses current week if None)
            publish: Whether to publish to GroupMe
            
        Returns:
            Generated recap text
        """
        async with AsyncSessionLocal() as db:
            # Get league
            result = await db.execute(select(League).filter(League.id == league_id))
            league = result.scalar_one_or_none()
            
            if not league:
                raise ValueError(f"League {league_id} not found")
            
            if not league.enable_waiver_recaps:
                raise ValueError(f"Waiver recaps disabled for league {league_id}")
            
            # Use current week if not specified
            if week is None:
                week = league.week or 1
            
            # Generate summary
            generator = SummaryGenerator(db)
            summary = await generator.generate_weekly_summary(league_id, week)
            
            # Focus on transactions for waiver recap
            if not summary.transactions:
                return f"📄 {league.name} Week {week} Waiver Report\n\nNo waiver activity this week. Everyone's happy with their teams... or gave up. 🤷‍♂️"
            
            # Format text with transaction focus
            if league.enable_llm_rendering and league.ai_persona_style:
                recap_text = await self._format_waiver_focused_llm(summary, league.ai_persona_style)
            else:
                recap_text = self._format_waiver_focused_deterministic(summary)
            
            # Publish if requested
            if publish:
                await self._publish_to_channels(league, recap_text, "Waiver Report")
            
            return recap_text
    
    def _format_waiver_focused_deterministic(self, summary) -> str:
        """Format a deterministic waiver-focused recap."""
        lines = []
        
        lines.append(f"💰 {summary.league_name} - Week {summary.week} Waiver Report")
        lines.append("=" * 45)
        lines.append("")
        
        # Waiver summary
        lines.append(f"💸 Total FAAB Spent: ${summary.total_faab_spent}")
        lines.append(f"📊 Total Transactions: {len(summary.transactions)}")
        if summary.most_active_trader:
            lines.append(f"🔥 Most Active: {summary.most_active_trader}")
        lines.append("")
        
        # Big spenders
        big_spenders = [t for t in summary.transactions if t.faab_spent and t.faab_spent >= 20]
        if big_spenders:
            lines.append("💰 BIG SPENDERS")
            for trans in big_spenders:
                lines.append(f"• {trans.owner_name}: ${trans.faab_spent} on {', '.join(trans.players_added)}")
            lines.append("")
        
        # All transactions
        lines.append("📋 ALL WAIVER ACTIVITY")
        for trans in summary.transactions:
            faab_text = f" (${trans.faab_spent})" if trans.faab_spent else ""
            lines.append(f"• {trans.owner_name}: {trans.notes}{faab_text}")
        lines.append("")
        
        # Analysis
        if summary.total_faab_spent > 100:
            lines.append("🔥 Hot waiver wire this week! Lots of movement.")
        elif summary.total_faab_spent > 50:
            lines.append("📈 Decent waiver activity. Some teams making moves.")
        else:
            lines.append("😴 Pretty quiet on the waiver wire this week.")
        
        return "\n".join(lines)
    
    async def _format_waiver_focused_llm(self, summary, persona: str) -> str:
        """Format a waiver-focused recap using LLM."""
        base_text = self._format_waiver_focused_deterministic(summary)
        
        prompt = f"""
Rewrite this fantasy football waiver wire report with a {persona} personality. 
Focus on the transactions, FAAB spending, and waiver wire strategy.
Make it entertaining and engaging for a group chat.
Keep it 200-300 words.

Original report:
{base_text}

Rewritten report:
"""
        
        return await self.formatter._render_with_openai(prompt)


# Background task functions
async def run_power_rankings(league_id: int, week: Optional[int] = None):
    """Background task to run power rankings recap."""
    service = RecapService()
    try:
        recap = await service.generate_power_rankings_recap(league_id, week, publish=True)
        print(f"Generated power rankings recap for league {league_id}: {len(recap)} characters")
    except Exception as e:
        print(f"Error generating power rankings for league {league_id}: {e}")
    finally:
        await service.close()


async def run_waiver_recap(league_id: int, week: Optional[int] = None):
    """Background task to run waiver recap."""
    service = RecapService()
    try:
        recap = await service.generate_waiver_recap(league_id, week, publish=True)
        print(f"Generated waiver recap for league {league_id}: {len(recap)} characters")
    except Exception as e:
        print(f"Error generating waiver recap for league {league_id}: {e}")
    finally:
        await service.close()


async def run_custom_recap(
    league_id: int, 
    week: Optional[int] = None, 
    style: str = "standard",
    persona: Optional[str] = None
):
    """Background task to run custom recap."""
    service = RecapService()
    try:
        async with AsyncSessionLocal() as db:
            # Get league
            result = await db.execute(select(League).filter(League.id == league_id))
            league = result.scalar_one_or_none()
            
            if not league:
                print(f"League {league_id} not found")
                return
            
            # Use current week if not specified
            if week is None:
                week = league.week or 1
            
            # Generate summary
            from ai_text.summary_generator import SummaryGenerator
            generator = SummaryGenerator(db)
            summary = await generator.generate_weekly_summary(league_id, week)
            
            # Format text
            if persona and service.formatter.openai_client:
                recap_text = await service.formatter.render_llm(summary, style, persona)
            else:
                recap_text = service.formatter.render_deterministic(summary, style)
            
            # Publish to all configured channels
            await service._publish_to_channels(league, recap_text, "Custom Recap")
            
            print(f"Generated custom recap for league {league_id}: {len(recap_text)} characters")
    
    except Exception as e:
        print(f"Error generating custom recap for league {league_id}: {e}")
    finally:
        await service.close()
