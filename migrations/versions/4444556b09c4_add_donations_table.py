"""Add donations table

Revision ID: 4444556b09c4
Revises: b1caaf81c024
Create Date: 2025-11-10 17:18:41.106581

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '4444556b09c4'
down_revision = 'b1caaf81c024'
branch_labels = None
depends_on = None


def upgrade():
    """Create donation table for tracking Stripe donations"""
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'donation' not in existing_tables:
        op.create_table('donation',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Integer(), nullable=False),  # Amount in cents
            sa.Column('currency', sa.String(length=3), nullable=True),  # Default 'eur' handled in model
            sa.Column('email', sa.String(length=255), nullable=True),  # Donor email (optional)
            sa.Column('stripe_session_id', sa.String(length=255), nullable=False),
            sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),  # Default 'pending' handled in model
            sa.Column('donation_type', sa.String(length=50), nullable=True),  # Default 'voluntary' handled in model
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),  # Optional: link to user if logged in
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('stripe_session_id')
        )


def downgrade():
    """Drop donation table"""
    op.drop_table('donation')
