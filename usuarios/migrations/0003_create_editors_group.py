from django.db import migrations


def create_editors_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Editores")


def remove_editors_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Editores").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0002_create_work_groups"),
    ]

    operations = [
        migrations.RunPython(create_editors_group, remove_editors_group),
    ]
