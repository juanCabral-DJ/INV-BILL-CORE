from decimal import Decimal
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.models import MovimientoInventario, Producto
from app.schemas.schemas import MovimientoInventarioCreate

LOW_STOCK_THRESHOLD = 5


class MovimientoService:
    def resumen_movimientos(self, db: Session) -> dict[str, int]:
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (MovimientoInventario.tipo_movimiento == "ENTRADA", MovimientoInventario.cantidad),
                        else_=0,
                    )
                ),
                0,
            ).label("inventory_inflow"),
            func.coalesce(
                func.sum(
                    case(
                        (MovimientoInventario.tipo_movimiento == "SALIDA", MovimientoInventario.cantidad),
                        else_=0,
                    )
                ),
                0,
            ).label("inventory_outflow"),
        ).where(
            MovimientoInventario.is_active.is_(True),
            MovimientoInventario.tipo_movimiento.in_(("ENTRADA", "SALIDA")),
        )

        resumen = db.execute(stmt).mappings().one()
        inventory_inflow = int(resumen["inventory_inflow"] or 0)
        inventory_outflow = int(resumen["inventory_outflow"] or 0)
        return {
            "total_movements": inventory_inflow + inventory_outflow,
            "inventory_inflow": inventory_inflow,
            "inventory_outflow": inventory_outflow,
        }

    def listar_movimientos(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 15,
    ) -> list[MovimientoInventario]:
        stmt = (
            select(MovimientoInventario)
            .where(
                MovimientoInventario.is_active.is_(True),
                MovimientoInventario.tipo_movimiento.in_(("ENTRADA", "SALIDA")),
            )
            .options(joinedload(MovimientoInventario.producto))
            .order_by(MovimientoInventario.fecha_movimiento.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def registrar_movimiento(
        self,
        db: Session,
        *,
        obj_in: MovimientoInventarioCreate,
        commit: bool = True,
    ) -> MovimientoInventario:
        producto = db.execute(
            select(Producto)
            .where(Producto.id == obj_in.producto_id, Producto.is_active.is_(True))
            .with_for_update()
        ).scalar_one_or_none()

        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado o inactivo.")

        nuevo_stock = self._calcular_nuevo_stock(
            stock_actual=producto.stock_actual,
            tipo_movimiento=obj_in.tipo_movimiento,
            cantidad=obj_in.cantidad,
        )

        producto.stock_actual = nuevo_stock
        movimiento = MovimientoInventario(**obj_in.model_dump())
        db.add(producto)
        db.add(movimiento)

        if commit:
            db.commit()
            db.refresh(movimiento)

        return movimiento

    def recalcular_stock(self, movimientos: Iterable[MovimientoInventario]) -> int:
        stock = 0
        for movimiento in movimientos:
            if movimiento.tipo_movimiento == "ENTRADA":
                stock += movimiento.cantidad
            elif movimiento.tipo_movimiento == "SALIDA":
                stock -= movimiento.cantidad
            else:
                stock += movimiento.cantidad
        return stock

    @staticmethod
    def _calcular_nuevo_stock(*, stock_actual: int, tipo_movimiento: str, cantidad: int) -> int:
        if cantidad == 0:
            raise HTTPException(status_code=400, detail="La cantidad del movimiento no puede ser cero.")

        if tipo_movimiento == "ENTRADA":
            if cantidad < 0:
                raise HTTPException(status_code=400, detail="Una entrada no puede ser negativa.")
            return stock_actual + cantidad

        if tipo_movimiento == "SALIDA":
            if cantidad < 0:
                raise HTTPException(status_code=400, detail="Una salida no puede ser negativa.")
            nuevo_stock = stock_actual - cantidad
            if nuevo_stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente. Disponible: {stock_actual}",
                )
            return nuevo_stock

        if tipo_movimiento == "AJUSTE":
            nuevo_stock = stock_actual + cantidad
            if nuevo_stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"El ajuste dejaria stock negativo. Disponible: {stock_actual}",
                )
            return nuevo_stock

        raise HTTPException(status_code=400, detail="Tipo de movimiento no soportado.")

    @staticmethod
    def valor_inventario(stock_actual: int, precio_compra: Decimal) -> Decimal:
        return Decimal(stock_actual) * precio_compra

    @staticmethod
    def clasificar_stock(stock_actual: int, umbral_bajo: int = LOW_STOCK_THRESHOLD) -> str:
        if stock_actual <= 0:
            return "AGOTADO"
        if stock_actual <= umbral_bajo:
            return "BAJO"
        return "DISPONIBLE"


movimiento_service = MovimientoService()
