"""Add participation table for anonymous participations

Revision ID: 97fcd8762217
Revises: 0c6b2b937baa
Create Date: 2025-12-07 23:17:37.534018

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '97fcd8762217'
down_revision = '0c6b2b937baa'
branch_labels = None
depends_on = None


def upgrade():
    """Create participation table for anonymous participations in initiatives"""
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'participation' not in existing_tables:
        op.create_table('participation',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('initiative_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('email', sa.String(length=100), nullable=True),
            sa.Column('phone', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['initiative_id'], ['initiative.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    """Drop participation table"""
    op.drop_table('participation')
