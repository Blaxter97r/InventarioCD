from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "usuarios"

urlpatterns = [
    path("", views.inicio_view, name="inicio"),
    path("ingresar/", RedirectView.as_view(pattern_name="login", permanent=False), name="login_legacy"),
    path("salir/", views.logout_view, name="logout"),
    path("recuperar-contrasena/", views.password_reset_view, name="password_reset"),
    path("administrar/", views.user_list_view, name="user_list"),
    path("administrar/nuevo/", views.user_create_view, name="user_create"),
    path("administrar/<int:pk>/editar/", views.user_update_view, name="user_update"),
    path("administrar/<int:pk>/eliminar/", views.user_delete_view, name="user_delete"),
]
