"""
Database migration to add email support to leagues.

This adds the following columns to the leagues table:
- enable_email_recaps: BOOLEAN DEFAULT FALSE
- league_member_emails: TEXT (JSON array of email addresses)
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add email support columns to leagues table."""
    # Add enable_email_recaps column
    op.add_column('leagues', sa.Column('enable_email_recaps', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add league_member_emails column  
    op.add_column('leagues', sa.Column('league_member_emails', sa.Text(), nullable=True))


def downgrade():
    """Remove email support columns from leagues table."""
    # Remove the columns
    op.drop_column('leagues', 'league_member_emails')
    op.drop_column('leagues', 'enable_email_recaps')
