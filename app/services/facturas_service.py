from decimal import Decimal

from io import BytesIO
from textwrap import wrap

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.Config import settings
from app.models.models import DetalleFactura, Factura, Producto
from app.schemas.schemas import FacturaAnulacion, FacturaCreate, MovimientoInventarioCreate
from app.services.movimiento_service import movimiento_service


class FacturasService:
    TICKET_WIDTH_CHARS = 32
    PDF_PAGE_WIDTH = 226
    PDF_MIN_PAGE_HEIGHT = 320
    PDF_MARGIN_X = 12
    PDF_MARGIN_Y = 18
    PDF_FONT_SIZE = 9
    PDF_LINE_HEIGHT = 11

    def crear_factura(self, db: Session, *, obj_in: FacturaCreate) -> Factura:
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
                cliente_nombre=obj_in.cliente_nombre,
                usuario_vendedor=obj_in.usuario_vendedor,
                monto_total=Decimal("0.00"),
                monto_pagado=Decimal("0.00"),
                cambio_devuelto=Decimal("0.00"),
                estado="PAGADA",
                is_active=obj_in.is_active,
            )
            db.add(factura)
            db.flush()

            total = Decimal("0.00")
            detalles_a_guardar: list[tuple[Producto, int, Decimal]] = []
            for detalle_in in obj_in.detalles:
                producto = productos_map[detalle_in.producto_id]
                if producto.stock_actual < detalle_in.cantidad:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock_actual}",
                    )

                subtotal = Decimal(detalle_in.cantidad) * producto.precio_venta
                total += subtotal
                detalles_a_guardar.append((producto, detalle_in.cantidad, subtotal))

            monto_pagado = self._normalize_money(obj_in.monto_pagado)
            total = self._normalize_money(total)
            if monto_pagado < total:
                raise HTTPException(
                    status_code=400,
                    detail=f"El monto pagado es insuficiente. Total factura: {self._format_money(total)}",
                )

            cambio_devuelto = self._normalize_money(monto_pagado - total)

            for producto, cantidad, subtotal in detalles_a_guardar:
                detalle = DetalleFactura(
                    factura_id=factura.id,
                    producto_id=producto.id,
                    cantidad=cantidad,
                    precio_unitario=producto.precio_venta,
                    subtotal=subtotal,
                )
                db.add(detalle)

                movimiento_service.registrar_movimiento(
                    db,
                    obj_in=MovimientoInventarioCreate(
                        producto_id=producto.id,
                        tipo_movimiento="SALIDA",
                        cantidad=cantidad,
                        motivo=f"Venta factura #{factura.numero_factura}",
                        referencia=str(factura.numero_factura),
                        usuario_responsable=obj_in.usuario_vendedor,
                    ),
                    commit=False,
                )

            factura.monto_total = total
            factura.monto_pagado = monto_pagado
            factura.cambio_devuelto = cambio_devuelto
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
            .options(joinedload(Factura.detalles).joinedload(DetalleFactura.producto))
        ).scalars().unique().one_or_none()
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        return factura

    def listar_facturas(self, db: Session, *, skip: int = 0, limit: int = 15):
        stmt = (
            select(Factura)
            .where(Factura.is_active.is_(True))
            .options(joinedload(Factura.detalles).joinedload(DetalleFactura.producto))
            .order_by(Factura.fecha_emision.desc(), Factura.numero_factura.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().unique().all())

    def generar_factura_pdf(self, db: Session, *, factura_id) -> tuple[bytes, str]:
        factura = self.obtener_factura(db, factura_id)
        impuesto_pct = Decimal(str(settings.invoice_tax_rate))
        base_gravada = self._calcular_base_gravada(factura.monto_total, impuesto_pct)
        impuesto = (factura.monto_total - base_gravada).quantize(Decimal("0.01"))

        lineas = [
            "FACTURA",
            "=" * self.TICKET_WIDTH_CHARS,
            settings.company_name.upper(),
            f"Direccion: {settings.company_address}",
            f"Ciudad: {settings.company_city}",
            f"Telefono: {settings.company_phone}",
            f"Inicio de actividades: {settings.company_start_date}",
            "",
            f"Numero: {factura.numero_factura:08d}",
            f"Fecha: {factura.fecha_emision.strftime('%d/%m/%Y %H:%M:%S')}",
            f"Estado: {factura.estado}",
            f"Cliente: {factura.cliente_nombre}",
            f"Vendedor: {factura.usuario_vendedor}",
            "Condicion IVA cliente: Consumidor final",
            "",
            "DETALLE",
            "-" * self.TICKET_WIDTH_CHARS,
        ]

        for detalle in factura.detalles:
            nombre = detalle.producto.nombre if detalle.producto else f"Producto {detalle.producto_id}"
            lineas.extend(
                [
                    f"Producto: {nombre}",
                    self._format_item_line(detalle.cantidad, detalle.precio_unitario, detalle.subtotal),
                    "-" * self.TICKET_WIDTH_CHARS,
                ]
            )

        lineas.extend(
            [
                "",
                "RESUMEN",
                "-" * self.TICKET_WIDTH_CHARS,
                f"Subtotal gravado: {self._format_money(base_gravada)}",
                f"ITBIS {self._format_tax_label(impuesto_pct)}: {self._format_money(impuesto)}",
                f"TOTAL FACTURA: {self._format_money(factura.monto_total)}",
                "",
                f"Pago efectivo: {self._format_money(factura.monto_pagado)}",
                f"Cambio: {self._format_money(factura.cambio_devuelto)}",
                f"CAE: {str(factura.id).replace('-', '').upper()[:14]}",
                f"Vto. CAE: {factura.fecha_emision.strftime('%Y-%m-%d')}",
            ]
        )

        if factura.estado == "ANULADA" and factura.motivo_anulacion:
            lineas.extend(["", "MOTIVO ANULACION", factura.motivo_anulacion])

        lineas.extend(["", "Gracias por su compra", "Documento generado por INV-BILL-CORE"])

        pdf_content = self._build_pdf(self._wrap_lines(lineas, self.TICKET_WIDTH_CHARS))
        filename = f"factura_{factura.numero_factura:08d}.pdf"
        return pdf_content, filename

    def _format_item_line(self, cantidad: int, precio_unitario: Decimal, subtotal: Decimal) -> str:
        return (
            f"{cantidad} x {self._format_money(precio_unitario)}"
            f" = {self._format_money(subtotal)}"
        )

    def _truncate(self, valor: str, max_len: int) -> str:
        return valor if len(valor) <= max_len else f"{valor[: max_len - 3]}..."

    def _format_money(self, valor: Decimal) -> str:
        return f"{valor.quantize(Decimal('0.01')):.2f}"

    def _normalize_money(self, valor: Decimal) -> Decimal:
        return Decimal(valor).quantize(Decimal("0.01"))

    def _format_tax_label(self, tasa: Decimal) -> str:
        porcentaje = (tasa * Decimal("100")).quantize(Decimal("0.01"))
        texto = f"{porcentaje}".rstrip("0").rstrip(".")
        return f"{texto}%"

    def _calcular_base_gravada(self, total: Decimal, tasa: Decimal) -> Decimal:
        if tasa <= 0:
            return total.quantize(Decimal("0.01"))
        divisor = Decimal("1.00") + tasa
        return (total / divisor).quantize(Decimal("0.01"))

    def _wrap_lines(self, lines: list[str], width: int) -> list[str]:
        wrapped_lines: list[str] = []
        for line in lines:
            sanitized = " ".join(str(line or "").split())
            if not sanitized:
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(wrap(sanitized, width=width) or [""])
        return wrapped_lines

    def _build_pdf(self, lines: list[str]) -> bytes:
        page_height = max(
            self.PDF_MIN_PAGE_HEIGHT,
            (len(lines) * self.PDF_LINE_HEIGHT) + (self.PDF_MARGIN_Y * 2) + 12,
        )
        pages = [lines or [""]]

        objects = [
            self._pdf_object(1, self._pdf_catalog_object()),
            self._pdf_object(2, self._pdf_pages_object(len(pages))),
            self._pdf_object(3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"),
        ]

        page_object_id = 4
        for page_lines in pages:
            content_object_id = page_object_id + 1
            objects.append(self._pdf_object(page_object_id, self._pdf_page_object(content_object_id, page_height)))
            objects.append(self._pdf_stream_object(content_object_id, self._build_pdf_text_stream(page_lines, page_height)))
            page_object_id += 2

        pdf = BytesIO()
        pdf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = [0]
        for obj in objects:
            offsets.append(pdf.tell())
            pdf.write(obj)

        xref_offset = pdf.tell()
        pdf.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        pdf.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))

        pdf.write(
            (
                f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("ascii")
        )
        return pdf.getvalue()

    def _build_pdf_text_stream(self, lines: list[str], page_height: int) -> bytes:
        start_y = page_height - self.PDF_MARGIN_Y
        commands = [
            "BT",
            f"/F1 {self.PDF_FONT_SIZE} Tf",
            f"{self.PDF_LINE_HEIGHT} TL",
            f"1 0 0 1 {self.PDF_MARGIN_X} {start_y} Tm",
        ]
        for index, line in enumerate(lines):
            commands.append(f"({self._escape_pdf_text(line)}) Tj")
            if index != len(lines) - 1:
                commands.append("T*")
        commands.append("ET")
        return "\n".join(commands).encode("cp1252", errors="replace")

    def _escape_pdf_text(self, text: str) -> str:
        return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _pdf_object(self, object_id: int, body: bytes) -> bytes:
        return f"{object_id} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    def _pdf_stream_object(self, object_id: int, stream: bytes) -> bytes:
        header = f"{object_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii")
        return header + stream + b"\nendstream\nendobj\n"

    def _pdf_catalog_object(self) -> bytes:
        return b"<< /Type /Catalog /Pages 2 0 R >>"

    def _pdf_pages_object(self, page_count: int) -> bytes:
        kids = " ".join(f"{4 + index * 2} 0 R" for index in range(page_count))
        return f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii")

    def _pdf_page_object(self, content_object_id: int, page_height: int) -> bytes:
        return (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.PDF_PAGE_WIDTH} {page_height}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_id} 0 R >>"
        ).encode("ascii")


facturas_service = FacturasService()
