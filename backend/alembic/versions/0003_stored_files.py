"""stored_files: image bytes in PostgreSQL so photos survive restarts (STORAGE_PROVIDER=database)

Revision ID: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('stored_files',
                    sa.Column('key', sa.String(255), primary_key=True),
                    sa.Column('data', sa.LargeBinary(), nullable=False),
                    sa.Column('size_bytes', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table('stored_files')
