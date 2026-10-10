from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archivos", "0013_linea_activa"),
    ]

    operations = [
        migrations.AddField(
            model_name="ajustecantidadconteoinventario",
            name="bodega_anterior",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="ajustecantidadconteoinventario",
            name="bodega_nueva",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="ajustecantidadconteoinventario",
            name="ubicacion_anterior",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="ajustecantidadconteoinventario",
            name="ubicacion_nueva",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
