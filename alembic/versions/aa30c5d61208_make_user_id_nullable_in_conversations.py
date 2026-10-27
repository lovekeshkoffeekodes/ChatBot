"""make_user_id_nullable_in_conversations

Revision ID: aa30c5d61208
Revises: bab291b34124
Create Date: 2026-10-26 19:50:37.231710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa30c5d61208'
down_revision: Union[str, Sequence[str], None] = 'bab291b34124'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make user_id nullable in conversations (temporary — until user system is built)."""
    op.execute("""
        ALTER TABLE conversations
        ALTER COLUMN user_id DROP NOT NULL;
    """)


def downgrade() -> None:
    """Revert user_id back to NOT NULL."""
    op.execute("""
        ALTER TABLE conversations
        ALTER COLUMN user_id SET NOT NULL;
    """)
