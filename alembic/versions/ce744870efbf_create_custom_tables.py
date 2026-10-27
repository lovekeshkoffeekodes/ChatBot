"""create_custom_tables

Revision ID: ce744870efbf
Revises: 
Create Date: 2026-10-26

"""
from typing import Sequence, Union
from alembic import op

# --- Revision identifiers (auto-generated, do not change) ---
revision: str = 'ce744870efbf'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all custom tables using raw SQL."""

    # 1. users — stores registered users
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        );
    """)

    # 2. conversations — each chat thread belongs to a user
    #    thread_id matches LangGraph's thread_id so both systems stay in sync
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          SERIAL PRIMARY KEY,
            user_id     INT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            thread_id   VARCHAR(255) NOT NULL UNIQUE,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ
        );
    """)

    # 3. messages — each message belongs to a conversation
    #    role: 'human' for user messages, 'ai' for assistant responses
    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              SERIAL PRIMARY KEY,
            conversation_id INT          NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            VARCHAR(50)  NOT NULL CHECK (role IN ('human', 'ai', 'tool')),
            content         TEXT         NOT NULL,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    """Drop all custom tables (rollback). Order matters — drop children before parents."""

    op.execute("DROP TABLE IF EXISTS messages;")
    op.execute("DROP TABLE IF EXISTS conversations;")
    op.execute("DROP TABLE IF EXISTS users;")
