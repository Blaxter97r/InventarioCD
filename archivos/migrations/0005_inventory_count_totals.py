from django.db import migrations, models


def populate_inventory_count_totals(apps, schema_editor):
    Load = apps.get_model("archivos", "CargaConteoInventario")
    for load in Load.objects.all():
        load.total_codigos = load.detalles.values("codigo").distinct().count()
        load.total_bodegas = load.detalles.values("bodega").distinct().count()
        load.save(update_fields=("total_codigos", "total_bodegas"))


class Migration(migrations.Migration):
    dependencies = [("archivos", "0004_single_inventory_count")]

    operations = [
        migrations.AddField(
            model_name="cargaconteoinventario",
            name="total_codigos",
            field=models.PositiveIntegerField(default=0, verbose_name="códigos distintos"),
        ),
        migrations.AddField(
            model_name="cargaconteoinventario",
            name="total_bodegas",
            field=models.PositiveIntegerField(default=0, verbose_name="bodegas"),
        ),
        migrations.RunPython(populate_inventory_count_totals, migrations.RunPython.noop),
    ]
