from django.db import migrations, models


def keep_latest_inventory_count(apps, schema_editor):
    Load = apps.get_model("archivos", "CargaConteoInventario")
    latest = Load.objects.order_by("-fecha_carga", "-pk").first()
    if latest is None:
        return
    Load.objects.exclude(pk=latest.pk).delete()
    latest.registro_unico = 1
    latest.save(update_fields=("registro_unico",))


class Migration(migrations.Migration):
    dependencies = [("archivos", "0003_inventory_count")]

    operations = [
        migrations.AddField(
            model_name="cargaconteoinventario",
            name="registro_unico",
            field=models.PositiveSmallIntegerField(editable=False, null=True),
        ),
        migrations.RunPython(keep_latest_inventory_count, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="cargaconteoinventario",
            name="registro_unico",
            field=models.PositiveSmallIntegerField(default=1, editable=False, unique=True),
        ),
    ]
