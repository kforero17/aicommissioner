"""
Database migration to add commissioner_notes to leagues.

Adds the following column to the leagues table:
- commissioner_notes: TEXT (free-form notes about league lore, rivalries, nicknames)
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('leagues', sa.Column('commissioner_notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('leagues', 'commissioner_notes')
