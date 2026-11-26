"""media: documents (PDF, Word, text) alongside images; mime_type widened for Word's long type name

Revision ID: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('media', 'mime_type', type_=sa.String(120), existing_type=sa.String(40), existing_nullable=False)


def downgrade() -> None:
    op.alter_column('media', 'mime_type', type_=sa.String(40), existing_type=sa.String(120), existing_nullable=False)
