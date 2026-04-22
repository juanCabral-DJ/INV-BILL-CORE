from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import EstadoInventarioResponse
from app.services.movimiento_service import LOW_STOCK_THRESHOLD
from app.services.reportes_service import reportes_service

router = APIRouter(
    prefix="/reportes",
    tags=["reportes"],
)


@router.get("/inventario/estado", response_model=List[EstadoInventarioResponse])
def estado_inventario(
    umbral_bajo: int = Query(LOW_STOCK_THRESHOLD, ge=0),
    offset: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    return reportes_service.estado_inventario(db=db, umbral_bajo=umbral_bajo, skip=offset, limit=limit)


@router.get("/inventario/excel")
def inventario_excel(umbral_bajo: int = Query(LOW_STOCK_THRESHOLD, ge=0), db: Session = Depends(get_db)):
    archivo = reportes_service.archivo_inventario_excel(db=db, umbral_bajo=umbral_bajo)
    return StreamingResponse(
        iter([archivo]),
        media_type=reportes_service.EXCEL_CONTENT_TYPE,
        headers={"Content-Disposition": 'attachment; filename="reporte_inventario.xlsx"'},
    )


@router.get("/ventas/excel")
def ventas_excel(db: Session = Depends(get_db)):
    archivo = reportes_service.archivo_ventas_excel(db=db)
    return StreamingResponse(
        iter([archivo]),
        media_type=reportes_service.EXCEL_CONTENT_TYPE,
        headers={"Content-Disposition": 'attachment; filename="reporte_ventas.xlsx"'},
    )


@router.get("/movimientos/excel")
def movimientos_excel(db: Session = Depends(get_db)):
    archivo = reportes_service.archivo_movimientos_excel(db=db)
    return StreamingResponse(
        iter([archivo]),
        media_type=reportes_service.EXCEL_CONTENT_TYPE,
        headers={"Content-Disposition": 'attachment; filename="reporte_movimientos.xlsx"'},
    )
