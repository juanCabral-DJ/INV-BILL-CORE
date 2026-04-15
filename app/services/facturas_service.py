from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.models import Cliente, DetalleFactura, Factura, Producto
from app.schemas.schemas import FacturaAnulacion, FacturaCreate, MovimientoInventarioCreate
from app.services.movimiento_service import movimiento_service


class FacturasService:
    def crear_factura(self, db: Session, *, obj_in: FacturaCreate) -> Factura:
        cliente = db.execute(
            select(Cliente).where(Cliente.id == obj_in.cliente_id, Cliente.is_active.is_(True))
        ).scalar_one_or_none()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

        productos_ids = [detalle.producto_id for detalle in obj_in.detalles]
        productos = db.execute(
            select(Producto)
            .where(Producto.id.in_(productos_ids), Producto.is_active.is_(True))
            .with_for_update()
        ).scalars().all()
        productos_map = {producto.id: producto for producto in productos}

        if len(productos_map) != len(set(productos_ids)):
            raise HTTPException(status_code=404, detail="Uno o mas productos no existen o estan inactivos.")

        try:
            factura = Factura(
                cliente_id=obj_in.cliente_id,
                usuario_vendedor=obj_in.usuario_vendedor,
                monto_total=Decimal("0.00"),
                estado="PAGADA",
                is_active=obj_in.is_active,
            )
            db.add(factura)
            db.flush()

            total = Decimal("0.00")
            for detalle_in in obj_in.detalles:
                producto = productos_map[detalle_in.producto_id]
                if producto.stock_actual < detalle_in.cantidad:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock_actual}",
                    )

                subtotal = Decimal(detalle_in.cantidad) * producto.precio_venta
                detalle = DetalleFactura(
                    factura_id=factura.id,
                    producto_id=producto.id,
                    cantidad=detalle_in.cantidad,
                    precio_unitario=producto.precio_venta,
                    subtotal=subtotal,
                )
                db.add(detalle)
                total += subtotal

                movimiento_service.registrar_movimiento(
                    db,
                    obj_in=MovimientoInventarioCreate(
                        producto_id=producto.id,
                        tipo_movimiento="SALIDA",
                        cantidad=detalle_in.cantidad,
                        motivo=f"Venta factura #{factura.numero_factura}",
                        referencia=str(factura.numero_factura),
                        usuario_responsable=obj_in.usuario_vendedor,
                    ),
                    commit=False,
                )

            factura.monto_total = total
            db.add(factura)
            db.commit()
            return self.obtener_factura(db, factura.id)
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"No fue posible registrar la venta: {exc}") from exc

    def anular_factura(self, db: Session, *, factura_id, obj_in: FacturaAnulacion) -> Factura:
        factura = db.execute(
            select(Factura)
            .where(Factura.id == factura_id, Factura.is_active.is_(True))
            .options(joinedload(Factura.detalles))
            .with_for_update()
        ).scalar_one_or_none()

        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        if factura.estado == "ANULADA":
            raise HTTPException(status_code=400, detail="La factura ya fue anulada.")

        try:
            for detalle in factura.detalles:
                movimiento_service.registrar_movimiento(
                    db,
                    obj_in=MovimientoInventarioCreate(
                        producto_id=detalle.producto_id,
                        tipo_movimiento="ENTRADA",
                        cantidad=detalle.cantidad,
                        motivo=f"Anulacion factura #{factura.numero_factura}: {obj_in.motivo_anulacion}",
                        referencia=str(factura.numero_factura),
                        usuario_responsable=obj_in.usuario_responsable,
                    ),
                    commit=False,
                )

            factura.estado = "ANULADA"
            factura.motivo_anulacion = obj_in.motivo_anulacion
            db.add(factura)
            db.commit()
            return self.obtener_factura(db, factura.id)
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"No fue posible anular la factura: {exc}") from exc

    def obtener_factura(self, db: Session, factura_id) -> Factura:
        factura = db.execute(
            select(Factura)
            .where(Factura.id == factura_id, Factura.is_active.is_(True))
            .options(joinedload(Factura.detalles), joinedload(Factura.cliente))
        ).scalars().unique().one_or_none()
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        return factura

    def listar_facturas(self, db: Session, *, skip: int = 0, limit: int = 100):
        stmt = (
            select(Factura)
            .where(Factura.is_active.is_(True))
            .options(joinedload(Factura.detalles), joinedload(Factura.cliente))
            .order_by(Factura.fecha_emision.desc(), Factura.numero_factura.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().unique().all())


facturas_service = FacturasService()
