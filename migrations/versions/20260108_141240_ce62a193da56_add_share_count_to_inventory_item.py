"""add_share_count_to_inventory_item

Revision ID: ce62a193da56
Revises: 16ba43ca206c
Create Date: 2026-01-08 14:12:40.844060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ce62a193da56'
down_revision = '16ba43ca206c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('inventory_item', sa.Column('share_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('inventory_item', 'share_count')
