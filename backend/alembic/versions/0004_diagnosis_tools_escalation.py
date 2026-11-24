"""diagnosis_results: required_tools and escalation_reason (additive, nullable-safe)

Revision ID: 0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('diagnosis_results', sa.Column('required_tools', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False, server_default='[]'))
    op.add_column('diagnosis_results', sa.Column('escalation_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnosis_results', 'escalation_reason')
    op.drop_column('diagnosis_results', 'required_tools')
