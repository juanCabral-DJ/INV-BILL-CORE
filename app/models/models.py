import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    productos: Mapped[List["Producto"]] = relationship(back_populates="categoria")


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    categoria_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    precio_compra: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    stock_actual: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    categoria: Mapped["Categoria"] = relationship(back_populates="productos")
    movimientos: Mapped[List["MovimientoInventario"]] = relationship(back_populates="producto")
    detalles_factura: Mapped[List["DetalleFactura"]] = relationship(back_populates="producto")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    correo: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class Factura(Base):
    __tablename__ = "facturas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    numero_factura: Mapped[int] = mapped_column(Identity(start=1), unique=True, index=True, nullable=False)
    cliente_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default=text("0"), nullable=False)
    cambio_devuelto: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default=text("0"), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PAGADA", nullable=False)
    usuario_vendedor: Mapped[str] = mapped_column(String(100), nullable=False)
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    __table_args__ = (
        CheckConstraint("estado IN ('PAGADA', 'ANULADA')", name="chk_facturas_estado"),
    )

    detalles: Mapped[List["DetalleFactura"]] = relationship(
        back_populates="factura",
        cascade="all, delete-orphan",
    )


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"), index=True, nullable=False)
    tipo_movimiento: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_movimiento: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    referencia: Mapped[Optional[str]] = mapped_column(String(100))
    usuario_responsable: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    __table_args__ = (
        CheckConstraint("tipo_movimiento IN ('ENTRADA', 'SALIDA', 'AJUSTE')", name="chk_movimientos_tipo"),
    )

    producto: Mapped["Producto"] = relationship(back_populates="movimientos")

    @property
    def producto_nombre(self) -> Optional[str]:
        return self.producto.nombre if self.producto else None


class DetalleFactura(Base):
    __tablename__ = "detalles_factura"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    factura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facturas.id"), nullable=False)
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    factura: Mapped["Factura"] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship(back_populates="detalles_factura")
