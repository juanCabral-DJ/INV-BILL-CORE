from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import (
    MovimientoInventarioCreate,
    MovimientoInventarioResponse,
    ResumenMovimientosInventarioResponse,
)
from app.services.movimiento_service import movimiento_service

router = APIRouter(
    prefix="/inventario",
    tags=["inventario"],
)


@router.get("/movimientos/resumen", response_model=ResumenMovimientosInventarioResponse)
def resumen_movimientos(db: Session = Depends(get_db)):
    return movimiento_service.resumen_movimientos(db=db)


@router.get("/movimientos", response_model=List[MovimientoInventarioResponse])
def listar_movimientos(
    offset: int = Query(0, ge=0),
    limit: int = Query(15, ge=1),
    db: Session = Depends(get_db),
):
    return movimiento_service.listar_movimientos(db=db, skip=offset, limit=limit)


@router.post("/movimientos", response_model=MovimientoInventarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(movimiento_in: MovimientoInventarioCreate, db: Session = Depends(get_db)):
    return movimiento_service.registrar_movimiento(db=db, obj_in=movimiento_in)
