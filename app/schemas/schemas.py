from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class ClienteBase(BaseModel):
    documento_identidad: str = Field(..., max_length=50)
    nombre_completo: str = Field(..., max_length=150)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    is_active: bool = True


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    documento_identidad: Optional[str] = Field(None, max_length=50)
    nombre_completo: Optional[str] = Field(None, max_length=150)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class ClienteResponse(ClienteBase):
    id: UUID
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


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
    fecha_movimiento: datetime

    model_config = ConfigDict(from_attributes=True)


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
    cliente_id: UUID
    usuario_vendedor: str = Field(..., max_length=100)
    is_active: bool = True


class FacturaCreate(FacturaBase):
    detalles: List[DetalleFacturaCreate] = Field(..., min_length=1)


class FacturaAnulacion(BaseModel):
    motivo_anulacion: str = Field(..., max_length=255)
    usuario_responsable: str = Field(..., max_length=100)


class FacturaResponse(FacturaBase):
    id: UUID
    numero_factura: int
    fecha_emision: datetime
    monto_total: Decimal
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
