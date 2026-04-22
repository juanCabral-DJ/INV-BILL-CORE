from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import FacturaAnulacion, FacturaCreate, FacturaResponse
from app.services.facturas_service import facturas_service

router = APIRouter(
    prefix="/facturas",
    tags=["facturas"],
)


@router.get("/", response_model=List[FacturaResponse])
def listar_facturas(
    offset: int = Query(0, ge=0),
    limit: int = Query(15, ge=1),
    db: Session = Depends(get_db),
):
    return facturas_service.listar_facturas(db=db, skip=offset, limit=limit)


@router.get("/{factura_id}", response_model=FacturaResponse)
def obtener_factura(factura_id: UUID, db: Session = Depends(get_db)):
    return facturas_service.obtener_factura(db=db, factura_id=factura_id)


@router.get(
    "/{factura_id}/ticket",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Factura en formato PDF descargable",
        }
    },
)
def ver_factura_ticket(factura_id: UUID, db: Session = Depends(get_db)):
    pdf_content, filename = facturas_service.generar_factura_pdf(db=db, factura_id=factura_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_content, media_type="application/pdf", headers=headers)


@router.post("/", response_model=FacturaResponse, status_code=status.HTTP_201_CREATED)
def crear_factura(factura_in: FacturaCreate, db: Session = Depends(get_db)):
    return facturas_service.crear_factura(db=db, obj_in=factura_in)


@router.post("/{factura_id}/anular", response_model=FacturaResponse)
def anular_factura(factura_id: UUID, anulacion_in: FacturaAnulacion, db: Session = Depends(get_db)):
    return facturas_service.anular_factura(db=db, factura_id=factura_id, obj_in=anulacion_in)
