from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conteo", "0011_validacionubicacion_flags"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inicioreconteobodega",
            name="bodega",
            field=models.CharField(
                choices=[
                    ("central", "Bodega Central"),
                    ("ransa", "RANSA"),
                    ("pedregal", "Pedregal"),
                ],
                max_length=10,
            ),
        ),
    ]
