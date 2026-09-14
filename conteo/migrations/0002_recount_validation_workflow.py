import conteo.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def number_existing_recounts(apps, schema_editor):
    Load = apps.get_model("conteo", "CargaDiferencias")
    line_ids = Load.objects.values_list("linea_id", flat=True).distinct()
    for line_id in line_ids:
        for number, load in enumerate(
            Load.objects.filter(linea_id=line_id).order_by("fecha_carga", "pk"),
            start=1,
        ):
            load.numero_reconteo = number
            load.estado = "VALIDADO"
            load.save(update_fields=("numero_reconteo", "estado"))


class Migration(migrations.Migration):
    dependencies = [
        ("conteo", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="cargadiferencias",
            name="archivo_original",
            field=models.FileField(blank=True, max_length=500, upload_to=conteo.models.difference_file_path, verbose_name="archivo original"),
        ),
        migrations.AddField(
            model_name="cargadiferencias",
            name="estado",
            field=models.CharField(choices=[("PENDIENTE", "Pendiente"), ("VALIDADO", "Validado")], default="PENDIENTE", max_length=12, verbose_name="estado"),
        ),
        migrations.AddField(
            model_name="cargadiferencias",
            name="fecha_validacion",
            field=models.DateTimeField(blank=True, null=True, verbose_name="fecha de validación"),
        ),
        migrations.AddField(
            model_name="cargadiferencias",
            name="numero_reconteo",
            field=models.PositiveIntegerField(default=1, verbose_name="número de reconteo"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="cargadiferencias",
            name="validado_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reconteos_validados", to=settings.AUTH_USER_MODEL, verbose_name="validado por"),
        ),
        migrations.AddField(
            model_name="diferencia",
            name="seleccionada",
            field=models.BooleanField(default=False, verbose_name="seleccionada por gerente"),
        ),
        migrations.RunPython(number_existing_recounts, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="cargadiferencias",
            constraint=models.UniqueConstraint(fields=("linea", "numero_reconteo"), name="conteo_reconteo_numero_unico_linea"),
        ),
        migrations.AddConstraint(
            model_name="cargadiferencias",
            constraint=models.UniqueConstraint(condition=models.Q(("estado", "PENDIENTE")), fields=("linea",), name="conteo_un_pendiente_por_linea"),
        ),
    ]
