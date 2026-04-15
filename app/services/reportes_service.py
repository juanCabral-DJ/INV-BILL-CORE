from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.models import DetalleFactura, Factura, Producto
from app.schemas.schemas import EstadoInventarioResponse, InventarioReporteRow, VentaReporteRow
from app.services.movimiento_service import movimiento_service


class ReportesService:
    EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def estado_inventario(self, db: Session, *, umbral_bajo: int = 5):
        productos = db.execute(
            select(Producto)
            .where(Producto.is_active.is_(True))
            .options(joinedload(Producto.categoria))
            .order_by(Producto.nombre.asc())
        ).scalars().unique().all()

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

    def reporte_inventario_excel(self, db: Session, *, umbral_bajo: int = 5):
        estado = self.estado_inventario(db, umbral_bajo=umbral_bajo)
        return [
            InventarioReporteRow(
                producto_id=item.producto_id,
                producto_nombre=item.producto_nombre,
                categoria_nombre=item.categoria_nombre,
                stock_actual=item.stock_actual,
                precio_compra=item.precio_compra,
                precio_venta=item.precio_venta,
                costo_total_inventario=item.valor_inventario,
                estado_stock=item.estado_stock,
            )
            for item in estado
        ]

    def reporte_ventas_excel(self, db: Session):
        facturas = db.execute(
            select(Factura)
            .where(Factura.is_active.is_(True))
            .options(
                joinedload(Factura.cliente),
                joinedload(Factura.detalles).joinedload(DetalleFactura.producto),
            )
            .order_by(Factura.fecha_emision.desc(), Factura.numero_factura.desc())
        ).scalars().unique().all()

        filas = []
        for factura in facturas:
            for detalle in factura.detalles:
                filas.append(
                    VentaReporteRow(
                        numero_factura=factura.numero_factura,
                        fecha_emision=factura.fecha_emision,
                        estado=factura.estado,
                        cliente_documento=factura.cliente.documento_identidad,
                        cliente_nombre=factura.cliente.nombre_completo,
                        producto_id=detalle.producto_id,
                        producto_nombre=detalle.producto.nombre,
                        cantidad=detalle.cantidad,
                        precio_unitario=detalle.precio_unitario,
                        subtotal=detalle.subtotal,
                        monto_total_factura=factura.monto_total,
                        usuario_vendedor=factura.usuario_vendedor,
                    )
                )
        return filas

    def archivo_inventario_excel(self, db: Session, *, umbral_bajo: int = 5) -> bytes:
        filas = self.reporte_inventario_excel(db=db, umbral_bajo=umbral_bajo)
        encabezados = [
            "Producto ID",
            "Producto",
            "Categoria",
            "Stock Actual",
            "Precio Compra",
            "Precio Venta",
            "Costo Total Inventario",
            "Estado Stock",
        ]
        datos = [
            [
                str(fila.producto_id),
                fila.producto_nombre,
                fila.categoria_nombre,
                fila.stock_actual,
                fila.precio_compra,
                fila.precio_venta,
                fila.costo_total_inventario,
                fila.estado_stock,
            ]
            for fila in filas
        ]
        return self._build_excel_file(sheet_name="Inventario", headers=encabezados, rows=datos)

    def archivo_ventas_excel(self, db: Session) -> bytes:
        filas = self.reporte_ventas_excel(db=db)
        encabezados = [
            "Numero Factura",
            "Fecha Emision",
            "Estado",
            "Documento Cliente",
            "Nombre Cliente",
            "Producto ID",
            "Producto",
            "Cantidad",
            "Precio Unitario",
            "Subtotal",
            "Monto Total Factura",
            "Usuario Vendedor",
        ]
        datos = [
            [
                fila.numero_factura,
                fila.fecha_emision,
                fila.estado,
                fila.cliente_documento,
                fila.cliente_nombre,
                str(fila.producto_id),
                fila.producto_nombre,
                fila.cantidad,
                fila.precio_unitario,
                fila.subtotal,
                fila.monto_total_factura,
                fila.usuario_vendedor,
            ]
            for fila in filas
        ]
        return self._build_excel_file(sheet_name="Ventas", headers=encabezados, rows=datos)

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


reportes_service = ReportesService()
