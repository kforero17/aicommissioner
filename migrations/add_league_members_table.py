"""
Migration script to add league_members table and create commissioner memberships.

This migration:
1. Creates the league_members table
2. Creates LeagueMember records for all existing league owners (as commissioners)

Run this script once to migrate the database.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import engine, AsyncSessionLocal
from models.league import League
from models.league_member import LeagueMember, MemberRole


async def migrate():
    """Run the migration."""
    print("Starting migration: add_league_members_table")

    async with engine.begin() as conn:
        # Create league_members table
        print("Creating league_members table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS league_members (
                id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL,
                user_id INTEGER,
                role VARCHAR(20) NOT NULL DEFAULT 'member',
                invite_token VARCHAR(64) UNIQUE,
                invite_email VARCHAR(255),
                invited_at TIMESTAMP WITH TIME ZONE,
                joined_at TIMESTAMP WITH TIME ZONE,
                preferences TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))

        # Create indexes
        print("Creating indexes...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_league_members_league_id
            ON league_members(league_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_league_members_user_id
            ON league_members(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_league_members_invite_token
            ON league_members(invite_token)
        """))

    print("Table created successfully")

    # Create commissioner memberships for existing leagues
    async with AsyncSessionLocal() as session:
        print("Fetching existing leagues...")
        result = await session.execute(text("SELECT id, owner_id FROM leagues"))
        leagues = result.fetchall()

        print(f"Found {len(leagues)} leagues")

        for league_id, owner_id in leagues:
            # Check if commissioner membership already exists
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM league_members
                    WHERE league_id = :league_id AND user_id = :user_id
                """),
                {"league_id": league_id, "user_id": owner_id}
            )
            count = result.scalar()

            if count == 0:
                # Create commissioner membership
                now = datetime.utcnow()
                await session.execute(
                    text("""
                        INSERT INTO league_members
                        (league_id, user_id, role, joined_at, created_at, updated_at)
                        VALUES (:league_id, :user_id, :role, :joined_at, :created_at, :updated_at)
                    """),
                    {
                        "league_id": league_id,
                        "user_id": owner_id,
                        "role": "commissioner",
                        "joined_at": now,
                        "created_at": now,
                        "updated_at": now
                    }
                )
                print(f"  Created commissioner membership for league {league_id}")
            else:
                print(f"  Commissioner membership already exists for league {league_id}")

        await session.commit()

    print("\nMigration completed successfully!")
    print("Summary:")
    print(f"  - Created league_members table")
    print(f"  - Created commissioner memberships for {len(leagues)} leagues")


if __name__ == "__main__":
    asyncio.run(migrate())
