"""user accept terms

Revision ID: a9b798e3d195
Revises: c3441e671a83
Create Date: 2025-12-11 10:28:10.684510

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9b798e3d195'
down_revision = 'c3441e671a83'
branch_labels = None
depends_on = None


def upgrade():
    # Añadimos la columna con default TRUE para rellenar usuarios existentes
    op.add_column(
        'user',
        sa.Column('accept_terms', sa.Boolean(), server_default=sa.text('true'), nullable=False)
    )
    # Opcional: ajustar el server_default a false para nous inserts (els formularis l'omplen)
    op.alter_column('user', 'accept_terms', server_default=sa.text('false'))


def downgrade():
    op.drop_column('user', 'accept_terms')
