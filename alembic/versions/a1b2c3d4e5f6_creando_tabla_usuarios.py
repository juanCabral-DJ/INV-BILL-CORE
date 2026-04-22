"""creando tabla usuarios

Revision ID: a1b2c3d4e5f6
Revises: f2a6c4d8b9e1
Create Date: 2026-04-15 11:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f2a6c4d8b9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("correo", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correo"),
    )
    op.create_index(op.f("ix_usuarios_correo"), "usuarios", ["correo"], unique=False)
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usuarios_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_correo"), table_name="usuarios")
    op.drop_table("usuarios")
