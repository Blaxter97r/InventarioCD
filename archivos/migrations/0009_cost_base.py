from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0008_rename_ubicacion_final_rge"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CargaBaseCosto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("registro_unico", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ("archivo_nombre", models.CharField(max_length=255, verbose_name="archivo")),
                ("total_registros", models.PositiveIntegerField(default=0, verbose_name="registros")),
                ("fecha_carga", models.DateTimeField(auto_now_add=True, verbose_name="fecha de carga")),
                ("cargado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cargas_base_costo", to=settings.AUTH_USER_MODEL, verbose_name="cargado por")),
            ],
            options={
                "verbose_name": "carga de base de costo",
                "verbose_name_plural": "cargas de base de costo",
                "ordering": ("-fecha_carga", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="CostoProducto",
            fields=[
                ("codigo", models.CharField(max_length=100, primary_key=True, serialize=False, verbose_name="código")),
                ("costo", models.DecimalField(decimal_places=4, max_digits=18, verbose_name="costo MCOSUC")),
                ("carga", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="costos", to="archivos.cargabasecosto", verbose_name="carga")),
            ],
            options={
                "verbose_name": "costo de producto",
                "verbose_name_plural": "costos de productos",
                "ordering": ("codigo",),
            },
        ),
    ]
