import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0002_ubicacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CargaConteoInventario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archivo_nombre", models.CharField(max_length=255, verbose_name="archivo")),
                ("total_registros", models.PositiveIntegerField(default=0, verbose_name="registros")),
                ("fecha_carga", models.DateTimeField(auto_now_add=True, verbose_name="fecha de carga")),
                ("cargado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cargas_conteo_inventario", to=settings.AUTH_USER_MODEL, verbose_name="cargado por")),
            ],
            options={
                "verbose_name": "carga de conteo de inventario",
                "verbose_name_plural": "cargas de conteo de inventario",
                "ordering": ("-fecha_carga", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="DetalleConteoInventario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bodega", models.CharField(max_length=100, verbose_name="bodega")),
                ("ubicacion", models.CharField(max_length=100, verbose_name="ubicación")),
                ("codigo", models.CharField(max_length=100, verbose_name="código")),
                ("cantidad", models.DecimalField(decimal_places=4, max_digits=18, verbose_name="cantidad")),
                ("carga", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="archivos.cargaconteoinventario", verbose_name="carga")),
            ],
            options={
                "verbose_name": "detalle de conteo de inventario",
                "verbose_name_plural": "detalles de conteo de inventario",
                "ordering": ("bodega", "ubicacion", "codigo", "pk"),
                "indexes": [
                    models.Index(fields=["codigo"], name="arch_conteo_codigo_idx"),
                    models.Index(fields=["ubicacion"], name="arch_conteo_ubic_idx"),
                    models.Index(fields=["carga", "codigo"], name="arch_carga_codigo_idx"),
                ],
            },
        ),
    ]
