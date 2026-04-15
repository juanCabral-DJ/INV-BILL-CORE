from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.db_connection import get_db
from app.schemas.schemas import CategoriaCreate, CategoriaResponse, CategoriaUpdate
from app.services.categorias_service import categorias_service

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("/", response_model=List[CategoriaResponse])
def listar_categorias(db: Session = Depends(get_db)):
    return categorias_service.get_multi(db=db)


@router.get("/{categoria_id}", response_model=CategoriaResponse)
def obtener_categoria(categoria_id: UUID, db: Session = Depends(get_db)):
    categoria = categorias_service.get(db=db, id=categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada.")
    return categoria


@router.post("/", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def crear_categoria(categoria_in: CategoriaCreate, db: Session = Depends(get_db)):
    return categorias_service.create(db=db, obj_in=categoria_in)


@router.put("/{categoria_id}", response_model=CategoriaResponse)
def actualizar_categoria(categoria_id: UUID, categoria_in: CategoriaUpdate, db: Session = Depends(get_db)):
    categoria = categorias_service.get(db=db, id=categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada.")
    return categorias_service.update(db=db, db_obj=categoria, obj_in=categoria_in)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(categoria_id: UUID, db: Session = Depends(get_db)):
    categoria = categorias_service.get(db=db, id=categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada.")
    categorias_service.delete(db=db, id=categoria_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
