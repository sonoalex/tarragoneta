"""Remove participation table (no longer used)

Revision ID: c3441e671a83
Revises: 6d646413299d
Create Date: 2025-12-08 21:58:06.470760

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3441e671a83'
down_revision = '6d646413299d'
branch_labels = None
depends_on = None


def upgrade():
    # Eliminar tabla participation si existe (ya no se usa, solo usuarios logueados participan)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'participation' in existing_tables:
        op.drop_table('participation')


def downgrade():
    # Recrear tabla participation (no se usará, pero por si acaso se necesita rollback)
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
