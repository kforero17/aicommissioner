"""
Migration script to add recaps table for storing generated AI content.

This migration creates the recaps table to persist power rankings,
waiver recaps, and weekly recaps so they can be displayed in the
league hub feed and history tabs.

Run: python migrations/add_recaps_table.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import engine


async def migrate():
    """Run the migration."""
    print("Starting migration: add_recaps_table")

    async with engine.begin() as conn:
        print("Creating recaps table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recaps (
                id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL,
                recap_type VARCHAR(20) NOT NULL,
                week INTEGER NOT NULL,
                season INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                rendering_mode VARCHAR(50),
                ai_persona VARCHAR(50),
                published_at TIMESTAMP WITH TIME ZONE,
                publish_channels TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE
            )
        """))

        print("Creating indexes...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_recaps_league_id
            ON recaps(league_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_recaps_recap_type
            ON recaps(recap_type)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_recaps_week
            ON recaps(week)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_recaps_status
            ON recaps(status)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_recaps_league_week_type
            ON recaps(league_id, week, recap_type)
        """))

    print("\nMigration completed successfully!")
    print("Summary:")
    print("  - Created recaps table")
    print("  - Created indexes for efficient querying")


if __name__ == "__main__":
    asyncio.run(migrate())
