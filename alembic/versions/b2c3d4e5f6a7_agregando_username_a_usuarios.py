"""agregando username a usuarios

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-15 12:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("username", sa.String(length=50), nullable=True))
    op.execute(
        """
        UPDATE usuarios
        SET username = LOWER(
            REGEXP_REPLACE(
                SPLIT_PART(correo, '@', 1) || '_' || SUBSTRING(id::text, 1, 8),
                '[^a-zA-Z0-9_]+',
                '_',
                'g'
            )
        )
        WHERE username IS NULL
        """
    )
    op.alter_column("usuarios", "username", nullable=False)
    op.create_index(op.f("ix_usuarios_username"), "usuarios", ["username"], unique=False)
    op.create_unique_constraint("uq_usuarios_username", "usuarios", ["username"])


def downgrade() -> None:
    op.drop_constraint("uq_usuarios_username", "usuarios", type_="unique")
    op.drop_index(op.f("ix_usuarios_username"), table_name="usuarios")
    op.drop_column("usuarios", "username")
