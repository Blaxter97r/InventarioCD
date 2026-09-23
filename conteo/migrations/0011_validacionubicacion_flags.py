from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conteo", "0010_validacionubicacion"),
    ]

    operations = [
        migrations.AddField(
            model_name="validacionubicacion",
            name="validada",
            field=models.BooleanField(default=True, verbose_name="ubicación validada"),
        ),
        migrations.AddField(
            model_name="validacionubicacion",
            name="modificar_rge",
            field=models.BooleanField(default=False, verbose_name="requiere modificar RGE"),
        ),
    ]
