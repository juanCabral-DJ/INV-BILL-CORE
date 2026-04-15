"""alineando esquema operativo actual

Revision ID: b7d3a7c2c9d1
Revises: ac3574f06321
Create Date: 2026-04-15 08:18:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d3a7c2c9d1"
down_revision: Union[str, Sequence[str], None] = "ac3574f06321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("productos", sa.Column("descripcion", sa.String(length=255), nullable=True))
    op.add_column("productos", sa.Column("precio_compra", sa.Numeric(precision=18, scale=2), nullable=True))
    op.execute("UPDATE productos SET descripcion = '' WHERE descripcion IS NULL")
    op.execute("UPDATE productos SET precio_compra = 0 WHERE precio_compra IS NULL")
    op.alter_column("productos", "descripcion", nullable=False)
    op.alter_column("productos", "precio_compra", nullable=False)
    op.create_check_constraint("chk_productos_precio_venta", "productos", "precio_venta >= 0")
    op.create_check_constraint("chk_productos_precio_compra", "productos", "precio_compra >= 0")
    op.create_check_constraint("chk_productos_stock_actual", "productos", "stock_actual >= 0")
    op.create_index(op.f("ix_productos_categoria_id"), "productos", ["categoria_id"], unique=False)
    op.drop_index("ix_productos_codigo_sku", table_name="productos")
    op.drop_column("productos", "codigo_sku")

    op.add_column("facturas", sa.Column("numero_factura", sa.Integer(), nullable=True))
    op.add_column("facturas", sa.Column("motivo_anulacion", sa.String(length=255), nullable=True))
    op.execute("CREATE SEQUENCE IF NOT EXISTS facturas_numero_factura_seq START WITH 1 INCREMENT BY 1")
    op.execute(
        """
        WITH numeradas AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY fecha_emision, id) AS numero
            FROM facturas
        )
        UPDATE facturas f
        SET numero_factura = numeradas.numero
        FROM numeradas
        WHERE f.id = numeradas.id
        """
    )
    op.execute(
        "SELECT setval('facturas_numero_factura_seq', COALESCE((SELECT MAX(numero_factura) FROM facturas), 0) + 1, false)"
    )
    op.execute("ALTER TABLE facturas ALTER COLUMN numero_factura SET DEFAULT nextval('facturas_numero_factura_seq')")
    op.alter_column("facturas", "numero_factura", nullable=False)
    op.create_check_constraint("chk_facturas_monto_total", "facturas", "monto_total >= 0")
    op.create_index(op.f("ix_facturas_cliente_id"), "facturas", ["cliente_id"], unique=False)
    op.create_index(op.f("ix_facturas_numero_factura"), "facturas", ["numero_factura"], unique=False)
    op.create_unique_constraint("uq_facturas_numero_factura", "facturas", ["numero_factura"])

    op.create_check_constraint("chk_detalles_factura_cantidad", "detalles_factura", "cantidad > 0")
    op.create_check_constraint(
        "chk_detalles_factura_precio_unitario",
        "detalles_factura",
        "precio_unitario >= 0",
    )
    op.create_check_constraint("chk_detalles_factura_subtotal", "detalles_factura", "subtotal >= 0")
    op.create_index(op.f("ix_detalles_factura_factura_id"), "detalles_factura", ["factura_id"], unique=False)
    op.create_index(op.f("ix_detalles_factura_producto_id"), "detalles_factura", ["producto_id"], unique=False)

    op.add_column("movimientos_inventario", sa.Column("referencia", sa.String(length=100), nullable=True))
    op.create_check_constraint(
        "chk_movimientos_cantidad_no_cero",
        "movimientos_inventario",
        "cantidad <> 0",
    )


def downgrade() -> None:
    op.drop_constraint("chk_movimientos_cantidad_no_cero", "movimientos_inventario", type_="check")
    op.drop_column("movimientos_inventario", "referencia")

    op.drop_index(op.f("ix_detalles_factura_producto_id"), table_name="detalles_factura")
    op.drop_index(op.f("ix_detalles_factura_factura_id"), table_name="detalles_factura")
    op.drop_constraint("chk_detalles_factura_subtotal", "detalles_factura", type_="check")
    op.drop_constraint("chk_detalles_factura_precio_unitario", "detalles_factura", type_="check")
    op.drop_constraint("chk_detalles_factura_cantidad", "detalles_factura", type_="check")

    op.drop_constraint("uq_facturas_numero_factura", "facturas", type_="unique")
    op.drop_index(op.f("ix_facturas_numero_factura"), table_name="facturas")
    op.drop_index(op.f("ix_facturas_cliente_id"), table_name="facturas")
    op.drop_constraint("chk_facturas_monto_total", "facturas", type_="check")
    op.execute("ALTER TABLE facturas ALTER COLUMN numero_factura DROP DEFAULT")
    op.drop_column("facturas", "motivo_anulacion")
    op.drop_column("facturas", "numero_factura")
    op.execute("DROP SEQUENCE IF EXISTS facturas_numero_factura_seq")

    op.add_column("productos", sa.Column("codigo_sku", sa.String(length=50), nullable=True))
    op.execute("UPDATE productos SET codigo_sku = id::text WHERE codigo_sku IS NULL")
    op.alter_column("productos", "codigo_sku", nullable=False)
    op.create_index("ix_productos_codigo_sku", "productos", ["codigo_sku"], unique=True)
    op.drop_index(op.f("ix_productos_categoria_id"), table_name="productos")
    op.drop_constraint("chk_productos_stock_actual", "productos", type_="check")
    op.drop_constraint("chk_productos_precio_compra", "productos", type_="check")
    op.drop_constraint("chk_productos_precio_venta", "productos", type_="check")
    op.drop_column("productos", "precio_compra")
    op.drop_column("productos", "descripcion")
