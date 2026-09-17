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
        from conteo.models import CargaDiferencias

        selected_recount_lines = (
            CargaDiferencias.objects.filter(estado=CargaDiferencias.Estado.RECONTEO)
            .exclude(
                linea_id__in=CargaDiferencias.objects.filter(
                    estado=CargaDiferencias.Estado.PENDIENTE
                ).values("linea_id")
            )
            .values("linea_id")
            .distinct()
            .count()
        )
    return {
        "can_administer": can_administer,
        "is_editor": is_editor,
        "can_upload_differences": can_upload_differences,
        "can_validate_differences": can_validate_differences,
        "pending_recounts": pending_recounts,
        "selected_recount_lines": selected_recount_lines,
    }
