from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CategoriaBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class CategoriaResponse(CategoriaBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class ProductoBase(BaseModel):
    categoria_id: UUID
    nombre: str = Field(..., max_length=150)
    descripcion: str = Field(..., max_length=255)
    precio_venta: Decimal = Field(..., ge=0)
    precio_compra: Decimal = Field(..., ge=0)
    is_active: bool = True


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    categoria_id: Optional[UUID] = None
    nombre: Optional[str] = Field(None, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio_venta: Optional[Decimal] = Field(None, ge=0)
    precio_compra: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductoResponse(ProductoBase):
    id: UUID
    stock_actual: int

    model_config = ConfigDict(from_attributes=True)


class ConteoProductosResponse(BaseModel):
    total: int


class SumaPrecioCompraResponse(BaseModel):
    total: Decimal


class UsuarioBase(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        validation_alias=AliasChoices("username", "nombre"),
    )
    correo: str = Field(
        ...,
        max_length=150,
        validation_alias=AliasChoices("correo", "email"),
    )
    is_active: bool = True


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=128)


class UsuarioLogin(BaseModel):
    identificador: str = Field(
        ...,
        min_length=3,
        max_length=150,
        validation_alias=AliasChoices("identificador", "username", "correo", "nombre"),
    )
    password: str = Field(..., min_length=8, max_length=128)


class UsuarioCambioPassword(BaseModel):
    identificador: Optional[str] = Field(
        None,
        min_length=3,
        max_length=150,
        validation_alias=AliasChoices("identificador", "username", "correo", "nombre"),
    )
    password_nueva: str = Field(..., min_length=8, max_length=128)


class UsuarioResponse(UsuarioBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    autenticado: bool
    mensaje: str
    usuario: UsuarioResponse
    access_token: str
    token_type: str = "bearer"


class MovimientoInventarioBase(BaseModel):
    producto_id: UUID
    tipo_movimiento: Literal["ENTRADA", "SALIDA", "AJUSTE"]
    cantidad: int = Field(..., ne=0)
    motivo: str = Field(..., max_length=255)
    usuario_responsable: str = Field(..., max_length=100)
    referencia: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class MovimientoInventarioCreate(MovimientoInventarioBase):
    pass


class MovimientoInventarioResponse(MovimientoInventarioBase):
    id: UUID
    producto_nombre: Optional[str] = None
    fecha_movimiento: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumenMovimientosInventarioResponse(BaseModel):
    total_movements: int
    inventory_inflow: int
    inventory_outflow: int


class DetalleFacturaCreate(BaseModel):
    producto_id: UUID
    cantidad: int = Field(..., gt=0)


class DetalleFacturaResponse(BaseModel):
    id: UUID
    producto_id: UUID
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class FacturaBase(BaseModel):
    cliente_nombre: str = Field(..., max_length=150)
    usuario_vendedor: str = Field(..., max_length=100)
    is_active: bool = True


class FacturaCreate(FacturaBase):
    monto_pagado: Decimal = Field(..., gt=0)
    detalles: List[DetalleFacturaCreate] = Field(..., min_length=1)


class FacturaAnulacion(BaseModel):
    motivo_anulacion: str = Field(..., max_length=255)
    usuario_responsable: str = Field(..., max_length=100)


class FacturaResponse(FacturaBase):
    id: UUID
    numero_factura: int
    fecha_emision: datetime
    monto_total: Decimal
    monto_pagado: Decimal
    cambio_devuelto: Decimal
    estado: Literal["PAGADA", "ANULADA"]
    motivo_anulacion: Optional[str]
    detalles: List[DetalleFacturaResponse]

    model_config = ConfigDict(from_attributes=True)


class EstadoInventarioResponse(BaseModel):
    producto_id: UUID
    producto_nombre: str
    categoria_id: UUID
    categoria_nombre: str
    stock_actual: int
    precio_compra: Decimal
    precio_venta: Decimal
    valor_inventario: Decimal
    estado_stock: Literal["DISPONIBLE", "BAJO", "AGOTADO"]


class VentaReporteRow(BaseModel):
    numero_factura: int
    fecha_emision: datetime
    estado: str
    cliente_documento: str
    cliente_nombre: str
    producto_id: UUID
    producto_nombre: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    monto_total_factura: Decimal
    usuario_vendedor: str


class InventarioReporteRow(BaseModel):
    producto_id: UUID
    producto_nombre: str
    categoria_nombre: str
    stock_actual: int
    precio_compra: Decimal
    precio_venta: Decimal
    costo_total_inventario: Decimal
    estado_stock: str
