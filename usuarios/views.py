from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ManagedUserCreateForm, ManagedUserUpdateForm


def _is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Admin").exists()
    )


def _require_admin(request):
    if not _is_admin(request.user):
        raise PermissionDenied


def login_view(request):
    """Muestra el formulario e inicia sesión con usuario o correo."""
    if request.user.is_authenticated:
        return redirect("usuarios:inicio")

    next_url = request.GET.get("next") or request.POST.get("next", "")
    context = {"next": next_url}

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        context["entered_username"] = identifier

        username = identifier
        if "@" in identifier:
            matched_user = get_user_model().objects.filter(email__iexact=identifier).first()
            if matched_user:
                username = matched_user.get_username()

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            request.session.set_expiry(1209600 if request.POST.get("remember") else 0)

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("usuarios:inicio")

        context["form_error"] = "El usuario o la contraseña no son correctos."

    return render(request, "usuarios/login.html", context)


@login_required
def inicio_view(request):
    """Página protegida posterior al ingreso."""
    return render(request, "usuarios/inicio.html", {"can_manage_users": _is_admin(request.user)})


@login_required
def user_list_view(request):
    _require_admin(request)
    users = get_user_model().objects.prefetch_related("groups").order_by("first_name", "username")
    return render(request, "usuarios/user_list.html", {"users": users})


@login_required
def user_create_view(request):
    _require_admin(request)
    form = ManagedUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"El usuario {user.username} fue creado correctamente.")
        return redirect("usuarios:user_list")
    if request.method == "POST":
        messages.error(
            request,
            "No se guardó el usuario. Revisa los campos marcados y vuelve a intentarlo.",
        )
    return render(request, "usuarios/user_form.html", {"form": form, "title": "Crear usuario"})


@login_required
def user_update_view(request, pk):
    _require_admin(request)
    user = get_object_or_404(get_user_model(), pk=pk)
    if user.groups.filter(name="Admin").exists() or user.is_superuser:
        messages.error(request, "La cuenta administradora no puede modificarse desde este formulario.")
        return redirect("usuarios:user_list")

    form = ManagedUserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        updated_user = form.save()
        messages.success(request, f"El usuario {updated_user.username} fue actualizado.")
        return redirect("usuarios:user_list")
    if request.method == "POST":
        messages.error(
            request,
            "No se guardaron los cambios. Revisa los campos marcados.",
        )
    return render(
        request,
        "usuarios/user_form.html",
        {"form": form, "title": "Editar usuario", "managed_user": user},
    )


@login_required
def user_delete_view(request, pk):
    _require_admin(request)
    user = get_object_or_404(get_user_model(), pk=pk)
    if user == request.user or user.groups.filter(name="Admin").exists() or user.is_superuser:
        messages.error(request, "La cuenta administradora no puede eliminarse.")
        return redirect("usuarios:user_list")

    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"El usuario {username} fue eliminado.")
        return redirect("usuarios:user_list")
    return render(request, "usuarios/user_confirm_delete.html", {"managed_user": user})


def logout_view(request):
    """Cierra la sesión por medio de una petición POST."""
    if request.method == "POST":
        logout(request)
        messages.success(request, "Tu sesión se cerró correctamente.")
    return redirect("login")


def password_reset_view(request):
    """Informa el canal de recuperación mientras se configura el correo."""
    messages.info(request, "Solicita al administrador el restablecimiento de tu contraseña.")
    return redirect("login")
