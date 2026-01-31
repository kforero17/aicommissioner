#!/usr/bin/env python3
"""
Database migration to add recap tracking fields to leagues.

This adds the following columns to the leagues table:
- last_power_rankings_at: TIMESTAMP WITH TIME ZONE (nullable)
- last_power_rankings_week: INTEGER (nullable)
- last_waiver_recap_at: TIMESTAMP WITH TIME ZONE (nullable)
- last_waiver_recap_week: INTEGER (nullable)

Run with: python migrations/add_recap_tracking_fields.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import engine


async def upgrade():
    """Add recap tracking columns to leagues table."""
    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'leagues' AND column_name = 'last_power_rankings_at'
        """))
        if result.fetchone():
            print("Columns already exist, skipping migration.")
            return

        print("Adding recap tracking columns...")

        await conn.execute(text("""
            ALTER TABLE leagues
            ADD COLUMN last_power_rankings_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN last_power_rankings_week INTEGER,
            ADD COLUMN last_waiver_recap_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN last_waiver_recap_week INTEGER
        """))

        print("Migration complete!")


async def downgrade():
    """Remove recap tracking columns from leagues table."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE leagues
            DROP COLUMN IF EXISTS last_power_rankings_at,
            DROP COLUMN IF EXISTS last_power_rankings_week,
            DROP COLUMN IF EXISTS last_waiver_recap_at,
            DROP COLUMN IF EXISTS last_waiver_recap_week
        """))
        print("Downgrade complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        asyncio.run(downgrade())
    else:
        asyncio.run(upgrade())
