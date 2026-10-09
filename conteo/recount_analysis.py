from collections import defaultdict

from django.db.models import OuterRef, Prefetch, Subquery
from django.db.models.functions import Upper

from archivos.models import (
    CargaConteoInventario,
    CargaRGE,
    DetalleConteoInventario,
    DetalleRGE,
    Ubicacion,
)

from .models import CargaDiferencias, Diferencia


WAREHOUSE_ORDER = ("central", "ransa", "pedregal")
WAREHOUSE_LABELS = {
    "central": "CD",
    "ransa": "RANSA",
    "pedregal": "PEDREGAL",
}


def _normalize(value):
    return str(value or "").strip().upper()


def _warehouse_key(value):
    normalized = _normalize(value)
    if "RANSA" in normalized:
        return "ransa"
    if "PEDREGAL" in normalized:
        return "pedregal"
    if "CENTRAL" in normalized or normalized == "CD":
        return "central"
    return None


def _warehouse_text(warehouses):
    labels = [
        WAREHOUSE_LABELS[key]
        for key in WAREHOUSE_ORDER
        if key in warehouses
    ]
    return " Y ".join(labels) if labels else "SIN DATOS"


def _audit_comment(warehouses):
    labels = [
        WAREHOUSE_LABELS[key]
        for key in ("ransa", "pedregal")
        if key in warehouses
    ]
    if not labels:
        labels = [WAREHOUSE_LABELS[key] for key in WAREHOUSE_ORDER if key in warehouses]
    joined = " y ".join(labels)
    return f"Esperar folleto de auditoría de {joined}."


def _warehouse_names(warehouses):
    labels = [
        WAREHOUSE_LABELS[key]
        for key in WAREHOUSE_ORDER
        if key in warehouses
    ]
    return " y ".join(labels)


def _location_assignments(codes):
    assignments = defaultdict(lambda: {"primary": set(), "secondary": set()})
    if not codes:
        return assignments

    location_catalog = {
        _normalize(location): {
            "warehouse": _warehouse_key(warehouse),
            "type": _normalize(location_type),
        }
        for location, warehouse, location_type in Ubicacion.objects.order_by().values_list(
            "ubicacion", "bodega", "tipo"
        )
    }

    def add_location(code, location, fallback_warehouse=None):
        catalog_entry = location_catalog.get(_normalize(location), {})
        warehouse = catalog_entry.get("warehouse") or _warehouse_key(fallback_warehouse)
        location_type = catalog_entry.get("type")
        if not warehouse:
            return
        if location_type == "PRIMARIO":
            assignments[_normalize(code)]["primary"].add(warehouse)
        elif location_type == "SECUNDARIO":
            assignments[_normalize(code)]["secondary"].add(warehouse)

    current_rge = CargaRGE.objects.first()
    if current_rge:
        for code, location in (
            DetalleRGE.objects.filter(carga=current_rge)
            .annotate(normalized_code=Upper("codigo"))
            .filter(normalized_code__in=codes)
            .values_list("codigo", "ubicacion")
        ):
            add_location(code, location)

    current_count = CargaConteoInventario.objects.first()
    if current_count:
        for code, warehouse, location in (
            DetalleConteoInventario.objects.filter(carga=current_count)
            .annotate(normalized_code=Upper("codigo"))
            .filter(normalized_code__in=codes)
            .values_list("codigo", "bodega", "ubicacion")
        ):
            add_location(code, location, warehouse)

    return assignments


def build_recount_analysis():
    """Construye el análisis de ubicaciones del reconteo vigente por línea."""
    selected_codes = Diferencia.objects.filter(seleccionada=True).order_by(
        "sublinea", "codigo", "pk"
    )
    latest_load_id = (
        CargaDiferencias.objects.filter(linea_id=OuterRef("linea_id"))
        .order_by("-fecha_carga", "-pk")
        .values("pk")[:1]
    )
    loads = list(
        CargaDiferencias.objects.filter(
            pk=Subquery(latest_load_id),
            estado=CargaDiferencias.Estado.RECONTEO,
            fecha_finalizacion__isnull=True,
            diferencias__seleccionada=True,
            linea__activa=True,
        )
        .select_related("linea", "seleccionado_por")
        .prefetch_related(
            Prefetch("diferencias", queryset=selected_codes, to_attr="codigos_analisis")
        )
        .distinct()
    )
    loads.sort(
        key=lambda load: (
            int(load.linea.nlinea) if load.linea.nlinea.isdigit() else 10**9,
            load.linea.nlinea,
            load.linea_id,
        )
    )

    all_codes = {
        _normalize(difference.codigo)
        for load in loads
        for difference in load.codigos_analisis
    }
    assignments = _location_assignments(all_codes)
    analysis = []
    for load in loads:
        seen_codes = set()
        primary_warehouses = set()
        secondary_warehouses = set()
        missing_primary = []
        missing_secondary = []
        combinations = set()
        for difference in load.codigos_analisis:
            code = _normalize(difference.codigo)
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)
            placement = assignments[code]
            primary = set(placement["primary"])
            secondary = set(placement["secondary"])
            primary_warehouses.update(primary)
            secondary_warehouses.update(secondary)
            if not primary:
                missing_primary.append(difference.codigo)
            if not secondary:
                missing_secondary.append(difference.codigo)
            combinations.add((_warehouse_text(primary), _warehouse_text(secondary)))

        audit_warehouses = (
            primary_warehouses - {"central"}
            if len(primary_warehouses) > 1
            else set()
        )
        audit_comment = _audit_comment(audit_warehouses) if audit_warehouses else ""
        if audit_comment:
            condition = "audit"
            condition_label = "Esperar folleto"
            comment = audit_comment
        elif missing_primary:
            condition = "review"
            condition_label = "Revisar ubicaciones"
            comment = (
                f"No se pudo identificar el Primario de {len(missing_primary)} "
                f"código{'s' if len(missing_primary) != 1 else ''}."
            )
        elif missing_secondary:
            condition = "review"
            condition_label = "Revisar ubicaciones"
            comment = (
                f"No se pudo identificar el Secundario de {len(missing_secondary)} "
                f"código{'s' if len(missing_secondary) != 1 else ''}."
            )
        else:
            other_secondary = secondary_warehouses - primary_warehouses
            if other_secondary:
                condition = "surplus"
                condition_label = "Solo excedente"
                comment = (
                    "Recibirás solo excedente de "
                    f"{_warehouse_names(other_secondary)}."
                )
            else:
                condition = "same_warehouse"
                condition_label = "Misma bodega"
                comment = "No recibirás nada de otra bodega."
        analysis.append(
            {
                "load": load,
                "line": load.linea,
                "code_count": len(seen_codes),
                "combination_count": len(combinations),
                "primary_label": _warehouse_text(primary_warehouses),
                "secondary_label": _warehouse_text(secondary_warehouses),
                "condition": condition,
                "condition_label": condition_label,
                "comment": comment,
                "audit_warehouses": audit_warehouses,
                "audit_comment": audit_comment,
            }
        )
    return analysis
