from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0006_inventory_count_history"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CargaRGE",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("registro_unico", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ("archivo_nombre", models.CharField(max_length=255, verbose_name="archivo")),
                ("total_registros", models.PositiveIntegerField(default=0, verbose_name="registros")),
                ("total_codigos", models.PositiveIntegerField(default=0, verbose_name="códigos distintos")),
                ("total_ubicaciones", models.PositiveIntegerField(default=0, verbose_name="ubicaciones distintas")),
                ("fecha_carga", models.DateTimeField(auto_now_add=True, verbose_name="fecha de carga")),
                ("cargado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cargas_rge", to=settings.AUTH_USER_MODEL, verbose_name="cargado por")),
            ],
            options={
                "verbose_name": "carga RGE",
                "verbose_name_plural": "cargas RGE",
                "ordering": ("-fecha_carga", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="DetalleRGE",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=100, verbose_name="código")),
                ("ubicacion_final", models.CharField(max_length=100, verbose_name="ubicación final")),
                ("carga", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="archivos.cargarge", verbose_name="carga")),
            ],
            options={
                "verbose_name": "detalle RGE",
                "verbose_name_plural": "detalles RGE",
                "ordering": ("ubicacion_final", "codigo", "pk"),
                "indexes": [models.Index(fields=["codigo"], name="arch_rge_codigo_idx"), models.Index(fields=["ubicacion_final"], name="arch_rge_ubic_idx")],
                "constraints": [models.UniqueConstraint(fields=("carga", "codigo", "ubicacion_final"), name="arch_rge_carga_codigo_ubic_unico")],
            },
        ),
    ]
