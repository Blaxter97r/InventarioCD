from collections import defaultdict
from decimal import Decimal
from html import escape
from io import BytesIO

from django.db.models.functions import Upper
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle
from pypdf import PdfReader, PdfWriter

from archivos.models import (
    CargaConteoBE,
    CargaConteoInventario,
    CargaRGE,
    DetalleConteoInventario,
    DetalleConteoBE,
    DetalleRGE,
    Sublinea,
    Ubicacion,
)


WAREHOUSES = {
    "central": "Bodega Central",
    "ransa": "RANSA",
}
SUMMARY_WAREHOUSES = (
    ("AGDOSA", "AGDOSA"),
    ("Lourdes", "Lourdes"),
    ("Miramar", "Miramar"),
    ("central", "Bodega Central"),
    ("ransa", "RANSA"),
    ("pedregal", "Pedregal"),
)


def _normalize(value):
    return str(value or "").strip().upper()


def _warehouse_key(value):
    normalized = _normalize(value)
    if "RANSA" in normalized:
        return "ransa"
    if "CENTRAL" in normalized:
        return "central"
    return None


def _count_warehouse_key(value):
    return _warehouse_key(value)


def _location_warehouses():
    return {
        _normalize(location): _warehouse_key(warehouse)
        for location, warehouse in Ubicacion.objects.values_list("ubicacion", "bodega")
    }


def attach_warehouse_options(recounts):
    """Añade los códigos por bodega, usando RGE para los que no tienen conteo."""
    selected_by_load = {
        load.pk: {_normalize(item.codigo) for item in load.codigos_reconteo}
        for load in recounts
    }
    all_codes = set().union(*selected_by_load.values()) if selected_by_load else set()
    warehouses_by_code = defaultdict(set)
    counted_codes = set()
    current_count = CargaConteoInventario.objects.first()

    if current_count and all_codes:
        details = (
            DetalleConteoInventario.objects.filter(carga=current_count)
            .annotate(normalized_code=Upper("codigo"))
            .filter(normalized_code__in=all_codes)
            .values_list("codigo", "bodega")
        )
        for code, warehouse_name in details:
            counted_codes.add(_normalize(code))
            warehouse = _count_warehouse_key(warehouse_name)
            if warehouse:
                warehouses_by_code[_normalize(code)].add(warehouse)

    rge_by_warehouse = _rge_locations_by_warehouse(all_codes - counted_codes)
    for warehouse, codes in rge_by_warehouse.items():
        for code in codes:
            warehouses_by_code[code].add(warehouse)

    for load in recounts:
        selected_codes = selected_by_load[load.pk]
        load.warehouse_options = [
            {
                "key": key,
                "label": label,
                "count": sum(key in warehouses_by_code[code] for code in selected_codes),
            }
            for key, label in WAREHOUSES.items()
        ]
        load.unclassified_codes = sorted(
            code for code in selected_codes if not warehouses_by_code[code]
        )


def _group_scanned_locations(codes, warehouse_key):
    grouped = defaultdict(lambda: defaultdict(Decimal))
    counted_codes = set()
    current_count = CargaConteoInventario.objects.first()
    if not current_count or not codes:
        return grouped, counted_codes
    details = (
        DetalleConteoInventario.objects.filter(carga=current_count)
        .annotate(normalized_code=Upper("codigo"))
        .filter(normalized_code__in=codes)
        .values_list("codigo", "bodega", "ubicacion", "cantidad")
    )
    for code, warehouse_name, location, quantity in details:
        normalized_code = _normalize(code)
        counted_codes.add(normalized_code)
        normalized_location = _normalize(location)
        if _count_warehouse_key(warehouse_name) == warehouse_key:
            grouped[normalized_code][normalized_location] += quantity
    return grouped, counted_codes


def _rge_locations_by_warehouse(codes):
    grouped = defaultdict(lambda: defaultdict(dict))
    current_rge = CargaRGE.objects.first()
    if not current_rge or not codes:
        return grouped
    location_warehouses = _location_warehouses()
    details = (
        DetalleRGE.objects.filter(carga=current_rge)
        .annotate(normalized_code=Upper("codigo"))
        .filter(normalized_code__in=codes)
        .values_list("codigo", "ubicacion", "cantidad")
    )
    for code, location, quantity in details:
        normalized_location = _normalize(location)
        warehouse_key = location_warehouses.get(normalized_location)
        if not warehouse_key:
            continue
        normalized_code = _normalize(code)
        locations = grouped[warehouse_key][normalized_code]
        previous = locations.get(normalized_location)
        if previous is None:
            locations[normalized_location] = quantity
        elif quantity is not None:
            locations[normalized_location] = previous + quantity
    return grouped


def _product_rows(load, warehouse_key):
    selected = list(
        load.diferencias.filter(seleccionada=True).order_by("sublinea", "codigo", "pk")
    )
    all_codes = {_normalize(item.codigo) for item in selected}
    scanned, counted_codes = _group_scanned_locations(all_codes, warehouse_key)
    rge = _rge_locations_by_warehouse(all_codes).get(warehouse_key, {})
    selected = [
        item for item in selected
        if scanned.get(_normalize(item.codigo))
        or (_normalize(item.codigo) not in counted_codes and rge.get(_normalize(item.codigo)))
    ]
    subline_descriptions = {}
    for subline in Sublinea.objects.filter(linea=load.linea):
        subline_descriptions[_normalize(subline.numero)] = subline.descripcion
        subline_descriptions[_normalize(subline.pk)] = subline.descripcion

    rows = []
    for difference in selected:
        code = _normalize(difference.codigo)
        counted_locations = scanned.get(code)
        if counted_locations:
            counted = sorted(counted_locations.items())
        else:
            counted = [(location, Decimal(0)) for location in sorted(rge[code])]
        rows.append(
            {
                "base": [
                    load.linea.nlinea,
                    difference.sublinea,
                    difference.item,
                    difference.codigo,
                    difference.descripcion
                    or subline_descriptions.get(_normalize(difference.sublinea), ""),
                ],
                "scanned": counted,
                "rge": sorted(rge.get(code, {}).items()),
            }
        )
    return rows


def _quantity_text(quantity):
    if quantity is None:
        return "—"
    return format(Decimal(quantity).normalize(), "f")


def _warehouse_summary_rows(load):
    """Suma cada código seleccionado por las seis bodegas del resumen."""
    selected_codes = {
        _normalize(code)
        for code in load.diferencias.filter(seleccionada=True).values_list("codigo", flat=True)
    }
    totals = {code: {key: Decimal(0) for key, _ in SUMMARY_WAREHOUSES} for code in selected_codes}
    if not selected_codes:
        return []

    be_load = CargaConteoBE.objects.first()
    if be_load:
        be_details = (
            DetalleConteoBE.objects.filter(carga=be_load)
            .annotate(normalized_code=Upper("codigo"))
            .filter(normalized_code__in=selected_codes)
            .values_list("codigo", "bodega", "cantidad")
        )
        for code, warehouse, quantity in be_details:
            totals[_normalize(code)][warehouse] += quantity

    inventory_load = CargaConteoInventario.objects.first()
    if inventory_load:
        inventory_details = (
            DetalleConteoInventario.objects.filter(carga=inventory_load)
            .annotate(normalized_code=Upper("codigo"))
            .filter(normalized_code__in=selected_codes)
            .values_list("codigo", "bodega", "cantidad")
        )
        for code, warehouse, quantity in inventory_details:
            normalized_warehouse = _normalize(warehouse)
            if "PEDREGAL" in normalized_warehouse:
                key = "pedregal"
            else:
                key = _count_warehouse_key(warehouse)
            if key:
                totals[_normalize(code)][key] += quantity

    return [
        [code, *(totals[code][key] for key, _ in SUMMARY_WAREHOUSES), sum(totals[code].values())]
        for code in sorted(selected_codes)
    ]


def _report_styles():
    styles = getSampleStyleSheet()
    return {
        "heading": ParagraphStyle(
            "RecountHeading", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=16, leading=19, textColor=colors.HexColor("#123A4A"),
            alignment=TA_CENTER, spaceAfter=4 * mm,
        ),
        "metadata": ParagraphStyle(
            "RecountMetadata", parent=styles["Normal"], fontName="Helvetica",
            fontSize=8, leading=11, textColor=colors.HexColor("#536269"),
            alignment=TA_CENTER, spaceAfter=5 * mm,
        ),
        "section": ParagraphStyle(
            "RecountSection", parent=styles["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=colors.white,
            backColor=colors.HexColor("#123A4A"),
            borderPadding=(3 * mm, 3 * mm, 3 * mm, 3 * mm), spaceAfter=3 * mm,
        ),
        "cell": ParagraphStyle(
            "RecountCell", parent=styles["Normal"], fontName="Helvetica",
            fontSize=6.5, leading=8, textColor=colors.HexColor("#263D47"), alignment=TA_LEFT,
        ),
        "cell_center": ParagraphStyle(
            "RecountCellCenter", parent=styles["Normal"], fontName="Helvetica",
            fontSize=6.5, leading=8, textColor=colors.HexColor("#263D47"), alignment=TA_CENTER,
        ),
        "cell_right": ParagraphStyle(
            "RecountCellRight", parent=styles["Normal"], fontName="Helvetica",
            fontSize=6.5, leading=8, textColor=colors.HexColor("#263D47"), alignment=TA_RIGHT,
        ),
        "summary_header": ParagraphStyle(
            "RecountSummaryHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
            fontSize=7, leading=8, textColor=colors.white, alignment=TA_CENTER,
        ),
    }


def _pdf_table(rows, source, styles):
    data = [["Línea", "Sublínea", "ITEM", "Código", "Descripción", "Ubicación", "Cantidad"]]
    for report_row in rows:
        for location, quantity in report_row[source] or [("—", None)]:
            base = report_row["base"]
            data.append(
                [
                    Paragraph(escape(str(base[0] or "—")), styles["cell_center"]),
                    Paragraph(escape(str(base[1] or "—")), styles["cell_center"]),
                    Paragraph(escape(str(base[2] or "—")), styles["cell_center"]),
                    Paragraph(escape(str(base[3] or "—")), styles["cell"]),
                    Paragraph(escape(str(base[4] or "—")), styles["cell"]),
                    Paragraph(escape(str(location or "—")), styles["cell"]),
                    Paragraph(escape(_quantity_text(quantity)), styles["cell_right"]),
                ]
            )

    table = LongTable(
        data,
        colWidths=(14 * mm, 17 * mm, 15 * mm, 31 * mm, 102 * mm, 57 * mm, 25 * mm),
        repeatRows=1,
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#087F76")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D7DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFA")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.8 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8 * mm),
            ]
        )
    )
    return table


def _warehouse_summary_table(rows, styles):
    data = [[
        Paragraph("Código", styles["summary_header"]),
        *(Paragraph(escape(label), styles["summary_header"]) for _, label in SUMMARY_WAREHOUSES),
        Paragraph("Total", styles["summary_header"]),
    ]]
    for code, *quantities in rows:
        data.append([
            Paragraph(escape(code), styles["cell"]),
            *(_quantity_text(quantity) for quantity in quantities),
        ])
    if rows:
        data.append([
            Paragraph("TOTAL SELECCIONADO", styles["cell"]),
            *(_quantity_text(sum(row[column] for row in rows)) for column in range(1, 8)),
        ])
    else:
        data.append(["—", *(["0"] * 7)])
    table = LongTable(
        data,
        colWidths=[43 * mm, *([32 * mm] * 6), 28 * mm],
        repeatRows=1,
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#087F76")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D7DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        *((
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2F4F1")),
            ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
        ) if rows else ()),
    ]))
    return table


def _draw_page_footer(canvas, document):
    canvas.saveState()
    page_width = landscape(A4)[0]
    canvas.setStrokeColor(colors.HexColor("#D7E1E3"))
    canvas.setLineWidth(0.4)
    canvas.line(document.leftMargin, 12 * mm, page_width - document.rightMargin, 12 * mm)
    canvas.setFillColor(colors.HexColor("#718087"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(document.leftMargin, 8 * mm, "Inventario 2026")
    canvas.drawRightString(page_width - document.rightMargin, 8 * mm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def build_recount_pdf(load, warehouse_key):
    if warehouse_key not in WAREHOUSES:
        raise ValueError("Bodega no válida")
    rows = _product_rows(load, warehouse_key)
    summary_rows = _warehouse_summary_rows(load)
    styles = _report_styles()
    manager_name = load.seleccionado_por.get_full_name() or load.seleccionado_por.username
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=landscape(A4), leftMargin=8 * mm, rightMargin=8 * mm,
        topMargin=8 * mm, bottomMargin=17 * mm,
        title="Formato de reconteo de inventario", author="Inventario 2026",
    )
    metadata = (
        f"{escape(WAREHOUSES[warehouse_key])} &nbsp;|&nbsp; "
        f"Línea {escape(str(load.linea.nlinea))} - {escape(load.linea.descripcion)} &nbsp;|&nbsp; "
        f"Reconteo #{load.numero_reconteo} &nbsp;|&nbsp; Seleccionado por: {escape(manager_name)}"
    )
    story = [
        Paragraph("FORMATO DE RECONTEO DE INVENTARIO", styles["heading"]),
        Paragraph(metadata, styles["metadata"]),
        Paragraph("1. CANTIDADES CONTADAS POR UBICACIÓN", styles["section"]),
        _pdf_table(rows, "scanned", styles),
        PageBreak(),
        Paragraph("2. UBICACIONES SEGÚN RGE", styles["section"]),
        Spacer(1, 1 * mm),
        _pdf_table(rows, "rge", styles),
        PageBreak(),
        Paragraph("3. RESUMEN DE CANTIDADES CONTADAS POR BODEGA", styles["section"]),
        Spacer(1, 1 * mm),
        _warehouse_summary_table(summary_rows, styles),
    ]
    if not CargaConteoBE.objects.exists():
        story.insert(-1, Paragraph(
            "Conteo BE pendiente de carga: AGDOSA, Lourdes y Miramar se muestran en cero.",
            styles["metadata"],
        ))
    if not CargaConteoInventario.objects.exists():
        story.insert(-1, Paragraph(
            "Conteo de inventario pendiente de carga: Central, RANSA y Pedregal se muestran en cero.",
            styles["metadata"],
        ))
    document.build(story, onFirstPage=_draw_page_footer, onLaterPages=_draw_page_footer)
    if not load.archivo_as400:
        return output.getvalue()

    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(output.getvalue())))
    with load.archivo_as400.storage.open(load.archivo_as400.name, "rb") as as400_file:
        writer.append(PdfReader(as400_file))
        merged_output = BytesIO()
        writer.write(merged_output)
    writer.close()
    return merged_output.getvalue()
