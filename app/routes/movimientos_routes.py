from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import MovimientoInventarioCreate, MovimientoInventarioResponse
from app.services.movimiento_service import movimiento_service

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.post("/movimientos", response_model=MovimientoInventarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(movimiento_in: MovimientoInventarioCreate, db: Session = Depends(get_db)):
    return movimiento_service.registrar_movimiento(db=db, obj_in=movimiento_in)
