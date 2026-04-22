"""eliminando tabla clientes

Revision ID: f2a6c4d8b9e1
Revises: e4f2b1a9c8d7
Create Date: 2026-04-15 09:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a6c4d8b9e1"
down_revision: Union[str, Sequence[str], None] = "e4f2b1a9c8d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_clientes_id"), table_name="clientes")
    op.drop_index(op.f("ix_clientes_documento_identidad"), table_name="clientes")
    op.drop_table("clientes")


def downgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("documento_identidad", sa.String(length=50), nullable=False),
        sa.Column("nombre_completo", sa.String(length=150), nullable=False),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clientes_documento_identidad"), "clientes", ["documento_identidad"], unique=True)
    op.create_index(op.f("ix_clientes_id"), "clientes", ["id"], unique=False)
