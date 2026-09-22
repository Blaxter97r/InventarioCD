def navigation_permissions(request):
    user = request.user
    can_administer = user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Admin").exists()
    )
    is_editor = user.is_authenticated and user.groups.filter(name="Editores").exists()
    can_validate_differences = user.is_authenticated and (
        can_administer or user.groups.filter(name="Gerente").exists()
    )
    can_upload_differences = user.is_authenticated and (
        can_administer or user.groups.filter(name="Supervisores").exists()
    )
    pending_recounts = 0
    selected_recount_lines = 0
    if can_validate_differences:
        from conteo.models import CargaDiferencias

        pending_recounts = CargaDiferencias.objects.filter(
            estado=CargaDiferencias.Estado.PENDIENTE
        ).count()
    if user.is_authenticated:
        from django.db.models import OuterRef, Subquery
        from conteo.models import CargaDiferencias

        latest_load_id = CargaDiferencias.objects.filter(
            linea_id=OuterRef("linea_id")
        ).order_by("-fecha_carga", "-pk").values("pk")[:1]
        selected_recount_lines = CargaDiferencias.objects.filter(
            pk=Subquery(latest_load_id),
            estado=CargaDiferencias.Estado.RECONTEO,
            fecha_finalizacion__isnull=True,
        ).count()
    return {
        "can_administer": can_administer,
        "is_editor": is_editor,
        "can_upload_differences": can_upload_differences,
        "can_validate_differences": can_validate_differences,
        "pending_recounts": pending_recounts,
        "selected_recount_lines": selected_recount_lines,
    }
