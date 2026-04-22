from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.models import DetalleFactura, Factura, MovimientoInventario, Producto
from app.schemas.schemas import EstadoInventarioResponse
from app.services.movimiento_service import LOW_STOCK_THRESHOLD, movimiento_service


class ReportesService:
    EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    _ZERO = Decimal("0.00")
    _HUNDRED = Decimal("100.00")

    def estado_inventario(
        self,
        db: Session,
        *,
        umbral_bajo: int = LOW_STOCK_THRESHOLD,
        skip: int = 0,
        limit: int | None = None,
    ):
        stmt = (
            select(Producto)
            .where(Producto.is_active.is_(True))
            .options(joinedload(Producto.categoria))
            .order_by(Producto.nombre.asc())
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        productos = db.execute(stmt).scalars().unique().all()

        return [
            EstadoInventarioResponse(
                producto_id=producto.id,
                producto_nombre=producto.nombre,
                categoria_id=producto.categoria_id,
                categoria_nombre=producto.categoria.nombre,
                stock_actual=producto.stock_actual,
                precio_compra=producto.precio_compra,
                precio_venta=producto.precio_venta,
                valor_inventario=movimiento_service.valor_inventario(producto.stock_actual, producto.precio_compra),
                estado_stock=movimiento_service.clasificar_stock(producto.stock_actual, umbral_bajo),
            )
            for producto in productos
        ]

    def reporte_inventario_excel(self, db: Session, *, umbral_bajo: int = LOW_STOCK_THRESHOLD) -> list[dict[str, object]]:
        productos = db.execute(
            select(Producto)
            .where(Producto.is_active.is_(True))
            .options(joinedload(Producto.categoria))
            .order_by(Producto.nombre.asc())
        ).scalars().unique().all()

        filas: list[dict[str, object]] = []
        for producto in productos:
            stock_actual = producto.stock_actual
            precio_compra = self._decimal(producto.precio_compra)
            precio_venta = self._decimal(producto.precio_venta)
            valor_inventario_costo = self._money(Decimal(stock_actual) * precio_compra)
            valor_inventario_venta = self._money(Decimal(stock_actual) * precio_venta)
            margen_unitario = self._money(precio_venta - precio_compra)
            margen_porcentaje = self._percentage(margen_unitario, precio_venta)
            estado_stock = movimiento_service.clasificar_stock(stock_actual, umbral_bajo)

            filas.append(
                {
                    "producto_id": str(producto.id),
                    "producto_nombre": producto.nombre,
                    "producto_descripcion": producto.descripcion,
                    "categoria_id": str(producto.categoria_id),
                    "categoria_nombre": producto.categoria.nombre,
                    "stock_actual": stock_actual,
                    "umbral_stock_bajo": umbral_bajo,
                    "estado_stock": estado_stock,
                    "es_stock_bajo": estado_stock == "BAJO",
                    "es_agotado": estado_stock == "AGOTADO",
                    "precio_compra": precio_compra,
                    "precio_venta": precio_venta,
                    "margen_unitario": margen_unitario,
                    "margen_porcentaje": margen_porcentaje,
                    "valor_inventario_costo": valor_inventario_costo,
                    "valor_inventario_venta": valor_inventario_venta,
                    "producto_activo": producto.is_active,
                }
            )
        return filas

    def reporte_ventas_excel(self, db: Session) -> list[dict[str, object]]:
        facturas = db.execute(
            select(Factura)
            .where(Factura.is_active.is_(True))
            .options(
                joinedload(Factura.detalles)
                .joinedload(DetalleFactura.producto)
                .joinedload(Producto.categoria)
            )
            .order_by(Factura.fecha_emision.desc(), Factura.numero_factura.desc())
        ).scalars().unique().all()

        filas: list[dict[str, object]] = []
        for factura in facturas:
            fecha = factura.fecha_emision
            for detalle in factura.detalles:
                producto = detalle.producto
                precio_compra = self._decimal(producto.precio_compra)
                precio_unitario = self._decimal(detalle.precio_unitario)
                subtotal = self._decimal(detalle.subtotal)
                costo_total_linea = self._money(precio_compra * Decimal(detalle.cantidad))
                utilidad_linea = self._money(subtotal - costo_total_linea)
                margen_linea_porcentaje = self._percentage(utilidad_linea, subtotal)

                filas.append(
                    {
                        "factura_id": str(factura.id),
                        "detalle_factura_id": str(detalle.id),
                        "numero_factura": factura.numero_factura,
                        "fecha_emision": fecha,
                        "fecha": fecha.date(),
                        "hora": fecha.strftime("%H:%M:%S"),
                        "anio": fecha.year,
                        "mes": fecha.month,
                        "mes_nombre": fecha.strftime("%B"),
                        "trimestre": ((fecha.month - 1) // 3) + 1,
                        "semana_anio": fecha.isocalendar().week,
                        "dia": fecha.day,
                        "dia_semana": fecha.strftime("%A"),
                        "estado_factura": factura.estado,
                        "es_factura_anulada": factura.estado == "ANULADA",
                        "motivo_anulacion": factura.motivo_anulacion or "",
                        "cliente_nombre": factura.cliente_nombre,
                        "cliente_documento": "",
                        "usuario_vendedor": factura.usuario_vendedor,
                        "producto_id": str(producto.id),
                        "producto_nombre": producto.nombre,
                        "producto_descripcion": producto.descripcion,
                        "categoria_id": str(producto.categoria_id),
                        "categoria_nombre": producto.categoria.nombre,
                        "cantidad": detalle.cantidad,
                        "precio_unitario_venta": precio_unitario,
                        "precio_unitario_compra": precio_compra,
                        "subtotal_linea": subtotal,
                        "costo_total_linea": costo_total_linea,
                        "utilidad_linea": utilidad_linea,
                        "margen_linea_porcentaje": margen_linea_porcentaje,
                        "monto_total_factura": self._decimal(factura.monto_total),
                        "monto_pagado": self._decimal(factura.monto_pagado),
                        "cambio_devuelto": self._decimal(factura.cambio_devuelto),
                        "factura_activa": factura.is_active,
                    }
                )
        return filas

    def reporte_movimientos_excel(self, db: Session) -> list[dict[str, object]]:
        movimientos = db.execute(
            select(MovimientoInventario)
            .where(MovimientoInventario.is_active.is_(True))
            .options(joinedload(MovimientoInventario.producto).joinedload(Producto.categoria))
            .order_by(MovimientoInventario.fecha_movimiento.desc())
        ).scalars().unique().all()

        filas: list[dict[str, object]] = []
        for movimiento in movimientos:
            fecha = movimiento.fecha_movimiento
            producto = movimiento.producto
            cantidad_firmada = self._signed_quantity(movimiento.tipo_movimiento, movimiento.cantidad)
            costo_unitario = self._decimal(producto.precio_compra)
            precio_venta_unitario = self._decimal(producto.precio_venta)

            filas.append(
                {
                    "movimiento_id": str(movimiento.id),
                    "fecha_movimiento": fecha,
                    "fecha": fecha.date(),
                    "hora": fecha.strftime("%H:%M:%S"),
                    "anio": fecha.year,
                    "mes": fecha.month,
                    "mes_nombre": fecha.strftime("%B"),
                    "trimestre": ((fecha.month - 1) // 3) + 1,
                    "semana_anio": fecha.isocalendar().week,
                    "dia": fecha.day,
                    "dia_semana": fecha.strftime("%A"),
                    "producto_id": str(producto.id),
                    "producto_nombre": producto.nombre,
                    "producto_descripcion": producto.descripcion,
                    "categoria_id": str(producto.categoria_id),
                    "categoria_nombre": producto.categoria.nombre,
                    "tipo_movimiento": movimiento.tipo_movimiento,
                    "cantidad": movimiento.cantidad,
                    "cantidad_firmada": cantidad_firmada,
                    "motivo": movimiento.motivo,
                    "referencia": movimiento.referencia or "",
                    "usuario_responsable": movimiento.usuario_responsable,
                    "precio_unitario_compra": costo_unitario,
                    "precio_unitario_venta": precio_venta_unitario,
                    "valor_movimiento_costo": self._money(costo_unitario * Decimal(cantidad_firmada)),
                    "valor_movimiento_venta": self._money(precio_venta_unitario * Decimal(cantidad_firmada)),
                    "movimiento_activo": movimiento.is_active,
                }
            )
        return filas

    def archivo_inventario_excel(self, db: Session, *, umbral_bajo: int = LOW_STOCK_THRESHOLD) -> bytes:
        filas = self.reporte_inventario_excel(db=db, umbral_bajo=umbral_bajo)
        return self._build_excel_file(
            sheet_name="Inventario",
            headers=list(filas[0].keys()) if filas else self._inventario_headers(),
            rows=[list(fila.values()) for fila in filas],
        )

    def archivo_ventas_excel(self, db: Session) -> bytes:
        filas = self.reporte_ventas_excel(db=db)
        return self._build_excel_file(
            sheet_name="Ventas",
            headers=list(filas[0].keys()) if filas else self._ventas_headers(),
            rows=[list(fila.values()) for fila in filas],
        )

    def archivo_movimientos_excel(self, db: Session) -> bytes:
        filas = self.reporte_movimientos_excel(db=db)
        return self._build_excel_file(
            sheet_name="Movimientos",
            headers=list(filas[0].keys()) if filas else self._movimientos_headers(),
            rows=[list(fila.values()) for fila in filas],
        )

    def _inventario_headers(self) -> list[str]:
        return [
            "producto_id",
            "producto_nombre",
            "producto_descripcion",
            "categoria_id",
            "categoria_nombre",
            "stock_actual",
            "umbral_stock_bajo",
            "estado_stock",
            "es_stock_bajo",
            "es_agotado",
            "precio_compra",
            "precio_venta",
            "margen_unitario",
            "margen_porcentaje",
            "valor_inventario_costo",
            "valor_inventario_venta",
            "producto_activo",
        ]

    def _ventas_headers(self) -> list[str]:
        return [
            "factura_id",
            "detalle_factura_id",
            "numero_factura",
            "fecha_emision",
            "fecha",
            "hora",
            "anio",
            "mes",
            "mes_nombre",
            "trimestre",
            "semana_anio",
            "dia",
            "dia_semana",
            "estado_factura",
            "es_factura_anulada",
            "motivo_anulacion",
            "cliente_nombre",
            "cliente_documento",
            "usuario_vendedor",
            "producto_id",
            "producto_nombre",
            "producto_descripcion",
            "categoria_id",
            "categoria_nombre",
            "cantidad",
            "precio_unitario_venta",
            "precio_unitario_compra",
            "subtotal_linea",
            "costo_total_linea",
            "utilidad_linea",
            "margen_linea_porcentaje",
            "monto_total_factura",
            "monto_pagado",
            "cambio_devuelto",
            "factura_activa",
        ]

    def _movimientos_headers(self) -> list[str]:
        return [
            "movimiento_id",
            "fecha_movimiento",
            "fecha",
            "hora",
            "anio",
            "mes",
            "mes_nombre",
            "trimestre",
            "semana_anio",
            "dia",
            "dia_semana",
            "producto_id",
            "producto_nombre",
            "producto_descripcion",
            "categoria_id",
            "categoria_nombre",
            "tipo_movimiento",
            "cantidad",
            "cantidad_firmada",
            "motivo",
            "referencia",
            "usuario_responsable",
            "precio_unitario_compra",
            "precio_unitario_venta",
            "valor_movimiento_costo",
            "valor_movimiento_venta",
            "movimiento_activo",
        ]

    def _build_excel_file(self, *, sheet_name: str, headers: list[str], rows: list[list[object]]) -> bytes:
        output = BytesIO()
        with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", self._content_types_xml())
            workbook.writestr("_rels/.rels", self._root_rels_xml())
            workbook.writestr("xl/workbook.xml", self._workbook_xml(sheet_name))
            workbook.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels_xml())
            workbook.writestr("xl/styles.xml", self._styles_xml())
            workbook.writestr("xl/worksheets/sheet1.xml", self._worksheet_xml(headers=headers, rows=rows))
        return output.getvalue()

    def _worksheet_xml(self, *, headers: list[str], rows: list[list[object]]) -> str:
        sheet_rows = [self._row_xml(1, headers, style_index=1)]
        for idx, row in enumerate(rows, start=2):
            sheet_rows.append(self._row_xml(idx, row))

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            f"{''.join(sheet_rows)}"
            "</sheetData>"
            "</worksheet>"
        )

    def _row_xml(self, row_number: int, values: list[object], style_index: int | None = None) -> str:
        cells = []
        for col_idx, value in enumerate(values, start=1):
            cell_ref = f"{self._column_name(col_idx)}{row_number}"
            cells.append(self._cell_xml(cell_ref, value, style_index=style_index))
        return f'<row r="{row_number}">{"".join(cells)}</row>'

    def _cell_xml(self, cell_ref: str, value: object, style_index: int | None = None) -> str:
        style_attr = f' s="{style_index}"' if style_index is not None else ""

        if value is None:
            return f'<c r="{cell_ref}"{style_attr}/>'

        if isinstance(value, bool):
            return f'<c r="{cell_ref}" t="b"{style_attr}><v>{int(value)}</v></c>'

        if isinstance(value, (int, float, Decimal)):
            return f'<c r="{cell_ref}"{style_attr}><v>{value}</v></c>'

        if isinstance(value, datetime):
            value = value.isoformat(sep=" ", timespec="seconds")
        elif isinstance(value, date):
            value = value.isoformat()

        safe_value = escape(str(value))
        return f'<c r="{cell_ref}" t="inlineStr"{style_attr}><is><t>{safe_value}</t></is></c>'

    def _column_name(self, index: int) -> str:
        name = ""
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def _content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>"
        )

    def _root_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _workbook_xml(self, sheet_name: str) -> str:
        safe_sheet_name = escape(sheet_name)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<sheets>"
            f'<sheet name="{safe_sheet_name}" sheetId="1" r:id="rId1"/>'
            "</sheets>"
            "</workbook>"
        )

    def _workbook_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            "</Relationships>"
        )

    def _styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2">'
            '<font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font>'
            "</fonts>"
            '<fills count="2">'
            '<fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            "</fills>"
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            "</cellXfs>"
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )

    def _signed_quantity(self, tipo_movimiento: str, cantidad: int) -> int:
        if tipo_movimiento == "ENTRADA":
            return cantidad
        if tipo_movimiento == "SALIDA":
            return -cantidad
        return cantidad

    def _decimal(self, value: Decimal | int | float) -> Decimal:
        return self._money(Decimal(value))

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _percentage(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == 0:
            return self._ZERO
        return self._money((numerator / denominator) * self._HUNDRED)


reportes_service = ReportesService()
