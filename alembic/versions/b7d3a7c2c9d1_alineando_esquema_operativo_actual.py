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


def _table_columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_indexes(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _table_check_constraints(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_check_constraints(table_name)
        if constraint.get("name")
    }


def _table_unique_constraints(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    productos_columns = _table_columns(inspector, "productos")
    productos_indexes = _table_indexes(inspector, "productos")
    productos_checks = _table_check_constraints(inspector, "productos")

    if "descripcion" not in productos_columns:
        op.add_column("productos", sa.Column("descripcion", sa.String(length=255), nullable=True))
        op.execute("UPDATE productos SET descripcion = '' WHERE descripcion IS NULL")
        op.alter_column("productos", "descripcion", nullable=False)
    if "precio_compra" not in productos_columns:
        op.add_column("productos", sa.Column("precio_compra", sa.Numeric(precision=18, scale=2), nullable=True))
        op.execute("UPDATE productos SET precio_compra = 0 WHERE precio_compra IS NULL")
        op.alter_column("productos", "precio_compra", nullable=False)
    if "chk_productos_precio_venta" not in productos_checks:
        op.create_check_constraint("chk_productos_precio_venta", "productos", "precio_venta >= 0")
    if "chk_productos_precio_compra" not in productos_checks:
        op.create_check_constraint("chk_productos_precio_compra", "productos", "precio_compra >= 0")
    if "chk_productos_stock_actual" not in productos_checks:
        op.create_check_constraint("chk_productos_stock_actual", "productos", "stock_actual >= 0")
    if op.f("ix_productos_categoria_id") not in productos_indexes:
        op.create_index(op.f("ix_productos_categoria_id"), "productos", ["categoria_id"], unique=False)
    if "codigo_sku" in productos_columns:
        if "ix_productos_codigo_sku" in productos_indexes:
            op.drop_index("ix_productos_codigo_sku", table_name="productos")
        op.drop_column("productos", "codigo_sku")

    inspector = sa.inspect(bind)
    facturas_columns = _table_columns(inspector, "facturas")
    facturas_indexes = _table_indexes(inspector, "facturas")
    facturas_checks = _table_check_constraints(inspector, "facturas")
    facturas_unique = _table_unique_constraints(inspector, "facturas")

    if "numero_factura" not in facturas_columns:
        op.add_column("facturas", sa.Column("numero_factura", sa.Integer(), nullable=True))
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
    if "motivo_anulacion" not in facturas_columns:
        op.add_column("facturas", sa.Column("motivo_anulacion", sa.String(length=255), nullable=True))
    if "chk_facturas_monto_total" not in facturas_checks:
        op.create_check_constraint("chk_facturas_monto_total", "facturas", "monto_total >= 0")
    if op.f("ix_facturas_cliente_id") not in facturas_indexes and "cliente_id" in facturas_columns:
        op.create_index(op.f("ix_facturas_cliente_id"), "facturas", ["cliente_id"], unique=False)
    if op.f("ix_facturas_numero_factura") not in facturas_indexes:
        op.create_index(op.f("ix_facturas_numero_factura"), "facturas", ["numero_factura"], unique=False)
    if "uq_facturas_numero_factura" not in facturas_unique:
        op.create_unique_constraint("uq_facturas_numero_factura", "facturas", ["numero_factura"])

    detalles_indexes = _table_indexes(inspector, "detalles_factura")
    detalles_checks = _table_check_constraints(inspector, "detalles_factura")
    if "chk_detalles_factura_cantidad" not in detalles_checks:
        op.create_check_constraint("chk_detalles_factura_cantidad", "detalles_factura", "cantidad > 0")
    if "chk_detalles_factura_precio_unitario" not in detalles_checks:
        op.create_check_constraint(
            "chk_detalles_factura_precio_unitario",
            "detalles_factura",
            "precio_unitario >= 0",
        )
    if "chk_detalles_factura_subtotal" not in detalles_checks:
        op.create_check_constraint("chk_detalles_factura_subtotal", "detalles_factura", "subtotal >= 0")
    if op.f("ix_detalles_factura_factura_id") not in detalles_indexes:
        op.create_index(op.f("ix_detalles_factura_factura_id"), "detalles_factura", ["factura_id"], unique=False)
    if op.f("ix_detalles_factura_producto_id") not in detalles_indexes:
        op.create_index(op.f("ix_detalles_factura_producto_id"), "detalles_factura", ["producto_id"], unique=False)

    movimientos_columns = _table_columns(inspector, "movimientos_inventario")
    movimientos_checks = _table_check_constraints(inspector, "movimientos_inventario")
    if "referencia" not in movimientos_columns:
        op.add_column("movimientos_inventario", sa.Column("referencia", sa.String(length=100), nullable=True))
    if "chk_movimientos_cantidad_no_cero" not in movimientos_checks:
        op.create_check_constraint(
            "chk_movimientos_cantidad_no_cero",
            "movimientos_inventario",
            "cantidad <> 0",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    movimientos_columns = _table_columns(inspector, "movimientos_inventario")
    movimientos_checks = _table_check_constraints(inspector, "movimientos_inventario")
    if "chk_movimientos_cantidad_no_cero" in movimientos_checks:
        op.drop_constraint("chk_movimientos_cantidad_no_cero", "movimientos_inventario", type_="check")
    if "referencia" in movimientos_columns:
        op.drop_column("movimientos_inventario", "referencia")

    inspector = sa.inspect(bind)
    detalles_indexes = _table_indexes(inspector, "detalles_factura")
    detalles_checks = _table_check_constraints(inspector, "detalles_factura")
    if op.f("ix_detalles_factura_producto_id") in detalles_indexes:
        op.drop_index(op.f("ix_detalles_factura_producto_id"), table_name="detalles_factura")
    if op.f("ix_detalles_factura_factura_id") in detalles_indexes:
        op.drop_index(op.f("ix_detalles_factura_factura_id"), table_name="detalles_factura")
    if "chk_detalles_factura_subtotal" in detalles_checks:
        op.drop_constraint("chk_detalles_factura_subtotal", "detalles_factura", type_="check")
    if "chk_detalles_factura_precio_unitario" in detalles_checks:
        op.drop_constraint("chk_detalles_factura_precio_unitario", "detalles_factura", type_="check")
    if "chk_detalles_factura_cantidad" in detalles_checks:
        op.drop_constraint("chk_detalles_factura_cantidad", "detalles_factura", type_="check")

    inspector = sa.inspect(bind)
    facturas_columns = _table_columns(inspector, "facturas")
    facturas_indexes = _table_indexes(inspector, "facturas")
    facturas_checks = _table_check_constraints(inspector, "facturas")
    facturas_unique = _table_unique_constraints(inspector, "facturas")
    if "uq_facturas_numero_factura" in facturas_unique:
        op.drop_constraint("uq_facturas_numero_factura", "facturas", type_="unique")
    if op.f("ix_facturas_numero_factura") in facturas_indexes:
        op.drop_index(op.f("ix_facturas_numero_factura"), table_name="facturas")
    if op.f("ix_facturas_cliente_id") in facturas_indexes:
        op.drop_index(op.f("ix_facturas_cliente_id"), table_name="facturas")
    if "chk_facturas_monto_total" in facturas_checks:
        op.drop_constraint("chk_facturas_monto_total", "facturas", type_="check")
    if "numero_factura" in facturas_columns:
        op.execute("ALTER TABLE facturas ALTER COLUMN numero_factura DROP DEFAULT")
    if "motivo_anulacion" in facturas_columns:
        op.drop_column("facturas", "motivo_anulacion")
    if "numero_factura" in facturas_columns:
        op.drop_column("facturas", "numero_factura")
        op.execute("DROP SEQUENCE IF EXISTS facturas_numero_factura_seq")

    inspector = sa.inspect(bind)
    productos_columns = _table_columns(inspector, "productos")
    productos_indexes = _table_indexes(inspector, "productos")
    productos_checks = _table_check_constraints(inspector, "productos")
    if "codigo_sku" not in productos_columns:
        op.add_column("productos", sa.Column("codigo_sku", sa.String(length=50), nullable=True))
        op.execute("UPDATE productos SET codigo_sku = id::text WHERE codigo_sku IS NULL")
        op.alter_column("productos", "codigo_sku", nullable=False)
    if "ix_productos_codigo_sku" not in productos_indexes:
        op.create_index("ix_productos_codigo_sku", "productos", ["codigo_sku"], unique=True)
    if op.f("ix_productos_categoria_id") in productos_indexes:
        op.drop_index(op.f("ix_productos_categoria_id"), table_name="productos")
    if "chk_productos_stock_actual" in productos_checks:
        op.drop_constraint("chk_productos_stock_actual", "productos", type_="check")
    if "chk_productos_precio_compra" in productos_checks:
        op.drop_constraint("chk_productos_precio_compra", "productos", type_="check")
    if "chk_productos_precio_venta" in productos_checks:
        op.drop_constraint("chk_productos_precio_venta", "productos", type_="check")
    if "precio_compra" in productos_columns:
        op.drop_column("productos", "precio_compra")
    if "descripcion" in productos_columns:
        op.drop_column("productos", "descripcion")
