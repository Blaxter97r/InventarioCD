import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("archivos", "0002_ubicacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CargaDiferencias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archivo_nombre", models.CharField(max_length=255, verbose_name="archivo")),
                ("total_registros", models.PositiveIntegerField(default=0, verbose_name="registros")),
                ("fecha_carga", models.DateTimeField(auto_now_add=True, verbose_name="fecha de carga")),
                ("cargado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cargas_diferencias", to=settings.AUTH_USER_MODEL, verbose_name="cargado por")),
                ("linea", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cargas_diferencias", to="archivos.linea", verbose_name="línea")),
            ],
            options={
                "verbose_name": "carga de diferencias",
                "verbose_name_plural": "cargas de diferencias",
                "ordering": ("-fecha_carga",),
            },
        ),
        migrations.CreateModel(
            name="Diferencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sublinea", models.CharField(max_length=50, verbose_name="sublínea")),
                ("codigo", models.CharField(max_length=100, verbose_name="código")),
                ("ultimo_conteo", models.DecimalField(decimal_places=4, max_digits=18, verbose_name="último conteo")),
                ("existencia", models.DecimalField(decimal_places=4, max_digits=18, verbose_name="existencia")),
                ("diferencia", models.DecimalField(decimal_places=4, max_digits=18, verbose_name="diferencia")),
                ("ubicacion_1", models.CharField(blank=True, max_length=100, verbose_name="ubicación 1")),
                ("ubicacion_2", models.CharField(blank=True, max_length=100, verbose_name="ubicación 2")),
                ("ubicacion_3", models.CharField(blank=True, max_length=100, verbose_name="ubicación 3")),
                ("ubicacion_4", models.CharField(blank=True, max_length=100, verbose_name="ubicación 4")),
                ("fecha_generacion", models.DateField(verbose_name="fecha de generación")),
                ("hora_generacion", models.TimeField(verbose_name="hora de generación")),
                ("carga", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="diferencias", to="conteo.cargadiferencias", verbose_name="carga")),
            ],
            options={
                "verbose_name": "diferencia",
                "verbose_name_plural": "diferencias",
                "ordering": ("sublinea", "codigo"),
            },
        ),
        migrations.AddIndex(
            model_name="diferencia",
            index=models.Index(fields=["codigo"], name="conteo_dif_codigo_idx"),
        ),
        migrations.AddIndex(
            model_name="diferencia",
            index=models.Index(fields=["sublinea"], name="conteo_dif_sublinea_idx"),
        ),
    ]
