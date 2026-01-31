"""
Database migration to add Google OAuth support.

This adds the following columns to the users table:
- google_user_id: VARCHAR(100) UNIQUE (Google OAuth user identifier)
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add google_user_id column to users table."""
    op.add_column('users', sa.Column('google_user_id', sa.String(100), nullable=True))
    op.create_index('ix_users_google_user_id', 'users', ['google_user_id'], unique=True)


def downgrade():
    """Remove google_user_id column from users table."""
    op.drop_index('ix_users_google_user_id', table_name='users')
    op.drop_column('users', 'google_user_id')
