"""add_chat_title_to_conversations

Revision ID: bab291b34124
Revises: ce744870efbf
Create Date: 2026-10-26 19:47:32.112501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bab291b34124'
down_revision: Union[str, Sequence[str], None] = 'ce744870efbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chat_title column to conversations table."""
    op.execute("""
        ALTER TABLE conversations
        ADD COLUMN chat_title VARCHAR(255) NOT NULL DEFAULT 'New Chat';
    """)


def downgrade() -> None:
    """Remove chat_title column from conversations table (rollback)."""
    op.execute("""
        ALTER TABLE conversations
        DROP COLUMN chat_title;
    """)
