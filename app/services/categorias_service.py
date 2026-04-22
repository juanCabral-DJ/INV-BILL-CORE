from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.base.crud_base import CRUDBase
from app.models.models import Categoria
from app.schemas.schemas import CategoriaCreate, CategoriaUpdate


class CategoriasService(CRUDBase[Categoria, CategoriaCreate, CategoriaUpdate]):
    @staticmethod
    def _normalizar_nombre(nombre: str) -> str:
        return nombre.strip()

    def _obtener_categoria_por_nombre(
        self,
        db: Session,
        nombre: str,
        *,
        exclude_id: Any | None = None,
    ) -> Categoria | None:
        nombre_normalizado = self._normalizar_nombre(nombre)
        stmt = select(Categoria).where(
            func.lower(func.trim(Categoria.nombre)) == nombre_normalizado.lower(),
        ).order_by(Categoria.id)
        if exclude_id is not None:
            stmt = stmt.where(Categoria.id != exclude_id)
        return db.execute(stmt).scalars().first()

    def _validar_nombre_unico(
        self,
        db: Session,
        nombre: str,
        *,
        exclude_id: Any | None = None,
    ) -> str:
        nombre_normalizado = self._normalizar_nombre(nombre)
        if not nombre_normalizado:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El nombre de la categoria no puede estar vacio.",
            )

        categoria_existente = self._obtener_categoria_por_nombre(
            db,
            nombre_normalizado,
            exclude_id=exclude_id,
        )
        if categoria_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una categoria con ese nombre.",
            )
        return nombre_normalizado

    def create(self, db: Session, *, obj_in: CategoriaCreate) -> Categoria:
        nombre_normalizado = self._validar_nombre_unico(db, obj_in.nombre)
        payload = obj_in.model_copy(update={"nombre": nombre_normalizado})
        return super().create(db=db, obj_in=payload)

    def update(self, db: Session, *, db_obj: Categoria, obj_in: CategoriaUpdate) -> Categoria:
        update_data = obj_in.model_dump(exclude_unset=True)

        if "nombre" in update_data and update_data["nombre"] is not None:
            update_data["nombre"] = self._validar_nombre_unico(
                db,
                update_data["nombre"],
                exclude_id=db_obj.id,
            )

        return super().update(db=db, db_obj=db_obj, obj_in=update_data)


categorias_service = CategoriasService(model=Categoria)
