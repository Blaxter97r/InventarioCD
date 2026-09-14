import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def move_validated_to_recount(apps, schema_editor):
    Load = apps.get_model("conteo", "CargaDiferencias")
    Load.objects.filter(estado="VALIDADO").update(estado="RECONTEO")


def move_recount_to_validated(apps, schema_editor):
    Load = apps.get_model("conteo", "CargaDiferencias")
    Load.objects.filter(estado="RECONTEO").update(estado="VALIDADO")


class Migration(migrations.Migration):
    dependencies = [
        ("conteo", "0002_recount_validation_workflow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name="cargadiferencias",
            old_name="validado_por",
            new_name="seleccionado_por",
        ),
        migrations.RenameField(
            model_name="cargadiferencias",
            old_name="fecha_validacion",
            new_name="fecha_seleccion",
        ),
        migrations.AlterField(
            model_name="cargadiferencias",
            name="fecha_seleccion",
            field=models.DateTimeField(blank=True, null=True, verbose_name="fecha de selección"),
        ),
        migrations.AlterField(
            model_name="cargadiferencias",
            name="seleccionado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reconteos_seleccionados",
                to=settings.AUTH_USER_MODEL,
                verbose_name="seleccionado por",
            ),
        ),
        migrations.RunPython(move_validated_to_recount, move_recount_to_validated),
        migrations.AlterField(
            model_name="cargadiferencias",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("RECONTEO", "Pendiente de reconteo"),
                ],
                default="PENDIENTE",
                max_length=12,
                verbose_name="estado",
            ),
        ),
    ]
