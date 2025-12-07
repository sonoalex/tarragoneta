"""Add SectionResponsible model and migrate active to approved

Revision ID: 0c6b2b937baa
Revises: a713321a1b0f
Create Date: 2025-12-06 20:46:34.276434

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0c6b2b937baa'
down_revision = 'a713321a1b0f'
branch_labels = None
depends_on = None


def upgrade():
    # Create section_responsible role if it doesn't exist
    op.execute("""
        INSERT INTO role (name, description)
        SELECT 'section_responsible', 'Responsable de Sección'
        WHERE NOT EXISTS (
            SELECT 1 FROM role WHERE name = 'section_responsible'
        )
    """)
    
    # Create section_responsible table
    op.create_table('section_responsible',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('section_id', sa.Integer(), nullable=False),
    sa.Column('assigned_at', sa.DateTime(), nullable=True),
    sa.Column('assigned_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['assigned_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['section_id'], ['section.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'section_id', name='unique_user_section')
    )
    
    # Migrate 'active' status to 'approved'
    op.execute("UPDATE inventory_item SET status = 'approved' WHERE status = 'active'")
    
    # Make status NOT NULL
    with op.batch_alter_table('inventory_item', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)


def downgrade():
    # Make status nullable again
    with op.batch_alter_table('inventory_item', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
    
    # Migrate 'approved' back to 'active' (if needed)
    op.execute("UPDATE inventory_item SET status = 'active' WHERE status = 'approved'")
    
    # Drop section_responsible table
    op.drop_table('section_responsible')
    
    # Remove section_responsible role
    op.execute("DELETE FROM role WHERE name = 'section_responsible'")
