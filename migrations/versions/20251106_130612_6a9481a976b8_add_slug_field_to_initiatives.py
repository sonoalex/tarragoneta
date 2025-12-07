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
    """
    Create base tables (role, user, roles_users, initiative) and add slug field.
    This is the first migration, so it creates all base tables if they don't exist.
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 1. Create role table if it doesn't exist (no dependencies)
    if 'role' not in existing_tables:
        op.create_table('role',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=80), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
    
    # 2. Create user table if it doesn't exist (no dependencies)
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
    
    # 3. Create roles_users association table if it doesn't exist (depends on role and user)
    if 'roles_users' not in existing_tables:
        op.create_table('roles_users',
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('role_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['role_id'], ['role.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
        )
    
    # 4. Create initiative table if it doesn't exist (depends on user)
    if 'initiative' not in existing_tables:
        op.create_table('initiative',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('slug', sa.String(length=250), nullable=False),  # NOT NULL from start
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
    else:
        # Table exists - add/modify slug column
        # Refresh inspector to get current state
        inspector = inspect(conn)
        columns = inspector.get_columns('initiative')
        has_slug = any(col['name'] == 'slug' for col in columns)
        
        if not has_slug:
            # Add slug column as nullable first
            op.add_column('initiative', sa.Column('slug', sa.String(length=250), nullable=True))
            
            # Update NULL slugs for existing rows
            conn.execute(sa.text("""
                UPDATE initiative 
                SET slug = LOWER(REGEXP_REPLACE(
                    REGEXP_REPLACE(title, '[^a-zA-Z0-9]+', '-', 'g'),
                    '^-|-$', '', 'g'
                )) || '-' || id::text
                WHERE slug IS NULL
            """))
            
            # Now make it NOT NULL
            op.alter_column('initiative', 'slug',
                   existing_type=sa.VARCHAR(length=250),
                   nullable=False)
        else:
            # Column exists - check if it's nullable and update if needed
            slug_col = next((col for col in columns if col['name'] == 'slug'), None)
            if slug_col and slug_col.get('nullable', True):
                # Update any NULL slugs first
                conn.execute(sa.text("""
                    UPDATE initiative 
                    SET slug = LOWER(REGEXP_REPLACE(
                        REGEXP_REPLACE(title, '[^a-zA-Z0-9]+', '-', 'g'),
                        '^-|-$', '', 'g'
                    )) || '-' || id::text
                    WHERE slug IS NULL
                """))
                
                # Make it NOT NULL
                op.alter_column('initiative', 'slug',
                       existing_type=sa.VARCHAR(length=250),
                       nullable=False)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('initiative', schema=None) as batch_op:
        batch_op.alter_column('slug',
               existing_type=sa.VARCHAR(length=250),
               nullable=True)
