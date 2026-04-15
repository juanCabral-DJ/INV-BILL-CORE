from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import ClienteCreate, ClienteResponse, ClienteUpdate
from app.services.clientes_service import clientes_service

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(db: Session = Depends(get_db)):
    return clientes_service.get_multi(db=db)


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: UUID, db: Session = Depends(get_db)):
    cliente = clientes_service.get(db=db, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente


@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def crear_cliente(cliente_in: ClienteCreate, db: Session = Depends(get_db)):
    return clientes_service.create(db=db, obj_in=cliente_in)


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(cliente_id: UUID, cliente_in: ClienteUpdate, db: Session = Depends(get_db)):
    cliente = clientes_service.get(db=db, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return clientes_service.update(db=db, db_obj=cliente, obj_in=cliente_in)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(cliente_id: UUID, db: Session = Depends(get_db)):
    cliente = clientes_service.get(db=db, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    clientes_service.delete(db=db, id=cliente_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
