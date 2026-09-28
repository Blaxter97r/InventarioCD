from collections import Counter, defaultdict
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.db.models.functions import Upper
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from archivos.models import (
    CargaConteoInventario,
    CargaRGE,
    DetalleConteoInventario,
    DetalleRGE,
    Ubicacion,
)

from .models import ValidacionUbicacion
from .progress import LOCATION_CONFIGS, _normalize, _parse_location


def _difference_report_locations(
    warehouse, location_type, scope, aisles, *, require_rge=True
):
    warehouse = _normalize(warehouse)
    location_type = _normalize(location_type)
    scope = _normalize(scope)
    aisles = {_normalize(aisle) for aisle in aisles if _normalize(aisle)}
    config = LOCATION_CONFIGS.get((warehouse, location_type))
    current_rge = CargaRGE.objects.first()
    if not config or not scope or not aisles or (require_rge and not current_rge):
        return set()

    rge_locations = set()
    if require_rge:
        rge_locations = {
            _normalize(location)
            for location in DetalleRGE.objects.filter(carga=current_rge)
            .values_list("ubicacion", flat=True).order_by().distinct()
        }

    locations = set()
    for location in Ubicacion.objects.filter(
        bodega__iexact=warehouse, tipo__iexact=location_type
    ).values_list("ubicacion", flat=True):
        normalized = _normalize(location)
        dimensions = _parse_location(normalized, config)
        if (
            dimensions
            and (not require_rge or normalized in rge_locations)
            and dimensions[config["scope_key"]] == scope
            and dimensions["pasillo"] in aisles
        ):
            locations.add(normalized)
    return locations


def primary_code_difference_rows(warehouse, scope, aisles):
    warehouse = _normalize(warehouse)
    locations = _difference_report_locations(warehouse, "PRIMARIO", scope, aisles)
    current_rge = CargaRGE.objects.first()
    if not locations or not current_rge:
        return []

    codes_by_location = defaultdict(set)
    for code, location in DetalleRGE.objects.filter(
        carga=current_rge, ubicacion__in=locations
    ).values_list("codigo", "ubicacion"):
        normalized_code = _normalize(code)
        if normalized_code:
            codes_by_location[_normalize(location)].add(normalized_code)

    eligible_count_locations = {
        _normalize(location)
        for location in Ubicacion.objects.filter(
            bodega__iexact=warehouse, tipo__iexact="PRIMARIO"
        ).values_list("ubicacion", flat=True)
    }
    current_count = CargaConteoInventario.objects.first()
    counted_codes = set()
    if current_count and eligible_count_locations:
        counted_codes = {
            _normalize(code)
            for code in DetalleConteoInventario.objects.filter(carga=current_count)
            .annotate(ubicacion_normalizada=Upper("ubicacion"))
            .filter(ubicacion_normalizada__in=eligible_count_locations)
            .values_list("codigo", flat=True).order_by().distinct()
            if _normalize(code)
        }

    rows = []
    for location in sorted(locations):
        expected_codes = codes_by_location.get(location, set())
        missing_codes = sorted(expected_codes - counted_codes)
        if not missing_codes:
            continue
        rows.append({
            "location": location,
            "counted_codes": len(expected_codes) - len(missing_codes),
            "total_codes": len(expected_codes),
            "missing_codes": missing_codes,
        })
    return rows


def secondary_quantity_difference_rows_for_aisles(warehouse, scope, aisles):
    warehouse = _normalize(warehouse)
    locations = _difference_report_locations(warehouse, "SECUNDARIO", scope, aisles)

    current_rge = CargaRGE.objects.first()
    current_count = CargaConteoInventario.objects.first()
    if not locations or not current_rge:
        return []

    rge_quantities = defaultdict(Decimal)
    rge_keys_with_quantity = set()
    rge_rows = (
        DetalleRGE.objects.filter(carga=current_rge)
        .annotate(ubicacion_normalizada=Upper("ubicacion"))
        .filter(ubicacion_normalizada__in=locations)
        .values_list("codigo", "ubicacion_normalizada", "cantidad")
    )
    for code, location, quantity in rge_rows:
        if quantity is None:
            continue
        key = (_normalize(location), _normalize(code))
        rge_quantities[key] += quantity
        rge_keys_with_quantity.add(key)

    counted_quantities = defaultdict(Decimal)
    if current_count:
        counted_rows = (
            DetalleConteoInventario.objects.filter(carga=current_count)
            .annotate(ubicacion_normalizada=Upper("ubicacion"))
            .filter(ubicacion_normalizada__in=locations)
            .values_list("codigo", "ubicacion_normalizada", "cantidad")
        )
        for code, location, quantity in counted_rows:
            counted_quantities[(_normalize(location), _normalize(code))] += quantity

    rows = []
    for location, code in sorted(rge_keys_with_quantity):
        key = (location, code)
        if key not in counted_quantities:
            continue
        rge_quantity = rge_quantities[key]
        counted_quantity = counted_quantities[key]
        if counted_quantity == 0:
            continue
        if rge_quantity == counted_quantity:
            continue
        rows.append({
            "location": location,
            "code": code,
            "rge_quantity": rge_quantity,
            "counted_quantity": counted_quantity,
            "difference": counted_quantity - rge_quantity,
        })
    return rows


def secondary_quantity_difference_rows(warehouse, scope, aisle):
    return secondary_quantity_difference_rows_for_aisles(warehouse, scope, [aisle])


def duplicate_scan_rows(warehouse, location_type, scope, aisles):
    locations = _difference_report_locations(
        warehouse, location_type, scope, aisles, require_rge=False
    )
    current_count = CargaConteoInventario.objects.first()
    if not locations or not current_count:
        return []

    scans = Counter()
    counted_rows = (
        DetalleConteoInventario.objects.filter(carga=current_count)
        .annotate(ubicacion_normalizada=Upper("ubicacion"))
        .filter(ubicacion_normalizada__in=locations)
        .values_list("ubicacion_normalizada", "codigo", "cantidad")
    )
    for location, code, quantity in counted_rows:
        normalized_code = _normalize(code)
        if normalized_code:
            scans[(_normalize(location), normalized_code, quantity)] += 1

    return [
        {
            "location": location,
            "code": code,
            "counted_quantity": quantity,
            "scan_count": scan_count,
            "duplicate_count": scan_count - 1,
        }
        for (location, code, quantity), scan_count in sorted(scans.items())
        if scan_count > 1
    ]


def build_filtered_difference_pdf(
    rows, warehouse, location_type, scope, aisles, report_kind="differences"
):
    warehouse = _normalize(warehouse)
    location_type = _normalize(location_type)
    scope = _normalize(scope)
    aisles = sorted({_normalize(aisle) for aisle in aisles if _normalize(aisle)})
    config = LOCATION_CONFIGS[(warehouse, location_type)]
    current_rge = CargaRGE.objects.first()
    current_count = CargaConteoInventario.objects.first()

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=11 * mm,
        bottomMargin=13 * mm,
        title=(
            f"Posibles duplicados - {warehouse.title()}"
            if report_kind == "duplicates"
            else f"Diferencias {location_type.title()} - {warehouse.title()}"
        ),
        author="Inventario 2026",
    )
    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle(
        "ReportEyebrow",
        parent=styles["Normal"],
        textColor=colors.HexColor("#087F76"),
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        spaceAfter=3 * mm,
    )
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#081D29"),
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=23,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    )
    context_style = ParagraphStyle(
        "ReportContext",
        parent=styles["Normal"],
        textColor=colors.HexColor("#52666E"),
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
    )
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["Normal"],
        textColor=colors.HexColor("#344A54"),
        fontSize=7.5,
        leading=10,
    )
    generated_at = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    scope_text = f"{config['scope_label']} {scope}"
    aisle_text = ", ".join(aisles)
    if report_kind == "duplicates":
        report_title = "Posibles escaneos duplicados"
        purpose = (
            "Revisar registros repetidos con la misma ubicación, el mismo código y "
            "la misma cantidad contada."
        )
    elif location_type == "PRIMARIO":
        report_title = "Diferencias de ubicaciones primarias"
        purpose = "Validar códigos esperados en el RGE que aún no aparecen en el conteo vigente."
    else:
        report_title = "Diferencias de ubicaciones secundarias"
        purpose = "Validar cantidades contadas que no coinciden con el RGE por ubicación."
    story = [
        Paragraph("INVENTARIO 2026 · REPORTE DE VALIDACIÓN", eyebrow),
        Paragraph(report_title, title),
        Paragraph(
            f"<b>{escape(warehouse.title())}</b> · {escape(scope_text)} · "
            f"Pasillo(s) {escape(aisle_text)}<br/>{escape(purpose)}",
            context_style,
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            f"RGE: {escape(current_rge.archivo_nombre if current_rge else 'Sin carga')} · "
            f"Conteo: {escape(current_count.archivo_nombre if current_count else 'Sin carga')} · "
            f"Generado: {generated_at}",
            context_style,
        ),
        Spacer(1, 6 * mm),
    ]

    if report_kind == "duplicates":
        data = [[
            "Ubicación",
            "Código",
            "Cantidad contada",
            "Veces escaneado",
            "Posibles duplicados",
        ]]
        data.extend([
            [
                row["location"],
                row["code"],
                _quantity_text(row["counted_quantity"]),
                str(row["scan_count"]),
                str(row["duplicate_count"]),
            ]
            for row in rows
        ])
        widths = (58 * mm, 72 * mm, 48 * mm, 43 * mm, 43 * mm)
    elif location_type == "PRIMARIO":
        data = [["Ubicación", "Códigos contados", "Códigos no contados"]]
        data.extend([
            [
                row["location"],
                f"{row['counted_codes']}/{row['total_codes']}",
                Paragraph(escape(", ".join(row["missing_codes"])), cell_style),
            ]
            for row in rows
        ])
        widths = (55 * mm, 42 * mm, 168 * mm)
    else:
        data = [[
            "Ubicación", "Códigos contados", "Cantidad RGE", "Cantidad contada", "Diferencia"
        ]]
        data.extend([
            [
                row["location"],
                row["code"],
                _quantity_text(row["rge_quantity"]),
                _quantity_text(row["counted_quantity"]),
                _quantity_text(row["difference"]),
            ]
            for row in rows
        ])
        widths = (57 * mm, 68 * mm, 43 * mm, 48 * mm, 43 * mm)
    if not rows:
        data.append(["Sin diferencias para los filtros seleccionados", *([""] * (len(data[0]) - 1))])

    table = LongTable(data, repeatRows=1, colWidths=widths)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#087F76")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), .45, colors.HexColor("#B7C8C6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F8F7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if (report_kind == "duplicates" or location_type == "SECUNDARIO") and rows:
        table_style.append(("ALIGN", (2, 1), (4, -1), "RIGHT"))
    if not rows:
        table_style.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(table_style))
    story.append(table)

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DCE5E7"))
        canvas.line(12 * mm, 9 * mm, landscape(A4)[0] - 12 * mm, 9 * mm)
        canvas.setFillColor(colors.HexColor("#718087"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(12 * mm, 5.5 * mm, "Inventario 2026 · Documento de apoyo para validación")
        canvas.drawRightString(
            landscape(A4)[0] - 12 * mm,
            5.5 * mm,
            f"Página {doc.page}",
        )
        canvas.restoreState()

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return output.getvalue()


def build_secondary_quantity_difference_pdf(rows, warehouse, scope, aisle):
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Diferencias secundarias - pasillo {aisle}",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Diferencias de cantidad · Ubicaciones secundarias", styles["Title"]),
        Paragraph(
            f"{warehouse.title()} · Piso/Zona {scope} · Pasillo {aisle}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]
    data = [[
        "Ubicación",
        "Código",
        "Cantidad RGE",
        "Cantidad contada",
        "Diferencia",
        "Firma auditor",
    ]]
    if rows:
        data.extend([
            [
                row["location"],
                row["code"],
                _quantity_text(row["rge_quantity"]),
                _quantity_text(row["counted_quantity"]),
                _quantity_text(row["difference"]),
                "",
            ]
            for row in rows
        ])
    else:
        data.append(["Sin diferencias para este pasillo", "", "", "", "", ""])
    table = LongTable(
        data,
        repeatRows=1,
        colWidths=(42 * mm, 42 * mm, 32 * mm, 36 * mm, 28 * mm, 62 * mm),
        rowHeights=[9 * mm] + [11 * mm] * (len(data) - 1),
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#087F76")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 1), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), .45, colors.HexColor("#B7C8C6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F8F7")]),
        ("SPAN", (0, 1), (-1, 1)) if not rows else ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    document.build(story)
    return output.getvalue()


def rge_modification_rows():
    current_rge = CargaRGE.objects.first()
    if not current_rge:
        return []

    secondary_locations = {
        _normalize(location)
        for location in Ubicacion.objects.filter(tipo__iexact="SECUNDARIO")
        .values_list("ubicacion", flat=True)
    }
    marked_locations = {
        _normalize(location)
        for location in ValidacionUbicacion.objects.filter(
            carga_rge=current_rge,
            modificar_rge=True,
            ubicacion__in=secondary_locations,
        ).values_list("ubicacion", flat=True)
    }
    if not marked_locations:
        return []

    rge_rows = (
        DetalleRGE.objects.filter(carga=current_rge)
        .annotate(ubicacion_normalizada=Upper("ubicacion"))
        .filter(ubicacion_normalizada__in=marked_locations)
        .values_list("codigo", "ubicacion_normalizada")
    )
    expected_rows = {
        (_normalize(code), _normalize(location))
        for code, location in rge_rows
        if _normalize(code)
    }
    return [
        {"code": code, "location": location, "counted_quantity": Decimal(0)}
        for code, location in sorted(expected_rows)
    ]


def _quantity_text(quantity):
    return format(Decimal(quantity).normalize(), "f")
