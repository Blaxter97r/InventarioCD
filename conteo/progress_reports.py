from collections import defaultdict
from decimal import Decimal
from io import BytesIO

from django.db.models.functions import Upper
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
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


def secondary_quantity_difference_rows(warehouse, scope, aisle):
    warehouse = _normalize(warehouse)
    scope = _normalize(scope)
    aisle = _normalize(aisle)
    config = LOCATION_CONFIGS.get((warehouse, "SECUNDARIO"))
    if not config or not scope or not aisle:
        return []

    locations = set()
    for location in Ubicacion.objects.filter(
        bodega__iexact=warehouse, tipo__iexact="SECUNDARIO"
    ).values_list("ubicacion", flat=True):
        normalized = _normalize(location)
        dimensions = _parse_location(normalized, config)
        if (
            dimensions
            and dimensions[config["scope_key"]] == scope
            and dimensions["pasillo"] == aisle
        ):
            locations.add(normalized)

    current_rge = CargaRGE.objects.first()
    current_count = CargaConteoInventario.objects.first()
    if not locations or not current_rge or not current_count:
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
