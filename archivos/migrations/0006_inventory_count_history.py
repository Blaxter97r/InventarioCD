from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("archivos", "0005_inventory_count_totals")]

    operations = [
        migrations.RemoveField(
            model_name="cargaconteoinventario",
            name="registro_unico",
        ),
    ]
