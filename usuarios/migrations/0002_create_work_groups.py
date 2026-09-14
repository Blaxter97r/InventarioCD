from django.db import migrations


def create_work_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model("usuarios", "User")

    admin_group, _ = Group.objects.get_or_create(name="Admin")
    Group.objects.get_or_create(name="Supervisores")
    Group.objects.get_or_create(name="Gerente")

    user_content_type, _ = ContentType.objects.get_or_create(
        app_label="usuarios",
        model="user",
    )
    permissions = []
    for action in ("add", "change", "delete", "view"):
        permission, _ = Permission.objects.get_or_create(
            content_type=user_content_type,
            codename=f"{action}_user",
            defaults={"name": f"Can {action} user"},
        )
        permissions.append(permission)
    admin_group.permissions.set(permissions)

    owner = User.objects.filter(username="noel.rivera").first()
    if owner:
        owner.groups.add(admin_group)


def remove_work_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=("Admin", "Supervisores", "Gerente")).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_work_groups, remove_work_groups),
    ]
