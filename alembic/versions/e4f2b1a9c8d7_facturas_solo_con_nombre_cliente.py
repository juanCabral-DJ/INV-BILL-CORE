"""facturas solo con nombre cliente

Revision ID: e4f2b1a9c8d7
Revises: b7d3a7c2c9d1
Create Date: 2026-04-15 09:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f2b1a9c8d7"
down_revision: Union[str, Sequence[str], None] = "b7d3a7c2c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("facturas", sa.Column("cliente_nombre", sa.String(length=150), nullable=True))
    op.execute(
        """
        UPDATE facturas f
        SET cliente_nombre = c.nombre_completo
        FROM clientes c
        WHERE f.cliente_id = c.id
        """
    )
    op.execute("UPDATE facturas SET cliente_nombre = 'Cliente general' WHERE cliente_nombre IS NULL")
    op.alter_column("facturas", "cliente_nombre", nullable=False)
    op.drop_index(op.f("ix_facturas_cliente_id"), table_name="facturas")
    op.drop_constraint("facturas_cliente_id_fkey", "facturas", type_="foreignkey")
    op.drop_column("facturas", "cliente_id")


def downgrade() -> None:
    op.add_column("facturas", sa.Column("cliente_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        INSERT INTO clientes (id, documento_identidad, nombre_completo, telefono, email, fecha_registro, is_active)
        SELECT
            ('00000000-0000-0000-0000-' || LPAD(ROW_NUMBER() OVER (ORDER BY nombre) ::text, 12, '0'))::uuid,
            'AUTO-' || LPAD(ROW_NUMBER() OVER (ORDER BY nombre) ::text, 6, '0'),
            nombre,
            NULL,
            NULL,
            NOW(),
            true
        FROM (
            SELECT DISTINCT cliente_nombre AS nombre
            FROM facturas
            WHERE cliente_nombre IS NOT NULL
        ) nombres
        ON CONFLICT (documento_identidad) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE facturas f
        SET cliente_id = c.id
        FROM clientes c
        WHERE c.nombre_completo = f.cliente_nombre
          AND f.cliente_id IS NULL
        """
    )
    op.alter_column("facturas", "cliente_id", nullable=False)
    op.create_foreign_key("facturas_cliente_id_fkey", "facturas", "clientes", ["cliente_id"], ["id"])
    op.create_index(op.f("ix_facturas_cliente_id"), "facturas", ["cliente_id"], unique=False)
    op.drop_column("facturas", "cliente_nombre")
