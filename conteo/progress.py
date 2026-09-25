import re
from collections import Counter
from urllib.parse import urlencode

from archivos.models import (
    CargaConteoInventario,
    CargaRGE,
    DetalleConteoInventario,
    DetalleRGE,
    Ubicacion,
)
from django.db.models.functions import Upper

from .models import ValidacionUbicacion


LOCATION_CONFIGS = {
    ("BODEGA CENTRAL", "PRIMARIO"): {
        "pattern": re.compile(
            r"^(?P<piso>[A-Z])(?P<pasillo>\d{2})(?P<lado>[A-Z])-(?P<cuerpo>[A-Z])(?P<nivel>\d{2})$",
            re.IGNORECASE,
        ),
        "scope_key": "piso",
        "scope_label": "Piso",
        "groups": (("pasillo", "Pasillo"), ("lado", "Lado"), ("cuerpo", "Estante")),
        "leaf_key": "nivel",
        "leaf_label": "Nivel",
        "format_help": "Piso · Pasillo · Lado · Estante · Nivel",
    },
    ("BODEGA CENTRAL", "SECUNDARIO"): {
        "pattern": re.compile(
            r"^(?P<piso>[A-Z])(?P<pasillo>\d{2})-(?P<cuerpo>\d{2})(?P<nivel>\d)(?P<lado>[A-Z0-9])$",
            re.IGNORECASE,
        ),
        "scope_key": "piso",
        "scope_label": "Piso",
        # En E08-045Y el lado es la última dimensión física.
        "groups": (("pasillo", "Pasillo"), ("cuerpo", "Estante"), ("nivel", "Nivel")),
        "leaf_key": "lado",
        "leaf_label": "Lado",
        "format_help": "Piso · Pasillo · Estante · Nivel · Lado",
    },
    ("RANSA", "PRIMARIO"): {
        "pattern": re.compile(
            r"^(?P<zona>[A-Z])-(?P<pasillo>\d{2})-(?P<cuerpo>\d{2})-(?P<nivel>\d{2})$",
            re.IGNORECASE,
        ),
        "scope_key": "zona",
        "scope_label": "Zona",
        "groups": (("pasillo", "Pasillo"), ("cuerpo", "Estante"), ("nivel", "Nivel")),
        "leaf_key": None,
        "leaf_label": "Ubicación",
        "format_help": "Zona · Pasillo · Estante · Nivel",
    },
    ("RANSA", "SECUNDARIO"): {
        "pattern": re.compile(
            r"^(?P<zona>[A-Z])-(?P<pasillo>\d{2})-(?P<cuerpo>\d{2})-(?P<nivel>\d{2})$",
            re.IGNORECASE,
        ),
        "scope_key": "zona",
        "scope_label": "Zona",
        "groups": (("pasillo", "Pasillo"), ("cuerpo", "Estante"), ("nivel", "Nivel")),
        "leaf_key": None,
        "leaf_label": "Ubicación",
        "format_help": "Zona · Pasillo · Estante · Nivel",
    },
}

# Se conserva el nombre público usado por pruebas e integraciones existentes.
MEZZANINE_LOCATION_RE = LOCATION_CONFIGS[("BODEGA CENTRAL", "PRIMARIO")]["pattern"]


def _normalize(value):
    return (value or "").strip().upper()


def parse_mezzanine_location(value):
    return _parse_location(value, LOCATION_CONFIGS[("BODEGA CENTRAL", "PRIMARIO")])


def _parse_location(value, config):
    match = config["pattern"].fullmatch((value or "").strip())
    if not match:
        return None
    return {key: item.upper() for key, item in match.groupdict().items()}


def _percentage(counted, expected):
    return round((counted / expected) * 100) if expected else 0


def _progress_summary(locations, counted_locations, validated_locations=None):
    counted = len(locations.intersection(counted_locations))
    validated = len(locations.intersection(validated_locations or set()) - counted_locations)
    expected = len(locations)
    completed = counted + validated
    return {
        "expected": expected,
        "counted": counted,
        "validated": validated,
        "completed": completed,
        "pending": expected - completed,
        "percentage": _percentage(completed, expected),
    }


def _build_reconciliation_data(
    locations,
    current_load,
    current_rge,
    counted_locations=None,
    validated_locations=None,
    modify_rge_locations=None,
):
    if not locations:
        return {}

    counted_location_set = counted_locations or set()
    validated_location_set = validated_locations or set()
    modify_rge_location_set = modify_rge_locations or set()
    products_by_location = {location: set() for location in locations}
    if current_rge:
        for code, location in DetalleRGE.objects.filter(
            carga=current_rge, ubicacion__in=locations
        ).values_list("codigo", "ubicacion"):
            normalized = _normalize(location)
            if normalized in products_by_location:
                products_by_location[normalized].add(_normalize(code))

    product_codes = {code for products in products_by_location.values() for code in products}
    rge_locations_by_code = {}
    if current_rge and product_codes:
        rge_rows = (
            DetalleRGE.objects.filter(carga=current_rge)
            .annotate(codigo_normalizado=Upper("codigo"))
            .filter(codigo_normalizado__in=product_codes)
            .values_list("codigo_normalizado", "ubicacion")
        )
        for code, location in rge_rows:
            rge_locations_by_code.setdefault(_normalize(code), set()).add(
                _normalize(location)
            )

    counted_by_code = {}
    if current_load and product_codes:
        counted_rows = (
            DetalleConteoInventario.objects.filter(carga=current_load)
            .annotate(codigo_normalizado=Upper("codigo"))
            .filter(codigo_normalizado__in=product_codes)
            .values_list("codigo_normalizado", "ubicacion")
            .order_by()
            .distinct()
        )
        for code, location in counted_rows:
            counted_by_code.setdefault(_normalize(code), set()).add(_normalize(location))

    reconciliation = {}
    for location, product_codes_at_location in products_by_location.items():
        products = []
        found_elsewhere = 0
        for code in sorted(product_codes_at_location):
            counted_here = location in counted_by_code.get(code, set())
            other_locations = sorted(counted_by_code.get(code, set()) - {location})
            if other_locations:
                found_elsewhere += 1
            products.append({
                "code": code,
                "expected_location": location,
                "counted_locations": other_locations,
                "unexpected_counted_locations": [
                    counted_location
                    for counted_location in other_locations
                    if counted_location not in rge_locations_by_code.get(code, set())
                ],
                "counted_elsewhere": bool(other_locations),
                "counted_here": counted_here,
            })

        is_counted = location in counted_location_set
        is_validated = location in validated_location_set and not is_counted
        if is_counted:
            status, status_label = "counted", "Contada"
        elif is_validated:
            status, status_label = "validated", "Validada"
        elif products and found_elsewhere == len(products):
            status, status_label = "possible_location_error", "Posible error de ubicación"
        elif found_elsewhere:
            status, status_label = "needs_review", "Revisión necesaria"
        elif products:
            status, status_label = "not_located", "Productos no localizados"
        elif not current_rge:
            status, status_label = "no_rge", "RGE no cargado"
        else:
            status, status_label = "no_reference", "Sin productos en RGE"

        reconciliation[location] = {
            "status": status,
            "status_label": status_label,
            "counted": is_counted,
            "validated": is_validated,
            "modify_rge": location in modify_rge_location_set,
            "expected_products": len(products),
            "found_elsewhere": found_elsewhere,
            "products": products,
        }
    return reconciliation


def _configured_locations(rge_locations):
    result = {key: {} for key in LOCATION_CONFIGS}
    invalid = Counter()
    map_locations = set()
    rows = Ubicacion.objects.order_by().values_list("ubicacion", "bodega", "tipo")
    for location, warehouse, location_type in rows.iterator(chunk_size=2000):
        normalized = _normalize(location)
        map_locations.add(normalized)
        key = (_normalize(warehouse), _normalize(location_type))
        config = LOCATION_CONFIGS.get(key)
        if not config:
            continue
        if normalized not in rge_locations:
            continue
        dimensions = _parse_location(normalized, config)
        if dimensions:
            result[key][normalized] = dimensions
        else:
            invalid[key] += 1
    return result, invalid, map_locations


def _build_tree(scoped_expected, counted, validated, reconciliation, config):
    group_keys = [item[0] for item in config["groups"]]

    def make_level(locations, depth):
        key = group_keys[depth]
        child_key = ("sides", "bodies")[depth] if depth < 2 else None
        nodes = []
        for name in sorted({scoped_expected[item][key] for item in locations}):
            node_locations = {
                location for location in locations if scoped_expected[location][key] == name
            }
            node = {
                "name": name,
                **_progress_summary(node_locations, counted, validated),
            }
            if depth < 2:
                node[child_key] = make_level(node_locations, depth + 1)
            else:
                node["pending_locations"] = []
                node["locations"] = []
                for location in sorted(node_locations):
                    path = [
                        {"label": config["scope_label"], "value": scoped_expected[location][config["scope_key"]]},
                        *[
                            {"label": label, "value": scoped_expected[location][dimension]}
                            for dimension, label in config["groups"]
                        ],
                    ]
                    if config["leaf_key"]:
                        path.append({
                            "label": config["leaf_label"],
                            "value": scoped_expected[location][config["leaf_key"]],
                        })
                    item = {
                        "code": location,
                        "level": scoped_expected[location].get("nivel", ""),
                        "leaf_value": scoped_expected[location].get(config["leaf_key"], "") if config["leaf_key"] else "",
                        "path": path,
                        **reconciliation[location],
                    }
                    node["locations"].append(item)
                    if location not in counted and location not in validated:
                        node["pending_locations"].append(item)
            nodes.append(node)
        return nodes

    return make_level(set(scoped_expected), 0) if scoped_expected else []


def _code_difference_summary(locations, codes_by_location, counted_codes):
    expected_codes = set().union(
        *(codes_by_location.get(location, set()) for location in locations)
    ) if locations else set()
    missing_codes = expected_codes - counted_codes
    return {
        "total_codes": len(expected_codes),
        "missing_codes": len(missing_codes),
        "counted_codes": len(expected_codes) - len(missing_codes),
        "missing_code_list": sorted(missing_codes),
    }


def _build_code_difference_tree(expected, codes_by_location, counted_codes, config):
    """Agrupa los códigos del RGE no encontrados en el conteo por su ubicación teórica."""
    group_keys = [item[0] for item in config["groups"]]

    def make_level(locations, depth):
        key = group_keys[depth]
        nodes = []
        for name in sorted({expected[location][key] for location in locations}):
            node_locations = {
                location for location in locations if expected[location][key] == name
            }
            node = {
                "name": name,
                **_code_difference_summary(node_locations, codes_by_location, counted_codes),
            }
            if depth < len(group_keys) - 1:
                node["children"] = make_level(node_locations, depth + 1)
            else:
                node["locations"] = []
                for location in sorted(node_locations):
                    item = {
                        "code": location,
                        "leaf_value": (
                            expected[location].get(config["leaf_key"], "")
                            if config["leaf_key"] else ""
                        ),
                        **_code_difference_summary(
                            {location}, codes_by_location, counted_codes
                        ),
                    }
                    node["locations"].append(item)
            nodes.append(node)
        return nodes

    return make_level(set(expected), 0) if expected else []


def build_code_differences_dashboard(
    selected_warehouse="", selected_type="", selected_floor=""
):
    """Tablero de códigos esperados por el RGE que aún no aparecen en el conteo."""
    current_load = CargaConteoInventario.objects.first()
    current_rge = CargaRGE.objects.first()
    rge_locations = set()
    if current_rge:
        rge_locations = {
            _normalize(value)
            for value in DetalleRGE.objects.filter(carga=current_rge)
            .values_list("ubicacion", flat=True).order_by().distinct()
        }

    expected_by_config, invalid_by_config, _ = _configured_locations(rge_locations)
    requested_key = (_normalize(selected_warehouse), _normalize(selected_type))
    key = requested_key if requested_key in LOCATION_CONFIGS else ("BODEGA CENTRAL", "PRIMARIO")
    warehouse, location_type = key
    config = LOCATION_CONFIGS[key]
    expected = expected_by_config[key]

    codes_by_location = {location: set() for location in expected}
    if current_rge and expected:
        for code, location in DetalleRGE.objects.filter(
            carga=current_rge, ubicacion__in=expected
        ).values_list("codigo", "ubicacion"):
            normalized_location = _normalize(location)
            normalized_code = _normalize(code)
            if normalized_location in codes_by_location and normalized_code:
                codes_by_location[normalized_location].add(normalized_code)

    counted_codes = set()
    eligible_count_locations = {
        _normalize(location)
        for location, map_warehouse, map_type in Ubicacion.objects.values_list(
            "ubicacion", "bodega", "tipo"
        )
        if (
            _normalize(map_warehouse),
            _normalize(map_type),
        ) == (warehouse, location_type)
    }
    if current_load and eligible_count_locations:
        counted_codes = {
            _normalize(value)
            for value in DetalleConteoInventario.objects.filter(carga=current_load)
            .annotate(ubicacion_normalizada=Upper("ubicacion"))
            .filter(ubicacion_normalizada__in=eligible_count_locations)
            .values_list("codigo", flat=True).order_by().distinct()
            if _normalize(value)
        }

    scope_key = config["scope_key"]
    available_scopes = sorted({dimensions[scope_key] for dimensions in expected.values()})
    selected_scope = _normalize(selected_floor)
    if selected_scope not in available_scopes:
        selected_scope = ""

    scopes = []
    for name in available_scopes:
        scoped_expected = {
            location: dimensions
            for location, dimensions in expected.items()
            if dimensions[scope_key] == name
        }
        scope_locations = set(scoped_expected)
        scopes.append({
            "name": name,
            **_code_difference_summary(scope_locations, codes_by_location, counted_codes),
            "url": "?" + urlencode({
                "bodega": warehouse,
                "tipo": location_type,
                "piso": name,
            }),
            "groups": (
                _build_code_difference_tree(
                    scoped_expected, codes_by_location, counted_codes, config
                )
                if name == selected_scope else []
            ),
        })

    selected_summary = _code_difference_summary(
        set(expected), codes_by_location, counted_codes
    )
    selectors = []
    for selector_warehouse in dict.fromkeys(item[0] for item in LOCATION_CONFIGS):
        selectors.append({
            "name": selector_warehouse.title(),
            "value": selector_warehouse,
            "types": [
                {
                    "name": selector_type.title(),
                    "value": selector_type,
                    "url": "?" + urlencode({
                        "bodega": selector_warehouse,
                        "tipo": selector_type,
                    }),
                }
                for configured_warehouse, selector_type in LOCATION_CONFIGS
                if configured_warehouse == selector_warehouse
            ],
        })

    return {
        "current_load": current_load,
        "current_rge": current_rge,
        "selected_warehouse": warehouse,
        "selected_type": location_type,
        "selectors": selectors,
        "scope_label": config["scope_label"],
        "group_labels": [label for _, label in config["groups"]],
        "leaf_label": config["leaf_label"],
        "format_help": config["format_help"],
        "invalid_total": invalid_by_config[key],
        "location_total": len(expected),
        "scopes": scopes,
        "selected_scope": selected_scope,
        "selected_floor": selected_scope,
        "refresh_query": urlencode({
            "bodega": warehouse,
            "tipo": location_type,
            **({"piso": selected_scope} if selected_scope else {}),
        }),
        **selected_summary,
    }


def _build_general_progress_summary(
    current_load, current_rge, rge_locations, expected_by_config, map_locations
):
    expected_by_group = {
        key: set(locations) for key, locations in expected_by_config.items()
    }
    for location, warehouse, location_type in Ubicacion.objects.values_list(
        "ubicacion", "bodega", "tipo"
    ).iterator(chunk_size=2000):
        normalized_location = _normalize(location)
        key = (_normalize(warehouse), _normalize(location_type))
        if key not in LOCATION_CONFIGS and normalized_location in rge_locations:
            expected_by_group.setdefault(key, set()).add(normalized_location)

    all_expected = set().union(*expected_by_group.values()) if expected_by_group else set()
    counted_locations = set()
    if current_load and all_expected:
        counted_locations = {
            _normalize(value)
            for value in DetalleConteoInventario.objects.filter(carga=current_load)
            .annotate(ubicacion_normalizada=Upper("ubicacion"))
            .filter(ubicacion_normalizada__in=all_expected)
            .values_list("ubicacion_normalizada", flat=True).order_by().distinct()
        }

    validated_locations = set()
    if current_rge and all_expected:
        validated_locations = {
            _normalize(value)
            for value in ValidacionUbicacion.objects.filter(
                carga_rge=current_rge,
                ubicacion__in=all_expected,
                validada=True,
            ).values_list("ubicacion", flat=True)
        } - counted_locations

    configured_warehouses = list(dict.fromkeys(key[0] for key in LOCATION_CONFIGS))
    extra_warehouses = sorted(
        {key[0] for key in expected_by_group} - set(configured_warehouses)
    )
    warehouse_cards = []
    for warehouse in [*configured_warehouses, *extra_warehouses]:
        configured_types = [
            key[1] for key in LOCATION_CONFIGS if key[0] == warehouse
        ]
        extra_types = sorted(
            {key[1] for key in expected_by_group if key[0] == warehouse}
            - set(configured_types)
        )
        type_cards = []
        warehouse_expected = set()
        for location_type in [*configured_types, *extra_types]:
            locations = expected_by_group.get((warehouse, location_type), set())
            warehouse_expected.update(locations)
            type_cards.append({
                "name": location_type.title(),
                "value": location_type,
                **_progress_summary(
                    locations, counted_locations, validated_locations
                ),
            })
        warehouse_cards.append({
            "name": warehouse.title(),
            "value": warehouse,
            "types": type_cards,
            **_progress_summary(
                warehouse_expected, counted_locations, validated_locations
            ),
        })

    return {
        "current_load": current_load,
        "warehouse_cards": warehouse_cards,
        "map_only_total": len(map_locations - rge_locations) if current_rge else 0,
        "rge_only_total": len(rge_locations - map_locations),
    }


def build_progress_dashboard(selected_floor="", selected_warehouse="", selected_type="", *, summary_only=False):
    current_load = CargaConteoInventario.objects.first()
    current_rge = CargaRGE.objects.first()
    rge_locations = set()
    if current_rge:
        rge_locations = {
            _normalize(value)
            for value in DetalleRGE.objects.filter(carga=current_rge)
            .values_list("ubicacion", flat=True).order_by().distinct()
        }

    expected_by_config, invalid_by_config, map_locations = _configured_locations(rge_locations)
    if summary_only:
        return _build_general_progress_summary(
            current_load,
            current_rge,
            rge_locations,
            expected_by_config,
            map_locations,
        )

    all_expected = set().union(*(set(items) for items in expected_by_config.values()))
    counted_locations = set()
    if current_load and all_expected:
        counted_locations = {
            _normalize(value)
            for value in DetalleConteoInventario.objects.filter(carga=current_load)
            .annotate(ubicacion_normalizada=Upper("ubicacion"))
            .filter(ubicacion_normalizada__in=all_expected)
            .values_list("ubicacion_normalizada", flat=True).order_by().distinct()
        }
    validated_locations = set()
    modify_rge_locations = set()
    if current_rge and all_expected:
        validated_locations = {
            _normalize(value)
            for value in ValidacionUbicacion.objects.filter(
                carga_rge=current_rge,
                ubicacion__in=all_expected,
                validada=True,
            ).values_list("ubicacion", flat=True)
        } - counted_locations
        modify_rge_locations = {
            _normalize(value)
            for value in ValidacionUbicacion.objects.filter(
                carga_rge=current_rge,
                ubicacion__in=all_expected,
                modificar_rge=True,
            ).values_list("ubicacion", flat=True)
        }
    all_completed = all_expected.intersection(counted_locations | validated_locations)

    warehouse_cards = []
    for warehouse in dict.fromkeys(key[0] for key in LOCATION_CONFIGS):
        type_cards = []
        warehouse_expected = set()
        for location_type in (key[1] for key in LOCATION_CONFIGS if key[0] == warehouse):
            locations = set(expected_by_config[(warehouse, location_type)])
            warehouse_expected.update(locations)
            type_cards.append({
                "name": location_type.title(),
                "value": location_type,
                **_progress_summary(locations, counted_locations, validated_locations),
                "url": "?" + urlencode({"bodega": warehouse, "tipo": location_type}),
            })
        warehouse_cards.append({
            "name": warehouse.title(),
            "value": warehouse,
            "types": type_cards,
            **_progress_summary(warehouse_expected, counted_locations, validated_locations),
        })

    requested_key = (_normalize(selected_warehouse), _normalize(selected_type))
    key = requested_key if requested_key in LOCATION_CONFIGS else ("BODEGA CENTRAL", "PRIMARIO")
    warehouse, location_type = key
    config = LOCATION_CONFIGS[key]
    expected = expected_by_config[key]
    counted = set(expected).intersection(counted_locations)
    validated = set(expected).intersection(validated_locations)
    completed = counted | validated

    scope_key = config["scope_key"]
    scopes = []
    for name in sorted({item[scope_key] for item in expected.values()}):
        locations = {loc for loc, dims in expected.items() if dims[scope_key] == name}
        scopes.append({
            "name": name,
            **_progress_summary(locations, counted, validated),
            "url": "?" + urlencode({"bodega": warehouse, "tipo": location_type, "piso": name}),
        })
    available_scopes = [item["name"] for item in scopes]
    selected_scope = _normalize(selected_floor)
    if selected_scope not in available_scopes:
        selected_scope = ""
    scoped_expected = {
        location: dims for location, dims in expected.items()
        if not selected_scope or dims[scope_key] == selected_scope
    }
    progress_tree = []
    if selected_scope:
        reconciliation = _build_reconciliation_data(
            set(scoped_expected),
            current_load,
            current_rge,
            counted,
            validated,
            modify_rge_locations,
        )
        progress_tree = _build_tree(scoped_expected, counted, validated, reconciliation, config)

    group_labels = [label for _, label in config["groups"]]
    pending_rows = []
    if selected_scope:
        for location, dims in sorted(scoped_expected.items()):
            if location not in completed:
                values = [selected_scope]
                values.extend(dims[group_key] for group_key, _ in config["groups"])
                if config["leaf_key"]:
                    values.append(dims[config["leaf_key"]])
                values.append(location)
                pending_rows.append(tuple(values))

    selected_query = urlencode({"bodega": warehouse, "tipo": location_type})
    refresh_params = {"bodega": warehouse, "tipo": location_type}
    if selected_scope:
        refresh_params["piso"] = selected_scope
    return {
        "current_load": current_load,
        "current_rge": current_rge,
        "source_label": "Conteo local (desarrollo)",
        "expected_total": len(expected),
        "counted_total": len(counted),
        "validated_total": len(validated),
        "completed_total": len(completed),
        "pending_total": len(expected) - len(completed),
        "percentage": _percentage(len(completed), len(expected)),
        "global_expected_total": len(all_expected),
        "global_counted_total": len(all_expected.intersection(counted_locations)),
        "global_validated_total": len(all_expected.intersection(validated_locations)),
        "global_completed_total": len(all_completed),
        "global_pending_total": len(all_expected) - len(all_completed),
        "global_percentage": _percentage(len(all_completed), len(all_expected)),
        "map_only_total": len(map_locations - rge_locations) if current_rge else 0,
        "rge_only_total": len(rge_locations - map_locations),
        "warehouse_cards": warehouse_cards,
        "selected_warehouse": warehouse,
        "selected_type": location_type,
        "selected_query": selected_query,
        "refresh_query": urlencode(refresh_params),
        "format_help": config["format_help"],
        "invalid_total": invalid_by_config[key],
        "scope_label": config["scope_label"],
        "scopes": scopes,
        "floors": scopes,
        "available_floors": available_scopes,
        "selected_scope": selected_scope,
        "selected_floor": selected_scope,
        "group_labels": group_labels,
        "leaf_label": config["leaf_label"],
        "progress_tree": progress_tree,
        "download_headers": (
            (config["scope_label"], *group_labels, config["leaf_label"], "Ubicación")
            if config["leaf_key"]
            else (config["scope_label"], *group_labels, "Ubicación")
        ),
        "pending_rows": pending_rows,
    }
