"""
Migration to add observability and debugging fields to recaps table.

These fields enable:
- "Show your work" for power rankings (facts pack, scores, derived picks)
- Transaction ID validation for waiver recaps
- LLM debugging without re-running syncs
- Error tracking for failed generations

Run: python migrations/add_recap_observability_fields.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import engine


async def migrate():
    """Run the migration."""
    print("Starting migration: add_recap_observability_fields")

    async with engine.begin() as conn:
        print("Adding generation_metadata column...")
        await conn.execute(text("""
            ALTER TABLE recaps
            ADD COLUMN IF NOT EXISTS generation_metadata TEXT
        """))

        print("Adding error_message column...")
        await conn.execute(text("""
            ALTER TABLE recaps
            ADD COLUMN IF NOT EXISTS error_message TEXT
        """))

        print("Adding llm_model column...")
        await conn.execute(text("""
            ALTER TABLE recaps
            ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100)
        """))

        print("Adding llm_latency_ms column...")
        await conn.execute(text("""
            ALTER TABLE recaps
            ADD COLUMN IF NOT EXISTS llm_latency_ms INTEGER
        """))

        print("Adding tokens_in column...")
        await conn.execute(text("""
            ALTER TABLE recaps
            ADD COLUMN IF NOT EXISTS tokens_in INTEGER
        """))

        print("Adding tokens_out column...")
        await conn.execute(text("""
            ALTER TABLE recaps
            ADD COLUMN IF NOT EXISTS tokens_out INTEGER
        """))

        print("Adding comments to columns...")
        await conn.execute(text("""
            COMMENT ON COLUMN recaps.generation_metadata IS 'JSON blob: facts pack, scores, transaction IDs, derived picks, warnings'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN recaps.error_message IS 'Stores failure reason if status=failed'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN recaps.llm_model IS 'LLM model used for generation (e.g., gpt-4o-mini)'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN recaps.llm_latency_ms IS 'LLM API call latency in milliseconds'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN recaps.tokens_in IS 'Input tokens sent to LLM'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN recaps.tokens_out IS 'Output tokens received from LLM'
        """))

    print("\nMigration completed successfully!")
    print("Summary:")
    print("  - Added generation_metadata TEXT column")
    print("  - Added error_message TEXT column")
    print("  - Added llm_model VARCHAR(100) column")
    print("  - Added llm_latency_ms INTEGER column")
    print("  - Added tokens_in INTEGER column")
    print("  - Added tokens_out INTEGER column")


if __name__ == "__main__":
    asyncio.run(migrate())
