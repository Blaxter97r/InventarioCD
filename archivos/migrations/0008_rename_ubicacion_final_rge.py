from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("archivos", "0007_rge")]

    operations = [
        migrations.RemoveConstraint(
            model_name="detallerge",
            name="arch_rge_carga_codigo_ubic_unico",
        ),
        migrations.RemoveIndex(
            model_name="detallerge",
            name="arch_rge_ubic_idx",
        ),
        migrations.RenameField(
            model_name="detallerge",
            old_name="ubicacion_final",
            new_name="ubicacion",
        ),
        migrations.AlterModelOptions(
            name="detallerge",
            options={
                "ordering": ("ubicacion", "codigo", "pk"),
                "verbose_name": "detalle RGE",
                "verbose_name_plural": "detalles RGE",
            },
        ),
        migrations.AlterField(
            model_name="detallerge",
            name="ubicacion",
            field=models.CharField(max_length=100, verbose_name="ubicación"),
        ),
        migrations.AddIndex(
            model_name="detallerge",
            index=models.Index(fields=["ubicacion"], name="arch_rge_ubic_idx"),
        ),
        migrations.AddConstraint(
            model_name="detallerge",
            constraint=models.UniqueConstraint(
                fields=("carga", "codigo", "ubicacion"),
                name="arch_rge_carga_codigo_ubic_unico",
            ),
        ),
    ]
