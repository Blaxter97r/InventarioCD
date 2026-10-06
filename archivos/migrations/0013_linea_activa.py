from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("archivos", "0012_cargaconteobe_detalleconteobe"),
    ]

    operations = [
        migrations.AddField(
            model_name="linea",
            name="activa",
            field=models.BooleanField(default=True, verbose_name="activa"),
        ),
    ]
