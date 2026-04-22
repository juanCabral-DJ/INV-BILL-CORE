from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import (
    ConteoProductosResponse,
    ProductoCreate,
    ProductoResponse,
    ProductoUpdate,
    SumaPrecioCompraResponse,
)
from app.services.movimiento_service import LOW_STOCK_THRESHOLD
from app.services.productos_service import productos_service

router = APIRouter(
    prefix="/productos",
    tags=["productos"],
)


@router.get("/", response_model=List[ProductoResponse])
def listar_productos(
    categoria_id: UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(15, ge=1),
    db: Session = Depends(get_db),
):
    if categoria_id:
        return productos_service.get_by_categoria(db=db, categoria_id=categoria_id, skip=offset, limit=limit)
    return productos_service.get_multi(db=db, skip=offset, limit=limit)


@router.get("/stock-bajo/conteo", response_model=ConteoProductosResponse)
def contar_productos_stock_bajo(
    umbral: int = Query(LOW_STOCK_THRESHOLD, ge=0),
    db: Session = Depends(get_db),
):
    return {"total": productos_service.count_stock_bajo(db=db, umbral=umbral)}


@router.get("/activos/conteo", response_model=ConteoProductosResponse)
def contar_productos_activos(db: Session = Depends(get_db)):
    return {"total": productos_service.count_activos(db=db)}


@router.get("/precio-compra/suma", response_model=SumaPrecioCompraResponse)
def sumar_precio_compra_productos(db: Session = Depends(get_db)):
    return {"total": productos_service.sum_valor_precio_compra(db=db)}


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: UUID, db: Session = Depends(get_db)):
    producto = productos_service.get(db=db, id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return producto


@router.post("/", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
def crear_producto(producto_in: ProductoCreate, db: Session = Depends(get_db)):
    return productos_service.create(db=db, obj_in=producto_in)


@router.put("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(producto_id: UUID, producto_in: ProductoUpdate, db: Session = Depends(get_db)):
    producto = productos_service.get(db=db, id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return productos_service.update(db=db, db_obj=producto, obj_in=producto_in)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(producto_id: UUID, db: Session = Depends(get_db)):
    producto = productos_service.get(db=db, id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    productos_service.delete(db=db, id=producto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
