"""add_image_gps_fields_to_inventory_item

Revision ID: a713321a1b0f
Revises: 842ac89522f9
Create Date: 2025-12-03 22:03:39.611954

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a713321a1b0f'
down_revision = '842ac89522f9'
branch_labels = None
depends_on = None


def upgrade():
    # Add GPS fields from image EXIF and location source
    with op.batch_alter_table('inventory_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_gps_latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('image_gps_longitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('location_source', sa.String(length=50), nullable=True))


def downgrade():
    # Remove GPS fields
    with op.batch_alter_table('inventory_item', schema=None) as batch_op:
        batch_op.drop_column('location_source')
        batch_op.drop_column('image_gps_longitude')
        batch_op.drop_column('image_gps_latitude')
