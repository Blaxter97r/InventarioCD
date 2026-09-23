from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0009_cost_base"),
        ("conteo", "0009_mark_finished_recounts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ValidacionUbicacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ubicacion", models.CharField(max_length=100, verbose_name="ubicación")),
                ("fecha_validacion", models.DateTimeField(auto_now_add=True, verbose_name="fecha de validación")),
                ("carga_rge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ubicaciones_validadas", to="archivos.cargarge", verbose_name="carga RGE")),
                ("validada_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ubicaciones_validadas", to=settings.AUTH_USER_MODEL, verbose_name="validada por")),
            ],
            options={
                "verbose_name": "validación de ubicación",
                "verbose_name_plural": "validaciones de ubicaciones",
                "ordering": ("ubicacion",),
            },
        ),
        migrations.AddConstraint(
            model_name="validacionubicacion",
            constraint=models.UniqueConstraint(fields=("carga_rge", "ubicacion"), name="conteo_validacion_unica_rge_ubicacion"),
        ),
        migrations.AddIndex(
            model_name="validacionubicacion",
            index=models.Index(fields=["carga_rge", "ubicacion"], name="conteo_val_rge_ubic_idx"),
        ),
    ]
