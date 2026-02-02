"""
Migration script to add unique constraint for idempotent recap generation.

Prevents duplicate recaps when Celery retries or manual sync is spam-clicked.
Constraint: (league_id, season, week, recap_type, ai_persona) must be unique.

Run: python migrations/add_recap_uniqueness_constraint.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import engine


async def migrate():
    """Run the migration."""
    print("Starting migration: add_recap_uniqueness_constraint")

    async with engine.begin() as conn:
        # First, identify and remove duplicates (keep the most recent)
        print("Checking for duplicate recaps...")
        result = await conn.execute(text("""
            SELECT league_id, season, week, recap_type, ai_persona, COUNT(*) as cnt
            FROM recaps
            GROUP BY league_id, season, week, recap_type, ai_persona
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()

        if duplicates:
            print(f"Found {len(duplicates)} duplicate groups, removing older entries...")
            # Delete older duplicates, keeping the most recent by id
            await conn.execute(text("""
                DELETE FROM recaps r1
                USING recaps r2
                WHERE r1.league_id = r2.league_id
                  AND r1.season = r2.season
                  AND r1.week = r2.week
                  AND r1.recap_type = r2.recap_type
                  AND COALESCE(r1.ai_persona, '') = COALESCE(r2.ai_persona, '')
                  AND r1.id < r2.id
            """))
            print("Duplicates removed.")
        else:
            print("No duplicates found.")

        # Add the unique constraint
        print("Adding unique constraint...")
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_recaps_league_season_week_type_persona
            ON recaps(league_id, season, week, recap_type, COALESCE(ai_persona, ''))
        """))

    print("\nMigration completed successfully!")
    print("Summary:")
    print("  - Removed duplicate recaps (if any)")
    print("  - Added unique constraint on (league_id, season, week, recap_type, ai_persona)")
    print("\nGeneration is now idempotent - retries will update existing records.")


if __name__ == "__main__":
    asyncio.run(migrate())
