import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Linea",
            fields=[
                ("id_linea", models.CharField(max_length=30, primary_key=True, serialize=False, verbose_name="ID de línea")),
                ("nlinea", models.CharField(max_length=30, verbose_name="Número de línea")),
                ("descripcion", models.CharField(max_length=255, verbose_name="Descripción")),
            ],
            options={
                "verbose_name": "línea",
                "verbose_name_plural": "líneas",
                "ordering": ("nlinea", "id_linea"),
            },
        ),
        migrations.CreateModel(
            name="Sublinea",
            fields=[
                ("id_sublinea", models.CharField(max_length=30, primary_key=True, serialize=False, verbose_name="ID de sublínea")),
                ("numero", models.CharField(max_length=30, verbose_name="Número de sublínea")),
                ("descripcion", models.CharField(max_length=255, verbose_name="Descripción")),
                ("linea", models.ForeignKey(db_column="id_linea", on_delete=django.db.models.deletion.PROTECT, related_name="sublineas", to="archivos.linea", verbose_name="línea")),
            ],
            options={
                "verbose_name": "sublínea",
                "verbose_name_plural": "sublíneas",
                "ordering": ("linea_id", "numero", "id_sublinea"),
            },
        ),
        migrations.AddConstraint(
            model_name="sublinea",
            constraint=models.UniqueConstraint(fields=("linea", "numero"), name="archivos_sublinea_linea_numero_unico"),
        ),
    ]
