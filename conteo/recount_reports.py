from collections import defaultdict
from decimal import Decimal
from html import escape
from io import BytesIO
import logging
import re

from django.db.models.functions import Trim, Upper
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepInFrame,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    TableStyle,
)
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
logger = logging.getLogger(__name__)


WAREHOUSES = {
    "central": "Bodega Central",
    "ransa": "RANSA",
    "pedregal": "Pedregal",
}
EXTERNAL_WAREHOUSES = ("LOURDES", "MIRAMAR", "AGDOSA")
REPORT_WAREHOUSE_LABELS = {
    "central": "CENTRAL",
    "ransa": "RANSA",
    "pedregal": "PEDREGAL",
}
EXTRA_LOCATION_ROWS = 1


def _normalize(value):
    return str(value or "").strip().upper()


def _item_sort_key(value):
    text = str(value or "").strip().upper()
    if not text:
        return (1, ())
    natural_parts = tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.split(r"(\d+)", text)
        if part
    )
    return (0, natural_parts)


def _product_sort_key(row):
    location_types = {location["type"] for location in row["locations"]}
    only_secondary = (
        "SECUNDARIO" in location_types
        and "PRIMARIO" not in location_types
    )
    return (
        0 if only_secondary else 1,
        _item_sort_key(row["base"][2]),
        _normalize(row["base"][3]),
    )


def _warehouse_key(value):
    normalized = _normalize(value)
    if "RANSA" in normalized:
        return "ransa"
    if "PEDREGAL" in normalized:
        return "pedregal"
    if "CENTRAL" in normalized:
        return "central"
    return None


def _count_warehouse_key(value):
    return _warehouse_key(value)


def _location_catalog():
    return {
        _normalize(location): {
            "warehouse": _warehouse_key(warehouse),
            "type": _normalize(location_type),
        }
        for location, warehouse, location_type in Ubicacion.objects.order_by().values_list(
            "ubicacion", "bodega", "tipo"
        ).iterator(chunk_size=2000)
    }


def attach_warehouse_options(recounts):
    """Añade los códigos por bodega, usando RGE para los que no tienen conteo."""
    selected_by_load = {
        load.pk: {_normalize(item.codigo) for item in load.codigos_reconteo}
        for load in recounts
    }
    all_codes = set().union(*selected_by_load.values()) if selected_by_load else set()
    location_catalog = _location_catalog()
    scanned_by_warehouse, _ = _group_all_scanned_locations(all_codes)
    rge_by_warehouse = _rge_locations_by_warehouse(all_codes, location_catalog)
    warehouses_by_code = {
        code: {
            warehouse
            for warehouse in WAREHOUSES
            if _pdf_locations_for_code(
                code,
                warehouse,
                scanned_by_warehouse,
                rge_by_warehouse,
                location_catalog,
            )
        }
        for code in all_codes
    }

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


def _group_all_scanned_locations(codes):
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
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
        warehouse_key = _count_warehouse_key(warehouse_name)
        if warehouse_key:
            grouped[warehouse_key][normalized_code][normalized_location] += quantity
    return grouped, counted_codes


def _group_scanned_locations(codes, warehouse_key):
    grouped, counted_codes = _group_all_scanned_locations(codes)
    return grouped[warehouse_key], counted_codes


def _rge_locations_by_warehouse(codes, location_catalog=None):
    grouped = defaultdict(lambda: defaultdict(dict))
    current_rge = CargaRGE.objects.first()
    if not current_rge or not codes:
        return grouped
    details = list(
        DetalleRGE.objects.filter(carga=current_rge)
        .annotate(normalized_code=Upper("codigo"))
        .filter(normalized_code__in=codes)
        .values_list("codigo", "ubicacion", "cantidad")
    )
    if location_catalog is None:
        locations = {_normalize(location) for _, location, _ in details}
        location_catalog = {
            _normalize(location): {"warehouse": _warehouse_key(warehouse)}
            for location, warehouse in Ubicacion.objects.annotate(
                normalized_location=Upper(Trim("ubicacion"))
            ).filter(normalized_location__in=locations).order_by().values_list(
                "ubicacion", "bodega"
            ).iterator(chunk_size=2000)
        }
    for code, location, quantity in details:
        normalized_location = _normalize(location)
        warehouse_key = location_catalog.get(normalized_location, {}).get("warehouse")
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


def _external_counts(codes):
    totals = {
        code: {warehouse: Decimal(0) for warehouse in EXTERNAL_WAREHOUSES}
        for code in codes
    }
    current_be_count = CargaConteoBE.objects.first()
    if not current_be_count or not codes:
        return totals
    details = (
        DetalleConteoBE.objects.filter(carga=current_be_count)
        .annotate(normalized_code=Upper("codigo"))
        .filter(normalized_code__in=codes)
        .values_list("codigo", "bodega", "cantidad")
    )
    for code, warehouse, quantity in details:
        normalized_warehouse = _normalize(warehouse)
        if normalized_warehouse in EXTERNAL_WAREHOUSES:
            totals[_normalize(code)][normalized_warehouse] += quantity
    return totals


def _filter_pdf_locations(location_rows, warehouse_key):
    """Aplica la matriz Primario/Secundario al PDF de una bodega."""
    primary_warehouses = {
        row_warehouse
        for row_warehouse, row in location_rows
        if row["type"] == "PRIMARIO"
    }
    if warehouse_key in primary_warehouses:
        return [
            row
            for row_warehouse, row in location_rows
            if row["type"] in {"PRIMARIO", "SECUNDARIO"}
            or row_warehouse == warehouse_key
        ]
    if primary_warehouses:
        return [
            row
            for row_warehouse, row in location_rows
            if row_warehouse == warehouse_key
            and row["type"] in {"SECUNDARIO", "—"}
        ]
    return [
        row for row_warehouse, row in location_rows
        if row_warehouse == warehouse_key
    ]


def _pdf_locations_for_code(
    code,
    warehouse_key,
    scanned_by_warehouse,
    rge_by_warehouse,
    location_catalog,
):
    location_rows = []
    warehouse_order = [warehouse_key, *(key for key in WAREHOUSES if key != warehouse_key)]
    for detail_warehouse in warehouse_order:
        counted_by_location = scanned_by_warehouse[detail_warehouse].get(code, {})
        rge_by_location = rge_by_warehouse[detail_warehouse].get(code, {})
        if not counted_by_location and not rge_by_location:
            continue
        displayed_counted = (
            counted_by_location
            if counted_by_location
            else {location: Decimal(0) for location in rge_by_location}
        )
        locations = sorted(
            set(displayed_counted) | set(rge_by_location),
            key=lambda location: (
                {"PRIMARIO": 0, "SECUNDARIO": 1}.get(
                    location_catalog.get(location, {}).get("type"), 2
                ),
                location,
            ),
        )
        location_rows.extend(
            (
                detail_warehouse,
                {
                    "warehouse": REPORT_WAREHOUSE_LABELS[detail_warehouse],
                    "type": location_catalog.get(location, {}).get("type") or "—",
                    "location": location,
                    "rge_quantity": rge_by_location.get(location),
                    "counted_quantity": displayed_counted.get(location),
                },
            )
            for location in locations
        )
    return _filter_pdf_locations(location_rows, warehouse_key)


def _product_rows(load, warehouse_key):
    selected = list(
        load.diferencias.filter(seleccionada=True).order_by("sublinea", "codigo", "pk")
    )
    all_codes = {_normalize(item.codigo) for item in selected}
    scanned_by_warehouse, _ = _group_all_scanned_locations(all_codes)
    location_catalog = _location_catalog()
    rge_by_warehouse = _rge_locations_by_warehouse(all_codes, location_catalog)
    scanned = scanned_by_warehouse[warehouse_key]
    rge = rge_by_warehouse[warehouse_key]
    external_counts = _external_counts(all_codes)
    pdf_locations_by_code = {
        code: _pdf_locations_for_code(
            code,
            warehouse_key,
            scanned_by_warehouse,
            rge_by_warehouse,
            location_catalog,
        )
        for code in all_codes
    }
    selected = [
        item for item in selected
        if pdf_locations_by_code[_normalize(item.codigo)]
    ]
    subline_descriptions = {}
    for subline in Sublinea.objects.filter(linea=load.linea):
        subline_descriptions[_normalize(subline.numero)] = subline.descripcion
        subline_descriptions[_normalize(subline.pk)] = subline.descripcion

    rows = []
    for difference in selected:
        code = _normalize(difference.codigo)
        requested_counted_locations = scanned.get(code)
        if requested_counted_locations:
            counted = sorted(requested_counted_locations.items())
        else:
            counted = [(location, Decimal(0)) for location in sorted(rge[code])]
        combined_locations = pdf_locations_by_code[code]
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
                "last_count": difference.ultimo_conteo,
                "stock": difference.existencia,
                "calculated_difference": difference.ultimo_conteo - difference.existencia,
                "scanned": counted,
                "rge": sorted(rge.get(code, {}).items()),
                "locations": combined_locations,
                "external": [
                    {
                        "warehouse": external_warehouse,
                        "type": "",
                        "location": "",
                        "rge_quantity": None,
                        "counted_quantity": external_counts[code][external_warehouse],
                        "is_external": True,
                    }
                    for external_warehouse in EXTERNAL_WAREHOUSES
                    if external_counts[code][external_warehouse] != 0
                ],
            }
        )
    rows.sort(key=_product_sort_key)
    return rows


def _quantity_text(quantity):
    if quantity is None:
        return "—"
    return format(Decimal(quantity).normalize(), "f")


def _report_styles():
    styles = getSampleStyleSheet()
    return {
        "cell": ParagraphStyle(
            "RecountCell", parent=styles["Normal"], fontName="Helvetica",
            fontSize=5.2, leading=6.3, textColor=colors.HexColor("#263D47"), alignment=TA_LEFT,
        ),
        "cell_center": ParagraphStyle(
            "RecountCellCenter", parent=styles["Normal"], fontName="Helvetica",
            fontSize=5.2, leading=6.3, textColor=colors.HexColor("#263D47"), alignment=TA_CENTER,
        ),
        "cell_right": ParagraphStyle(
            "RecountCellRight", parent=styles["Normal"], fontName="Helvetica",
            fontSize=5.2, leading=6.3, textColor=colors.HexColor("#263D47"), alignment=TA_RIGHT,
        ),
        "summary_header": ParagraphStyle(
            "RecountSummaryHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
            fontSize=5.2, leading=6.3, textColor=colors.white, alignment=TA_CENTER,
        ),
    }


def _combined_inventory_table(rows, styles):
    headers = (
        "Línea", "Sublínea", "ITEM", "Código", "Descripción", "Bodega",
        "Tipo ubicación", "Ubicación", "RGE", "Contado", "Firma auditor",
    )
    data = [
        [Paragraph(header, styles["summary_header"]) for header in headers],
        ["", "", "", "", "", "", "", "", "Cantidad", "Cantidad", ""],
    ]
    product_ranges = []
    product_headers = []
    blank_rows = []
    for product_index, report_row in enumerate(rows):
        base = report_row["base"]
        product_header = len(data)
        identity = (
            f"<b>Línea {escape(str(base[0] or '—'))} · "
            f"Sublínea {escape(str(base[1] or '—'))} · "
            f"ITEM {escape(str(base[2] or '—'))} · "
            f"{escape(str(base[3] or '—'))}</b><br/>"
            f"{escape(str(base[4] or '—'))}"
        )
        continuation_notes = []
        if report_row.get("continuation_from_previous"):
            continuation_notes.append("CONTINUACIÓN DE LA PÁGINA ANTERIOR")
        if report_row.get("continues_next_page"):
            continuation_notes.append("CONTINÚA EN LA PÁGINA SIGUIENTE")
        if continuation_notes:
            identity += (
                "<br/><font color='#9F5A18'><b>"
                + " · ".join(continuation_notes)
                + "</b></font>"
            )
        calculated_difference = report_row["calculated_difference"]
        difference_color = (
            "#9F3030" if calculated_difference < 0
            else "#17695D" if calculated_difference > 0
            else "#536269"
        )
        data.append([
            Paragraph(identity, styles["cell"]), "", "", "", "",
            Paragraph(
                f"<b>Último conteo</b><br/>{escape(_quantity_text(report_row['last_count']))}",
                styles["cell_center"],
            ),
            "",
            Paragraph(
                f"<b>Existencia</b><br/>{escape(_quantity_text(report_row['stock']))}",
                styles["cell_center"],
            ),
            "",
            Paragraph(
                f"<b>Diferencia</b><br/><font color='{difference_color}'>"
                f"<b>{escape(_quantity_text(calculated_difference))}</b></font>",
                styles["cell_center"],
            ),
            "",
        ])
        product_headers.append(product_header)
        first_row = len(data)
        manual_rows = [
            {
                "warehouse": "",
                "type": "",
                "location": "",
                "rge_quantity": None,
                "counted_quantity": None,
                "is_blank": True,
            }
            for _ in range(
                report_row.get("extra_location_rows", EXTRA_LOCATION_ROWS)
            )
        ]
        for detail in report_row["locations"] + report_row["external"] + manual_rows:
            current_row = len(data)
            data.append([
                Paragraph(escape(str(base[0] or "—")), styles["cell_center"]),
                Paragraph(escape(str(base[1] or "—")), styles["cell_center"]),
                Paragraph(escape(str(base[2] or "—")), styles["cell_center"]),
                Paragraph(escape(str(base[3] or "—")), styles["cell"]),
                Paragraph(escape(str(base[4] or "—")), styles["cell"]),
                Paragraph(escape(detail["warehouse"]), styles["cell_center"]),
                Paragraph(escape(detail["type"]), styles["cell_center"]),
                Paragraph(escape(detail["location"]), styles["cell"]),
                Paragraph(
                    "" if detail.get("is_external") or detail.get("is_blank") else escape(_quantity_text(detail["rge_quantity"])),
                    styles["cell_right"],
                ),
                Paragraph(
                    "" if detail.get("is_blank") else escape(_quantity_text(detail["counted_quantity"])),
                    styles["cell_right"],
                ),
                "",
            ])
            if detail.get("is_blank"):
                blank_rows.append(current_row)
        product_ranges.append((first_row, len(data) - 1, product_index))

    if not rows:
        data.append(["—", "—", "—", "Sin productos", "—", "—", "—", "—", "—", "—", ""])

    table = LongTable(
        data,
        colWidths=(8 * mm, 10 * mm, 9 * mm, 19 * mm, 41 * mm, 18 * mm,
                   20 * mm, 26 * mm, 13 * mm, 14 * mm, 22 * mm),
        repeatRows=2,
        hAlign="CENTER",
    )
    commands = [
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#087F76")),
        ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 1), 5.2),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (1, 1)),
        ("SPAN", (2, 0), (2, 1)),
        ("SPAN", (3, 0), (3, 1)),
        ("SPAN", (4, 0), (4, 1)),
        ("SPAN", (5, 0), (5, 1)),
        ("SPAN", (6, 0), (6, 1)),
        ("SPAN", (7, 0), (7, 1)),
        ("SPAN", (10, 0), (10, 1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D7DB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]
    for first_row, last_row, product_index in product_ranges:
        background = colors.white if product_index % 2 == 0 else colors.HexColor("#F2F8F7")
        commands.extend([
            ("BACKGROUND", (0, first_row), (-1, last_row), background),
        ])
    for product_header in product_headers:
        commands.extend([
            ("SPAN", (0, product_header), (4, product_header)),
            ("SPAN", (5, product_header), (6, product_header)),
            ("SPAN", (7, product_header), (8, product_header)),
            ("SPAN", (9, product_header), (10, product_header)),
            ("BACKGROUND", (0, product_header), (-1, product_header), colors.HexColor("#DCEFEB")),
            ("LINEABOVE", (0, product_header), (-1, product_header), 1, colors.HexColor("#4F8F88")),
            ("LINEBELOW", (0, product_header), (-1, product_header), 0.5, colors.HexColor("#7BA9A4")),
            ("TOPPADDING", (0, product_header), (-1, product_header), 2 * mm),
            ("BOTTOMPADDING", (0, product_header), (-1, product_header), 2 * mm),
        ])
    for blank_row in blank_rows:
        commands.extend([
            ("TOPPADDING", (0, blank_row), (-1, blank_row), 3 * mm),
            ("BOTTOMPADDING", (0, blank_row), (-1, blank_row), 3 * mm),
        ])
    table.setStyle(TableStyle(commands))
    return table


def _split_oversized_inventory_row(
    report_row, styles, available_width, available_height
):
    table = _combined_inventory_table([report_row], styles)
    _, table_height = table.wrap(available_width, available_height)
    if table_height <= available_height:
        return [report_row]

    details = [
        *(dict(detail, _detail_group="locations") for detail in report_row["locations"]),
        *(dict(detail, _detail_group="external") for detail in report_row["external"]),
    ]
    if not details:
        return [report_row]

    fragments = []
    offset = 0
    while offset < len(details):
        remaining_count = len(details) - offset
        low, high = 1, remaining_count
        best_count = 0
        while low <= high:
            candidate_count = (low + high) // 2
            is_final = candidate_count == remaining_count
            candidate_details = details[offset:offset + candidate_count]
            candidate = {
                **report_row,
                "locations": [
                    {key: value for key, value in detail.items() if key != "_detail_group"}
                    for detail in candidate_details
                    if detail["_detail_group"] == "locations"
                ],
                "external": [
                    {key: value for key, value in detail.items() if key != "_detail_group"}
                    for detail in candidate_details
                    if detail["_detail_group"] == "external"
                ],
                "continuation_from_previous": bool(fragments),
                "continues_next_page": not is_final,
                "extra_location_rows": EXTRA_LOCATION_ROWS if is_final else 0,
            }
            candidate_table = _combined_inventory_table([candidate], styles)
            _, candidate_height = candidate_table.wrap(
                available_width, available_height
            )
            if candidate_height <= available_height:
                best_count = candidate_count
                low = candidate_count + 1
            else:
                high = candidate_count - 1

        # Incluso una sola fila puede exceder una página con dimensiones
        # atípicas. En ese caso se conserva el encogimiento mínimo existente.
        selected_count = best_count or 1
        is_final = selected_count == remaining_count
        selected_details = details[offset:offset + selected_count]
        fragments.append({
            **report_row,
            "locations": [
                {key: value for key, value in detail.items() if key != "_detail_group"}
                for detail in selected_details
                if detail["_detail_group"] == "locations"
            ],
            "external": [
                {key: value for key, value in detail.items() if key != "_detail_group"}
                for detail in selected_details
                if detail["_detail_group"] == "external"
            ],
            "continuation_from_previous": bool(fragments),
            "continues_next_page": not is_final,
            "extra_location_rows": EXTRA_LOCATION_ROWS if is_final else 0,
        })
        offset += selected_count
    return fragments


def _paginated_inventory_rows(rows, styles, available_width, available_height):
    """Agrupa productos completos por página para no cortar un código."""
    if not rows:
        return [[]]

    render_rows = []
    for report_row in rows:
        render_rows.extend(_split_oversized_inventory_row(
            report_row, styles, available_width, available_height
        ))

    pages = []
    current_page = []
    for report_row in render_rows:
        candidate_page = [*current_page, report_row]
        candidate_table = _combined_inventory_table(candidate_page, styles)
        _, candidate_height = candidate_table.wrap(available_width, available_height)
        if current_page and candidate_height > available_height:
            pages.append(current_page)
            current_page = [report_row]
        else:
            current_page = candidate_page
    pages.append(current_page)
    return pages


def _draw_page_footer(canvas, document):
    canvas.saveState()
    page_width = document.pagesize[0]
    canvas.setStrokeColor(colors.HexColor("#D7E1E3"))
    canvas.setLineWidth(0.4)
    canvas.line(document.leftMargin, 12 * mm, page_width - document.rightMargin, 12 * mm)
    canvas.setFillColor(colors.HexColor("#718087"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(document.leftMargin, 8 * mm, "Inventario 2026")
    canvas.drawCentredString(page_width / 2, 8 * mm, document.recount_label)
    canvas.drawRightString(
        page_width - document.rightMargin,
        8 * mm,
        f"Página {canvas.getPageNumber()}/{document.recount_total_pages}",
    )
    canvas.restoreState()


def _append_as400(report, as400_content):
    writer = PdfWriter()
    try:
        writer.append(PdfReader(BytesIO(report)))
        writer.append(PdfReader(BytesIO(as400_content)))
        merged_output = BytesIO()
        writer.write(merged_output)
        return merged_output.getvalue()
    finally:
        writer.close()


def build_recount_pdf(load, warehouse_key):
    if warehouse_key not in WAREHOUSES:
        raise ValueError("Bodega no válida")
    rows = _product_rows(load, warehouse_key)
    styles = _report_styles()
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=5 * mm, rightMargin=5 * mm,
        topMargin=8 * mm, bottomMargin=17 * mm,
        title="Formato de reconteo de inventario", author="Inventario 2026",
    )
    document.recount_label = (
        f"Línea {load.linea.nlinea} · Reconteo #{load.numero_reconteo} · "
        f"{WAREHOUSES[warehouse_key]}"
    )
    page_rows = _paginated_inventory_rows(rows, styles, document.width, document.height)
    document.recount_total_pages = len(page_rows)
    story = []
    for page_index, rows_for_page in enumerate(page_rows):
        if page_index:
            story.append(PageBreak())
        story.append(KeepInFrame(
            document.width,
            document.height,
            [_combined_inventory_table(rows_for_page, styles)],
            mode="shrink",
        ))
    document.build(story, onFirstPage=_draw_page_footer, onLaterPages=_draw_page_footer)
    report = output.getvalue()
    if load.archivo_as400:
        try:
            with load.archivo_as400.storage.open(load.archivo_as400.name, "rb") as as400_file:
                return _append_as400(report, as400_file.read()), False
        except Exception:
            logger.exception("No se pudo abrir o anexar el AS400 de la carga %s", load.pk)
        return report, True

    return report, False
