from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ubicacion",
            fields=[
                ("ubicacion", models.CharField(max_length=50, primary_key=True, serialize=False, verbose_name="Ubicación")),
                ("bodega", models.CharField(max_length=100, verbose_name="Bodega")),
                ("sector", models.CharField(max_length=100, verbose_name="Sector")),
                ("tipo", models.CharField(max_length=100, verbose_name="Tipo")),
            ],
            options={
                "verbose_name": "ubicación",
                "verbose_name_plural": "ubicaciones",
                "ordering": ("bodega", "sector", "ubicacion"),
            },
        ),
    ]
