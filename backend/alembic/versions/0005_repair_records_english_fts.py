"""repair_records full-text index: English stemming, so 'burning' matches 'burn' and 'humming' matches 'hum'

Revision ID: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('ix_repair_records_fts', table_name='repair_records')
    op.create_index('ix_repair_records_fts', 'repair_records', [sa.literal_column("to_tsvector('english', search_text)")], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_repair_records_fts', table_name='repair_records')
    op.create_index('ix_repair_records_fts', 'repair_records', [sa.literal_column("to_tsvector('simple', search_text)")], unique=False, postgresql_using='gin')
