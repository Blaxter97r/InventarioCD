import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conteo", "0003_recount_selection_state"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="cargadiferencias",
            name="fecha_finalizacion",
            field=models.DateTimeField(blank=True, null=True, verbose_name="fecha de finalización"),
        ),
        migrations.AddField(
            model_name="cargadiferencias",
            name="finalizado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_reconteo_finalizadas",
                to=settings.AUTH_USER_MODEL,
                verbose_name="finalizado por",
            ),
        ),
        migrations.AlterField(
            model_name="cargadiferencias",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("RECONTEO", "Pendiente de reconteo"),
                    ("FINALIZADO", "Finalizado"),
                ],
                default="PENDIENTE",
                max_length=12,
                verbose_name="estado",
            ),
        ),
    ]
