from django.db import migrations
from django.db.models import F


def recalculate_differences(apps, schema_editor):
    Diferencia = apps.get_model("conteo", "Diferencia")
    Diferencia.objects.update(
        diferencia=F("ultimo_conteo") - F("existencia")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("conteo", "0012_add_pedregal_recount_warehouse"),
    ]

    operations = [
        migrations.RunPython(recalculate_differences, migrations.RunPython.noop),
    ]
