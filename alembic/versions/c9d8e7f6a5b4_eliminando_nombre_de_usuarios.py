"""eliminando nombre de usuarios

Revision ID: c9d8e7f6a5b4
Revises: f6a7b8c9d0e1
Create Date: 2026-04-16 16:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("usuarios", "nombre")


def downgrade() -> None:
    op.add_column("usuarios", sa.Column("nombre", sa.String(length=100), nullable=True))
    op.execute("UPDATE usuarios SET nombre = username WHERE nombre IS NULL")
    op.alter_column("usuarios", "nombre", nullable=False)
