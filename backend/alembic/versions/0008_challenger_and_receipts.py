"""diagnosis_results challenger columns and customer_receipts table.

Revision ID: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.add_column('diagnosis_results', sa.Column('challenger', JSON_TYPE, nullable=True))
    op.add_column('diagnosis_results', sa.Column('challenger_checked_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'customer_receipts',
        sa.Column('token', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('repair_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_id', sa.Uuid(), sa.ForeignKey('service_reports.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payload', JSON_TYPE, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_customer_receipts_session_id', 'customer_receipts', ['session_id'])
    op.create_index('ix_customer_receipts_expires_at', 'customer_receipts', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_customer_receipts_expires_at', table_name='customer_receipts')
    op.drop_index('ix_customer_receipts_session_id', table_name='customer_receipts')
    op.drop_table('customer_receipts')
    op.drop_column('diagnosis_results', 'challenger_checked_at')
    op.drop_column('diagnosis_results', 'challenger')
