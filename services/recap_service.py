"""Main service for generating and publishing fantasy sports recaps.

Implements a state machine pattern where:
1. Draft is created immediately (before any work)
2. Generation updates the draft with content
3. Publishing is a separate step that can fail independently
4. Failures never lose content - PUBLISH_FAILED preserves generated content
"""
import json
import logging
from dataclasses import asdict
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.connection import AsyncSessionLocal
from models.league import League
from models.recap import Recap, RecapType, RecapStatus
from ai_text.summary_generator import SummaryGenerator, WeeklySummary
from ai_text.text_formatter import TextFormatter
from ai_text.llm_handler import RecapMode, RecapResult
from publishers.groupme_publisher import GroupMePublisher
from publishers.email_publisher import EmailPublisher
from recaps.generators import (
    PowerRankingsGenerator,
    WaiverRecapGenerator,
    WeeklyRecapGenerator,
    GeneratorResult,
    RenderingMode,
)


logger = logging.getLogger(__name__)


def _build_recap_metadata(
    summary: WeeklySummary,
    recap_type: str,
    warnings: Optional[List[str]] = None
) -> dict[str, Any]:
    """Build metadata dict from summary for observability and debugging."""
    metadata = {
        "league_name": summary.league_name,
        "week": summary.week,
        "season": summary.season,
        "recap_type": recap_type,
        "generated_at": datetime.utcnow().isoformat(),
    }

    # Core stats
    metadata["stats"] = {
        "average_score": round(summary.average_score, 2),
        "total_points": round(summary.total_points, 2),
        "total_faab_spent": summary.total_faab_spent,
        "transaction_count": len(summary.transactions),
        "team_count": len(summary.performances),
    }

    # Key derived picks
    metadata["picks"] = {
        "highest_scorer": {
            "team": summary.highest_scorer.team_name,
            "owner": summary.highest_scorer.owner_name,
            "points": summary.highest_scorer.points_scored,
        },
        "lowest_scorer": {
            "team": summary.lowest_scorer.team_name,
            "owner": summary.lowest_scorer.owner_name,
            "points": summary.lowest_scorer.points_scored,
        },
        "biggest_blowout": {
            "winner": summary.biggest_blowout[0].team_name,
            "loser": summary.biggest_blowout[1].team_name,
            "margin": summary.biggest_blowout[0].margin,
        },
        "closest_matchup": {
            "winner": summary.closest_matchup[0].team_name,
            "loser": summary.closest_matchup[1].team_name,
            "margin": summary.closest_matchup[0].margin,
        },
    }

    if summary.most_active_trader:
        metadata["picks"]["most_active_trader"] = summary.most_active_trader

    if summary.biggest_climber:
        metadata["picks"]["biggest_climber"] = {
            "team": summary.biggest_climber.team_name,
            "movement": summary.biggest_climber.movement,
        }

    if summary.biggest_fall:
        metadata["picks"]["biggest_fall"] = {
            "team": summary.biggest_fall.team_name,
            "movement": summary.biggest_fall.movement,
        }

    # Power rankings summary
    metadata["power_rankings"] = [
        {
            "rank": pr.rank,
            "team": pr.team_name,
            "owner": pr.owner_name,
            "record": pr.record,
            "power_score": round(pr.power_score, 2),
            "trend": pr.trend,
            "movement": pr.movement,
        }
        for pr in summary.power_rankings
    ]

    # Transaction IDs for validation
    metadata["transactions"] = [
        {
            "type": t.transaction_type,
            "team": t.team_name,
            "players_added": t.players_added,
            "players_dropped": t.players_dropped,
            "faab_spent": t.faab_spent,
        }
        for t in summary.transactions
    ]

    # Warnings from generation
    if warnings:
        metadata["warnings"] = warnings

    return metadata


class RecapService:
    """Service for generating and publishing fantasy sports recaps.

    Implements a state machine pattern:
    - DRAFT created immediately before any work starts
    - Generation updates the draft with content
    - Publishing is a separate step
    - PUBLISH_FAILED status preserves content when publishing fails
    - FAILED status indicates generation failure (no content)
    """

    def __init__(self):
        self.formatter = TextFormatter()
        self.groupme_publisher = GroupMePublisher()
        self.email_publisher = EmailPublisher()
        # Facts-First generators
        self.power_rankings_generator = PowerRankingsGenerator()
        self.waiver_generator = WaiverRecapGenerator()
        self.weekly_generator = WeeklyRecapGenerator()
        # Reuse TextFormatter's LLM handler (shares circuit breaker state)
        self.llm_handler = self.formatter.llm_handler

    async def close(self):
        """Clean up resources."""
        await self.groupme_publisher.close()

    async def _get_or_create_draft(
        self,
        db: AsyncSession,
        league_id: int,
        recap_type: RecapType,
        week: int,
        season: int,
        ai_persona: Optional[str],
        default_title: str,
    ) -> tuple[Recap, bool]:
        """Get existing recap or create a new draft.

        Idempotent: retries/spam-clicks reuse the same record instead of creating duplicates.

        Args:
            db: Database session
            league_id: League ID
            recap_type: Type of recap
            week: Week number
            season: Season year
            ai_persona: AI persona style (can be None)
            default_title: Title to use if creating new recap

        Returns:
            Tuple of (recap, is_new) where is_new indicates if this is a fresh draft
        """
        result = await db.execute(
            select(Recap).filter(
                and_(
                    Recap.league_id == league_id,
                    Recap.season == season,
                    Recap.week == week,
                    Recap.recap_type == recap_type,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                "Reusing existing recap",
                extra={
                    "recap_id": existing.id,
                    "league_id": league_id,
                    "week": week,
                    "recap_type": recap_type.value,
                    "current_status": existing.status.value,
                }
            )
            return existing, False

        recap = Recap(
            league_id=league_id,
            recap_type=recap_type,
            week=week,
            season=season,
            title=default_title,
            content="",
            status=RecapStatus.DRAFT,
            rendering_mode=None,
            ai_persona=ai_persona,
        )
        db.add(recap)
        await db.flush()

        logger.info(
            "Created new draft recap",
            extra={
                "recap_id": recap.id,
                "league_id": league_id,
                "week": week,
                "recap_type": recap_type.value,
                "status": RecapStatus.DRAFT.value,
            }
        )
        return recap, True

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
        publish: bool = True,
        test_mode: bool = False
    ) -> str:
        """
        Generate and optionally publish a power rankings recap.

        State machine flow:
        1. Create DRAFT row immediately (no content yet)
        2. Generate content and update draft
        3. If publish=True, attempt to publish
        4. On publish failure, set PUBLISH_FAILED (content preserved)
        5. On generation failure, set FAILED

        Args:
            league_id: League ID
            week: Week number (uses current week if None)
            publish: Whether to publish to configured channels
            test_mode: Whether to prefix header with [TEST]

        Returns:
            Generated recap text
        """
        async with AsyncSessionLocal() as db:
            # Get league (validation)
            result = await db.execute(select(League).filter(League.id == league_id))
            league = result.scalar_one_or_none()

            if not league:
                raise ValueError(f"League {league_id} not found")

            if not league.enable_power_rankings:
                raise ValueError(f"Power rankings disabled for league {league_id}")

            if week is None:
                week = league.week or 1

            # STEP 1: Get or create draft (idempotent)
            recap_record, is_new = await self._get_or_create_draft(
                db=db,
                league_id=league_id,
                recap_type=RecapType.POWER_RANKINGS,
                week=week,
                season=league.season,
                ai_persona=league.ai_persona_style,
                default_title=f"Power Rankings - Week {week}",
            )
            recap_id = recap_record.id

            # Skip if already published (unless we want to regenerate)
            if recap_record.status == RecapStatus.PUBLISHED:
                logger.info(
                    "Recap already published, skipping regeneration",
                    extra={
                        "recap_id": recap_id,
                        "league_id": league_id,
                        "week": week,
                        "recap_type": "power_rankings",
                    }
                )
                return recap_record.content

            # Reset status to DRAFT if retrying a failed recap
            if recap_record.status in (RecapStatus.FAILED, RecapStatus.PUBLISH_FAILED):
                recap_record.status = RecapStatus.DRAFT
                recap_record.error_message = None

            try:
                # STEP 2: Generate summary
                summary_generator = SummaryGenerator(db)
                summary = await summary_generator.generate_weekly_summary(league_id, week)

                # STEP 3: Generate content using facts-first generator
                generator_result = await self.power_rankings_generator.generate(
                    summary=summary,
                    persona=league.ai_persona_style if league.enable_llm_rendering else None,
                    use_llm=league.enable_llm_rendering,
                    llm_handler=self.llm_handler if league.enable_llm_rendering else None
                )

                recap_text = generator_result.content

                # Log warnings from generator
                if generator_result.warnings:
                    for warning in generator_result.warnings:
                        logger.warning(
                            f"Power rankings recap warning: {warning}",
                            extra={
                                "recap_id": recap_id,
                                "league_id": league_id,
                                "week": week,
                                "mode": generator_result.rendering_mode.value,
                            }
                        )

                # Add header
                header_prefix = "[TEST] " if test_mode else ""
                header = f"{header_prefix}🏆 POWER RANKINGS - {league.name} Week {week}\n\n"
                recap_text = header + recap_text

                # Build metadata
                recap_metadata = _build_recap_metadata(
                    summary, "power_rankings", warnings=generator_result.warnings
                )
                recap_metadata["facts_pack"] = generator_result.metadata.get("facts_pack", {})

                # STEP 4: Update draft with content
                recap_record.content = recap_text
                recap_record.rendering_mode = generator_result.rendering_mode.value
                recap_record.generation_metadata = json.dumps(recap_metadata)
                recap_record.llm_model = generator_result.llm_provider
                recap_record.llm_latency_ms = generator_result.latency_ms
                await db.flush()

                logger.info(
                    "Power rankings content generated",
                    extra={
                        "recap_id": recap_id,
                        "league_id": league_id,
                        "week": week,
                        "mode": generator_result.rendering_mode.value,
                        "provider": generator_result.llm_provider,
                        "latency_ms": generator_result.latency_ms,
                        "status": RecapStatus.DRAFT.value,
                    }
                )

                # STEP 5: Publish if requested
                if publish:
                    try:
                        publish_results = await self._publish_to_channels(
                            league, recap_text, "Power Rankings"
                        )

                        # Update to published
                        recap_record.status = RecapStatus.PUBLISHED
                        recap_record.published_at = datetime.utcnow()
                        recap_record.publish_channels = json.dumps(publish_results)

                        # Update legacy tracking
                        league.last_power_rankings_at = datetime.utcnow()
                        league.last_power_rankings_week = week

                        logger.info(
                            "Power rankings published",
                            extra={
                                "recap_id": recap_id,
                                "league_id": league_id,
                                "channels": publish_results,
                                "status": RecapStatus.PUBLISHED.value,
                            }
                        )

                    except Exception as e:
                        # Publishing failed but we have content - don't lose it!
                        logger.error(
                            f"Publishing failed for recap {recap_id}: {e}",
                            extra={
                                "recap_id": recap_id,
                                "league_id": league_id,
                                "error": str(e),
                                "status": RecapStatus.PUBLISH_FAILED.value,
                            }
                        )
                        recap_record.status = RecapStatus.PUBLISH_FAILED
                        recap_record.error_message = f"Publishing failed: {str(e)}"
                        # Content is preserved in draft state

                await db.commit()
                return recap_text

            except Exception as e:
                # Generation failed - update the draft with error
                logger.exception(
                    f"Generation failed for recap {recap_id}: {e}",
                    extra={
                        "recap_id": recap_id,
                        "league_id": league_id,
                        "error": str(e),
                        "status": RecapStatus.FAILED.value,
                    }
                )
                recap_record.status = RecapStatus.FAILED
                recap_record.error_message = f"Generation failed: {str(e)}"
                await db.commit()
                raise

    async def generate_waiver_recap(
        self,
        league_id: int,
        week: Optional[int] = None,
        publish: bool = True,
        test_mode: bool = False
    ) -> str:
        """
        Generate and optionally publish a waiver wire recap.

        State machine flow:
        1. Create DRAFT row immediately (no content yet)
        2. Generate content and update draft (handles "no transactions" case)
        3. If publish=True, attempt to publish
        4. On publish failure, set PUBLISH_FAILED (content preserved)
        5. On generation failure, set FAILED

        Args:
            league_id: League ID
            week: Week number (uses current week if None)
            publish: Whether to publish to configured channels
            test_mode: Whether to prefix header with [TEST]

        Returns:
            Generated recap text
        """
        async with AsyncSessionLocal() as db:
            # Get league (validation)
            result = await db.execute(select(League).filter(League.id == league_id))
            league = result.scalar_one_or_none()

            if not league:
                raise ValueError(f"League {league_id} not found")

            if not league.enable_waiver_recaps:
                raise ValueError(f"Waiver recaps disabled for league {league_id}")

            if week is None:
                week = league.week or 1

            # STEP 1: Get or create draft (idempotent)
            recap_record, is_new = await self._get_or_create_draft(
                db=db,
                league_id=league_id,
                recap_type=RecapType.WAIVER_RECAP,
                week=week,
                season=league.season,
                ai_persona=league.ai_persona_style,
                default_title=f"Waiver Report - Week {week}",
            )
            recap_id = recap_record.id

            # Skip if already published (unless we want to regenerate)
            if recap_record.status == RecapStatus.PUBLISHED:
                logger.info(
                    "Recap already published, skipping regeneration",
                    extra={
                        "recap_id": recap_id,
                        "league_id": league_id,
                        "week": week,
                        "recap_type": "waiver_recap",
                    }
                )
                return recap_record.content

            # Reset status to DRAFT if retrying a failed recap
            if recap_record.status in (RecapStatus.FAILED, RecapStatus.PUBLISH_FAILED):
                recap_record.status = RecapStatus.DRAFT
                recap_record.error_message = None

            try:
                # STEP 2: Generate summary
                summary_generator = SummaryGenerator(db)
                summary = await summary_generator.generate_weekly_summary(league_id, week)

                # Handle "no transactions" case - still generate content
                if not summary.transactions:
                    header_prefix = "[TEST] " if test_mode else ""
                    recap_text = f"{header_prefix}📄 {league.name} Week {week} Waiver Report\n\nNo waiver activity this week. Everyone's happy with their teams... or gave up."

                    # Build minimal metadata for empty recap
                    recap_metadata = _build_recap_metadata(summary, "waiver_recap")
                    recap_metadata["empty_recap"] = True

                    # Update draft with "no activity" content
                    recap_record.content = recap_text
                    recap_record.rendering_mode = "deterministic"
                    recap_record.generation_metadata = json.dumps(recap_metadata)
                    await db.flush()

                    logger.info(
                        "Waiver recap content generated (no transactions)",
                        extra={
                            "recap_id": recap_id,
                            "league_id": league_id,
                            "week": week,
                            "empty_recap": True,
                            "status": RecapStatus.DRAFT.value,
                        }
                    )

                else:
                    # STEP 3: Generate content using facts-first generator
                    generator_result = await self.waiver_generator.generate(
                        summary=summary,
                        persona=league.ai_persona_style if league.enable_llm_rendering else None,
                        use_llm=league.enable_llm_rendering,
                        llm_handler=self.llm_handler if league.enable_llm_rendering else None
                    )

                    recap_text = generator_result.content

                    # Log warnings from generator
                    if generator_result.warnings:
                        for warning in generator_result.warnings:
                            logger.warning(
                                f"Waiver recap warning: {warning}",
                                extra={
                                    "recap_id": recap_id,
                                    "league_id": league_id,
                                    "week": week,
                                    "mode": generator_result.rendering_mode.value,
                                }
                            )

                    # Handle test mode prefix
                    if test_mode:
                        lines = recap_text.split('\n', 1)
                        if len(lines) > 1:
                            recap_text = f"[TEST] {lines[0]}\n{lines[1]}"
                        else:
                            recap_text = f"[TEST] {recap_text}"

                    # Build metadata including facts_pack
                    recap_metadata = _build_recap_metadata(
                        summary, "waiver_recap", warnings=generator_result.warnings
                    )
                    recap_metadata["facts_pack"] = generator_result.metadata.get("facts_pack", {})

                    # STEP 4: Update draft with content
                    recap_record.content = recap_text
                    recap_record.rendering_mode = generator_result.rendering_mode.value
                    recap_record.generation_metadata = json.dumps(recap_metadata)
                    recap_record.llm_model = generator_result.llm_provider
                    recap_record.llm_latency_ms = generator_result.latency_ms
                    await db.flush()

                    logger.info(
                        "Waiver recap content generated",
                        extra={
                            "recap_id": recap_id,
                            "league_id": league_id,
                            "week": week,
                            "mode": generator_result.rendering_mode.value,
                            "provider": generator_result.llm_provider,
                            "latency_ms": generator_result.latency_ms,
                            "status": RecapStatus.DRAFT.value,
                        }
                    )

                # STEP 5: Publish if requested
                if publish:
                    try:
                        publish_results = await self._publish_to_channels(
                            league, recap_text, "Waiver Report"
                        )

                        # Update to published
                        recap_record.status = RecapStatus.PUBLISHED
                        recap_record.published_at = datetime.utcnow()
                        recap_record.publish_channels = json.dumps(publish_results)

                        # Update legacy tracking
                        league.last_waiver_recap_at = datetime.utcnow()
                        league.last_waiver_recap_week = week

                        logger.info(
                            "Waiver recap published",
                            extra={
                                "recap_id": recap_id,
                                "league_id": league_id,
                                "channels": publish_results,
                                "status": RecapStatus.PUBLISHED.value,
                            }
                        )

                    except Exception as e:
                        # Publishing failed but we have content - don't lose it!
                        logger.error(
                            f"Publishing failed for recap {recap_id}: {e}",
                            extra={
                                "recap_id": recap_id,
                                "league_id": league_id,
                                "error": str(e),
                                "status": RecapStatus.PUBLISH_FAILED.value,
                            }
                        )
                        recap_record.status = RecapStatus.PUBLISH_FAILED
                        recap_record.error_message = f"Publishing failed: {str(e)}"
                        # Content is preserved in draft state

                await db.commit()
                return recap_text

            except Exception as e:
                # Generation failed - update the draft with error
                logger.exception(
                    f"Generation failed for recap {recap_id}: {e}",
                    extra={
                        "recap_id": recap_id,
                        "league_id": league_id,
                        "error": str(e),
                        "status": RecapStatus.FAILED.value,
                    }
                )
                recap_record.status = RecapStatus.FAILED
                recap_record.error_message = f"Generation failed: {str(e)}"
                await db.commit()
                raise

    async def retry_publish(self, recap_id: int) -> bool:
        """
        Retry publishing a failed recap.

        Only works for recaps in DRAFT or PUBLISH_FAILED status that have content.

        Args:
            recap_id: ID of the recap to retry publishing

        Returns:
            True if publishing succeeded, False otherwise

        Raises:
            ValueError: If recap not found or not in retryable state
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Recap).filter(Recap.id == recap_id))
            recap = result.scalar_one_or_none()

            if not recap:
                raise ValueError(f"Recap {recap_id} not found")

            if recap.status not in (RecapStatus.DRAFT, RecapStatus.PUBLISH_FAILED):
                raise ValueError(
                    f"Recap {recap_id} is {recap.status.value}, can only retry DRAFT or PUBLISH_FAILED"
                )

            if not recap.content:
                raise ValueError(f"Recap {recap_id} has no content to publish")

            # Get league for publishing config
            league_result = await db.execute(
                select(League).filter(League.id == recap.league_id)
            )
            league = league_result.scalar_one_or_none()

            if not league:
                raise ValueError(f"League {recap.league_id} not found")

            logger.info(
                f"Retrying publish for recap {recap_id}",
                extra={
                    "recap_id": recap_id,
                    "league_id": recap.league_id,
                    "previous_status": recap.status.value,
                }
            )

            try:
                # Determine recap type name for publishing
                recap_type_name = {
                    RecapType.POWER_RANKINGS: "Power Rankings",
                    RecapType.WAIVER_RECAP: "Waiver Report",
                    RecapType.WEEKLY_RECAP: "Weekly Recap",
                }.get(recap.recap_type, "Recap")

                publish_results = await self._publish_to_channels(
                    league, recap.content, recap_type_name
                )

                recap.status = RecapStatus.PUBLISHED
                recap.published_at = datetime.utcnow()
                recap.publish_channels = json.dumps(publish_results)
                recap.error_message = None  # Clear previous error

                await db.commit()

                logger.info(
                    f"Retry publish succeeded for recap {recap_id}",
                    extra={
                        "recap_id": recap_id,
                        "league_id": recap.league_id,
                        "channels": publish_results,
                        "status": RecapStatus.PUBLISHED.value,
                    }
                )
                return True

            except Exception as e:
                logger.error(
                    f"Retry publish failed for recap {recap_id}: {e}",
                    extra={
                        "recap_id": recap_id,
                        "league_id": recap.league_id,
                        "error": str(e),
                        "status": RecapStatus.PUBLISH_FAILED.value,
                    }
                )
                recap.error_message = f"Retry publish failed: {str(e)}"
                await db.commit()
                return False


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

            # Format text with robust error handling
            if persona and service.formatter.openai_client:
                result = await service.formatter.generate_recap(summary, style, persona)
                recap_text = result.text

                # Log warnings and metadata
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(
                            f"Custom recap warning: {warning}",
                            extra={
                                "league_id": league_id,
                                "week": week,
                                "mode": result.mode.value,
                            }
                        )

                logger.info(
                    "Custom recap generated",
                    extra={
                        "league_id": league_id,
                        "week": week,
                        "mode": result.mode.value,
                        "provider": result.provider,
                        "latency_ms": result.latency_ms,
                        "style": style,
                        "persona": persona,
                    }
                )

                # Inform users if circuit breaker is open
                if result.mode == RecapMode.CIRCUIT_OPEN:
                    recap_text = "⚠️ AI recap temporarily unavailable, showing standard recap:\n\n" + recap_text
            else:
                recap_text = service.formatter.render_deterministic(summary, style)

            # Publish to all configured channels
            await service._publish_to_channels(league, recap_text, "Custom Recap")

            print(f"Generated custom recap for league {league_id}: {len(recap_text)} characters")

    except Exception as e:
        print(f"Error generating custom recap for league {league_id}: {e}")
    finally:
        await service.close()
