from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conteo", "0004_finalize_line"),
    ]

    operations = [
        migrations.AddField(
            model_name="diferencia",
            name="descripcion",
            field=models.CharField(blank=True, max_length=255, verbose_name="descripción"),
        ),
        migrations.AddField(
            model_name="diferencia",
            name="item",
            field=models.CharField(blank=True, max_length=100, verbose_name="item"),
        ),
    ]
