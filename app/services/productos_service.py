from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.base.crud_base import CRUDBase
from app.models.models import Producto
from app.schemas.schemas import ProductoCreate, ProductoUpdate
from app.services.movimiento_service import LOW_STOCK_THRESHOLD


class ProductosService(CRUDBase[Producto, ProductoCreate, ProductoUpdate]):
    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 15) -> List[Producto]:
        stmt = (
            select(Producto)
            .where(Producto.is_active.is_(True))
            .options(joinedload(Producto.categoria))
            .order_by(Producto.nombre.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().unique().all())

    def get_by_categoria(self, db: Session, categoria_id: UUID, *, skip: int = 0, limit: int = 15) -> List[Producto]:
        stmt = (
            select(Producto)
            .where(Producto.is_active.is_(True), Producto.categoria_id == categoria_id)
            .options(joinedload(Producto.categoria))
            .order_by(Producto.nombre.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().unique().all())

    def get_stock_bajo(
        self,
        db: Session,
        umbral: int = LOW_STOCK_THRESHOLD,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Producto]:
        stmt = (
            select(Producto)
            .where(Producto.is_active.is_(True), Producto.stock_actual <= umbral)
            .options(joinedload(Producto.categoria))
            .order_by(Producto.stock_actual.asc(), Producto.nombre.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().unique().all())

    def count_activos(self, db: Session) -> int:
        return db.execute(
            select(func.count()).select_from(Producto).where(Producto.is_active.is_(True))
        ).scalar_one()

    def count_stock_bajo(self, db: Session, umbral: int = LOW_STOCK_THRESHOLD) -> int:
        return db.execute(
            select(func.count())
            .select_from(Producto)
            .where(Producto.is_active.is_(True), Producto.stock_actual <= umbral)
        ).scalar_one()

    def sum_valor_precio_compra(self, db: Session) -> Decimal:
        return db.execute(
            select(func.coalesce(func.sum(Producto.precio_compra * Producto.stock_actual), 0))
            .select_from(Producto)
            .where(Producto.is_active.is_(True))
        ).scalar_one()


productos_service = ProductosService(model=Producto)
