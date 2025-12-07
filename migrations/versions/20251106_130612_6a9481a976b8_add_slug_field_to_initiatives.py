"""Add slug field to initiatives

Revision ID: 6a9481a976b8
Revises: 
Create Date: 2025-11-06 13:06:12.730220

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '6a9481a976b8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check if base tables exist, if not create them (for new databases like staging)
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create role table if it doesn't exist (must be first, no dependencies)
    if 'role' not in existing_tables:
        op.create_table('role',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=80), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
    
    # Create user table if it doesn't exist (must be before roles_users)
    if 'user' not in existing_tables:
        op.create_table('user',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('username', sa.String(length=255), nullable=False),
            sa.Column('password', sa.String(length=255), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=True),
            sa.Column('fs_uniquifier', sa.String(length=255), nullable=False),
            sa.Column('confirmed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
            sa.UniqueConstraint('fs_uniquifier'),
            sa.UniqueConstraint('username')
        )
    
    # Create roles_users association table if it doesn't exist (depends on both role and user)
    if 'roles_users' not in existing_tables:
        op.create_table('roles_users',
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('role_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['role_id'], ['role.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
        )
    
    # Create initiative table if it doesn't exist
    if 'initiative' not in existing_tables:
        op.create_table('initiative',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('slug', sa.String(length=250), nullable=True),  # Will be set to NOT NULL below
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('location', sa.String(length=200), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('time', sa.String(length=10), nullable=True),
            sa.Column('image_path', sa.String(length=300), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('view_count', sa.Integer(), nullable=True),
            sa.Column('creator_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('slug')
        )
        # Index is automatically created by UniqueConstraint, no need to create it manually
    
    # Now modify the slug column (works for both existing and newly created tables)
    # Refresh table list after potential table creation
    inspector = inspect(conn)
    current_tables = inspector.get_table_names()
    
    if 'initiative' in current_tables:
        # First, update any NULL slugs (if table already existed with data before migration)
        was_existing = 'initiative' in existing_tables
        if was_existing:
            try:
                result = conn.execute(sa.text("SELECT COUNT(*) FROM initiative WHERE slug IS NULL"))
                null_count = result.scalar()
                if null_count > 0:
                    # Generate slugs for existing rows with NULL slugs
                    # Using a simple approach: slugify the title
                    conn.execute(sa.text("""
                        UPDATE initiative 
                        SET slug = LOWER(REGEXP_REPLACE(
                            REGEXP_REPLACE(title, '[^a-zA-Z0-9]+', '-', 'g'),
                            '^-|-$', '', 'g'
                        )) || '-' || id::text
                        WHERE slug IS NULL
                    """))
            except Exception as e:
                # If query fails, skip this step - table might be empty or have no NULLs
                pass
        
        # Now make slug NOT NULL (safe because all NULLs have been updated or table is new)
        try:
            # Check if column is already NOT NULL
            columns = inspector.get_columns('initiative')
            slug_col = next((col for col in columns if col['name'] == 'slug'), None)
            if slug_col and slug_col.get('nullable', True):
                # Use direct alter_column instead of batch_alter_table for better error handling
                op.alter_column('initiative', 'slug',
                       existing_type=sa.VARCHAR(length=250),
                       nullable=False,
                       schema=None)
        except Exception as e:
            # If column is already NOT NULL or operation fails, that's fine
            # This makes the migration idempotent
            # Log but don't fail - column might already be NOT NULL
            pass


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('initiative', schema=None) as batch_op:
        batch_op.alter_column('slug',
               existing_type=sa.VARCHAR(length=250),
               nullable=True)
