from django.core.exceptions import PermissionDenied


EDITOR_ALLOWED_VIEWS = {
    "login",
    "usuarios:logout",
    "usuarios:password_reset",
    "archivos:inventory_count_index",
    "archivos:inventory_count_quantity",
    "archivos:inventory_count_bulk_quantity",
}


class EditorAccessMiddleware:
    """Limita a los Editores al conteo vigente y sus acciones de edición."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if not user.is_authenticated or user.is_superuser:
            return None
        if user.groups.filter(name="Admin").exists():
            return None
        if (
            user.groups.filter(name="Editores").exists()
            and request.resolver_match.view_name not in EDITOR_ALLOWED_VIEWS
        ):
            raise PermissionDenied
        return None
