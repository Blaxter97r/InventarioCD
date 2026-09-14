from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("archivos", "0009_cost_base"),
    ]

    operations = [
        migrations.AddField(
            model_name="detallerge",
            name="cantidad",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=18,
                null=True,
                verbose_name="cantidad",
            ),
        ),
    ]
