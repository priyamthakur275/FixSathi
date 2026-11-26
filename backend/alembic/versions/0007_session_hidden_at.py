"""repair_sessions.hidden_at: a technician can remove a conversation from their chat history without deleting any record

Revision ID: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('repair_sessions', sa.Column('hidden_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('repair_sessions', 'hidden_at')
