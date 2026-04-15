"""normalizando nombre de id de nuevo

Revision ID: ac3574f06321
Revises:
Create Date: 2026-03-29 19:03:53.534852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ac3574f06321"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categorias",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", name="uq_categorias_nombre"),
    )
    op.create_index(op.f("ix_categorias_id"), "categorias", ["id"], unique=False)

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

    op.create_table(
        "productos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("categoria_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("precio_venta", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("precio_compra", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("stock_actual", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("precio_venta >= 0", name="chk_productos_precio_venta"),
        sa.CheckConstraint("precio_compra >= 0", name="chk_productos_precio_compra"),
        sa.CheckConstraint("stock_actual >= 0", name="chk_productos_stock_actual"),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", name="uq_productos_nombre"),
    )
    op.create_index(op.f("ix_productos_categoria_id"), "productos", ["categoria_id"], unique=False)
    op.create_index(op.f("ix_productos_id"), "productos", ["id"], unique=False)

    op.create_table(
        "facturas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("numero_factura", sa.Integer(), sa.Identity(start=1), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("fecha_emision", sa.DateTime(), nullable=False),
        sa.Column("monto_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("usuario_vendedor", sa.String(length=100), nullable=False),
        sa.Column("motivo_anulacion", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("estado IN ('PAGADA', 'ANULADA')", name="chk_facturas_estado"),
        sa.CheckConstraint("monto_total >= 0", name="chk_facturas_monto_total"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_factura", name="uq_facturas_numero_factura"),
    )
    op.create_index(op.f("ix_facturas_cliente_id"), "facturas", ["cliente_id"], unique=False)
    op.create_index(op.f("ix_facturas_fecha_emision"), "facturas", ["fecha_emision"], unique=False)
    op.create_index(op.f("ix_facturas_id"), "facturas", ["id"], unique=False)
    op.create_index(op.f("ix_facturas_numero_factura"), "facturas", ["numero_factura"], unique=False)

    op.create_table(
        "detalles_factura",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("factura_id", sa.Uuid(), nullable=False),
        sa.Column("producto_id", sa.Uuid(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="chk_detalles_factura_cantidad"),
        sa.CheckConstraint("precio_unitario >= 0", name="chk_detalles_factura_precio_unitario"),
        sa.CheckConstraint("subtotal >= 0", name="chk_detalles_factura_subtotal"),
        sa.ForeignKeyConstraint(["factura_id"], ["facturas.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_detalles_factura_factura_id"), "detalles_factura", ["factura_id"], unique=False)
    op.create_index(op.f("ix_detalles_factura_id"), "detalles_factura", ["id"], unique=False)
    op.create_index(op.f("ix_detalles_factura_producto_id"), "detalles_factura", ["producto_id"], unique=False)

    op.create_table(
        "movimientos_inventario",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("producto_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_movimiento", sa.String(length=20), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("fecha_movimiento", sa.DateTime(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("referencia", sa.String(length=100), nullable=True),
        sa.Column("usuario_responsable", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("tipo_movimiento IN ('ENTRADA', 'SALIDA', 'AJUSTE')", name="chk_movimientos_tipo"),
        sa.CheckConstraint("cantidad <> 0", name="chk_movimientos_cantidad_no_cero"),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_movimientos_inventario_fecha_movimiento"), "movimientos_inventario", ["fecha_movimiento"], unique=False)
    op.create_index(op.f("ix_movimientos_inventario_id"), "movimientos_inventario", ["id"], unique=False)
    op.create_index(op.f("ix_movimientos_inventario_producto_id"), "movimientos_inventario", ["producto_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_movimientos_inventario_producto_id"), table_name="movimientos_inventario")
    op.drop_index(op.f("ix_movimientos_inventario_id"), table_name="movimientos_inventario")
    op.drop_index(op.f("ix_movimientos_inventario_fecha_movimiento"), table_name="movimientos_inventario")
    op.drop_table("movimientos_inventario")

    op.drop_index(op.f("ix_detalles_factura_producto_id"), table_name="detalles_factura")
    op.drop_index(op.f("ix_detalles_factura_id"), table_name="detalles_factura")
    op.drop_index(op.f("ix_detalles_factura_factura_id"), table_name="detalles_factura")
    op.drop_table("detalles_factura")

    op.drop_index(op.f("ix_facturas_numero_factura"), table_name="facturas")
    op.drop_index(op.f("ix_facturas_id"), table_name="facturas")
    op.drop_index(op.f("ix_facturas_fecha_emision"), table_name="facturas")
    op.drop_index(op.f("ix_facturas_cliente_id"), table_name="facturas")
    op.drop_table("facturas")

    op.drop_index(op.f("ix_productos_id"), table_name="productos")
    op.drop_index(op.f("ix_productos_categoria_id"), table_name="productos")
    op.drop_table("productos")

    op.drop_index(op.f("ix_clientes_id"), table_name="clientes")
    op.drop_index(op.f("ix_clientes_documento_identidad"), table_name="clientes")
    op.drop_table("clientes")

    op.drop_index(op.f("ix_categorias_id"), table_name="categorias")
    op.drop_table("categorias")
