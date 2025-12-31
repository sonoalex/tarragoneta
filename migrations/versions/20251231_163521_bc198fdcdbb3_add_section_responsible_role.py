"""add_section_responsible_role

Revision ID: bc198fdcdbb3
Revises: bcf387f506da
Create Date: 2025-12-31 16:35:21.350863

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Import RoleEnum - puede fallar en migraciones, así que tenemos fallback
try:
    from app.models import RoleEnum
    USE_ROLE_ENUM = True
except ImportError:
    USE_ROLE_ENUM = False


# revision identifiers, used by Alembic.
revision = 'bc198fdcdbb3'
down_revision = 'bcf387f506da'
branch_labels = None
depends_on = None


def upgrade():
    # Insertar todos los roles necesarios si no existen
    # Usamos INSERT ... ON CONFLICT DO NOTHING (PostgreSQL)
    # Idempotente: si los roles ya existen, no hace nada
    conn = op.get_bind()
    
    # Lista de roles que deben existir (como en producción)
    # Usar RoleEnum si está disponible, sino usar valores hardcodeados como fallback
    if USE_ROLE_ENUM:
        role_descriptions = RoleEnum.descriptions()
        roles = [
            (RoleEnum.ADMIN.value, role_descriptions[RoleEnum.ADMIN.value]),
            (RoleEnum.USER.value, role_descriptions[RoleEnum.USER.value]),
            (RoleEnum.MODERATOR.value, role_descriptions[RoleEnum.MODERATOR.value]),
            (RoleEnum.SECTION_RESPONSIBLE.value, role_descriptions[RoleEnum.SECTION_RESPONSIBLE.value]),
        ]
    else:
        # Fallback si no se puede importar RoleEnum (puede pasar en migraciones)
        roles = [
            ('admin', 'Administrator'),
            ('user', 'Regular User'),
            ('moderator', 'Moderator'),
            ('section_responsible', 'Responsable de Sección'),
        ]
    
    # Insertar cada rol si no existe
    for role_name, role_description in roles:
        conn.execute(text(
            """
            INSERT INTO role (name, description) 
            VALUES (:name, :description)
            ON CONFLICT (name) DO NOTHING
            """
        ).bindparams(name=role_name, description=role_description))
    
    conn.commit()


def downgrade():
    # Opcional: eliminar el rol si se hace rollback
    # Comentado para no perder datos accidentalmente
    # conn = op.get_bind()
    # conn.execute(text("DELETE FROM role WHERE name = 'section_responsible'"))
    # conn.commit()
    pass
