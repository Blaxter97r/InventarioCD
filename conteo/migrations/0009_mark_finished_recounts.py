from collections import defaultdict

from django.db import migrations


def mark_finished_recounts(apps, schema_editor):
    Load = apps.get_model("conteo", "CargaDiferencias")
    Difference = apps.get_model("conteo", "Diferencia")
    WarehouseStart = apps.get_model("conteo", "InicioReconteoBodega")
    loads = list(Load.objects.filter(estado="RECONTEO", fecha_finalizacion__isnull=True))
    if not loads:
        return

    selected_by_load = defaultdict(list)
    load_ids = [load.pk for load in loads]
    for item in Difference.objects.filter(
        carga_id__in=load_ids, seleccionada=True
    ).only("carga_id", "codigo"):
        selected_by_load[item.carga_id].append(item)
    for load in loads:
        load.codigos_reconteo = selected_by_load[load.pk]

    # Usa la misma asignación de bodegas que la vista de reconteos.
    from conteo.recount_reports import attach_warehouse_options

    attach_warehouse_options(loads)
    finished_by_load = defaultdict(dict)
    for start in WarehouseStart.objects.filter(carga_id__in=load_ids, fecha_fin__isnull=False):
        finished_by_load[start.carga_id][start.bodega] = start

    for load in loads:
        assigned = [option["key"] for option in load.warehouse_options if option["count"]]
        finished = finished_by_load[load.pk]
        if assigned and not load.unclassified_codes and all(key in finished for key in assigned):
            last = max((finished[key] for key in assigned), key=lambda item: item.fecha_fin)
            Load.objects.filter(pk=load.pk).update(
                fecha_finalizacion=last.fecha_fin,
                finalizado_por_id=last.finalizado_por_id,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0012_cargaconteobe_detalleconteobe"),
        ("conteo", "0008_inicioreconteobodega_fecha_fin_and_more"),
    ]

    operations = [
        migrations.RunPython(mark_finished_recounts, migrations.RunPython.noop),
    ]
