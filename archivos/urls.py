from django.urls import path

from . import views


app_name = "archivos"

urlpatterns = [
    path("", views.index_view, name="index"),
    path("cargar/", views.upload_view, name="upload"),
    path("plantilla/", views.template_view, name="template"),
    path("ubicaciones/", views.location_index_view, name="location_index"),
    path("ubicaciones/cargar/", views.location_upload_view, name="location_upload"),
    path("ubicaciones/plantilla/", views.location_template_view, name="location_template"),
    path("conteo-inventario/", views.inventory_count_index_view, name="inventory_count_index"),
    path("conteo-inventario/detalle/<int:pk>/cantidad/", views.inventory_count_quantity_view, name="inventory_count_quantity"),
    path("conteo-inventario/ubicacion/agregar/", views.inventory_count_location_view, name="inventory_count_location"),
    path("conteo-inventario/cantidades/guardar/", views.inventory_count_bulk_quantity_view, name="inventory_count_bulk_quantity"),
    path("conteo-inventario/cargar/", views.inventory_count_upload_view, name="inventory_count_upload"),
    path("conteo-inventario/<int:pk>/eliminar/", views.inventory_count_delete_view, name="inventory_count_delete"),
    path("conteo-inventario/plantilla/", views.inventory_count_template_view, name="inventory_count_template"),
    path("conteo-be/", views.be_count_index_view, name="be_count_index"),
    path("conteo-be/cargar/", views.be_count_upload_view, name="be_count_upload"),
    path("conteo-be/plantilla/", views.be_count_template_view, name="be_count_template"),
    path("rge/", views.rge_index_view, name="rge_index"),
    path("rge/cargar/", views.rge_upload_view, name="rge_upload"),
    path("rge/plantilla/", views.rge_template_view, name="rge_template"),
    path("base-costo/", views.cost_base_index_view, name="cost_base_index"),
    path("base-costo/cargar/", views.cost_base_upload_view, name="cost_base_upload"),
    path("base-costo/plantilla/", views.cost_base_template_view, name="cost_base_template"),
]
