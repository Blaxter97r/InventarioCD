from django.urls import path

from . import views


app_name = "conteo"

urlpatterns = [
    path("diferencias/", views.differences_index_view, name="differences_index"),
    path("diferencias/reiniciar/", views.reset_differences_view, name="reset_differences"),
    path("diferencias/cargar/", views.differences_upload_view, name="differences_upload"),
    path("diferencias/plantilla/", views.differences_template_view, name="differences_template"),
    path("diferencias/pendientes/", views.pending_queue_view, name="pending_queue"),
    path("diferencias/pendientes/<int:pk>/codigos/", views.pending_codes_view, name="pending_codes"),
    path("diferencias/pendientes/<int:pk>/seleccionar/", views.select_recount_codes_view, name="select_recount_codes"),
    path("diferencias/pendientes/<int:pk>/finalizar/", views.finalize_line_view, name="finalize_line"),
    path("diferencias/pendientes/<int:pk>/eliminar/", views.delete_pending_recount_view, name="delete_pending_recount"),
    path("diferencias/reconteo/<int:pk>/descargar/", views.download_recount_view, name="download_recount"),
    path("diferencias/reconteo/<int:pk>/as400/descargar/", views.download_recount_as400_view, name="download_recount_as400"),
    path("reconteos/", views.recounts_view, name="recounts"),
    path("reconteos/<int:pk>/as400/adjuntar/", views.replace_recount_as400_view, name="replace_recount_as400"),
    path(
        "reconteos/<int:pk>/bodega/<str:warehouse>/iniciar/",
        views.start_recount_warehouse_view,
        name="start_recount_warehouse",
    ),
    path(
        "reconteos/<int:pk>/bodega/<str:warehouse>/finalizar/",
        views.finish_recount_warehouse_view,
        name="finish_recount_warehouse",
    ),
    path(
        "reconteos/<int:pk>/bodega/<str:warehouse>/imprimir/",
        views.recount_warehouse_report_view,
        name="recount_warehouse_report",
    ),
    path("resumen-por-linea/", views.line_summary_view, name="line_summary"),
    path("avance/general/", views.progress_general_view, name="progress_general"),
    path("avance/", views.progress_view, name="progress"),
    path("avance/validar-ubicacion/", views.validate_progress_location_view, name="validate_progress_location"),
    path("avance/secundario/diferencias-cantidad.pdf", views.secondary_quantity_differences_pdf_view, name="secondary_quantity_differences_pdf"),
    path("avance/secundario/modificaciones-rge.xlsx", views.rge_modifications_download_view, name="rge_modifications_download"),
    path("avance/<str:floor>/ubicaciones-pendientes/", views.pending_locations_download_view, name="pending_locations_download"),
    path("diferencias/seleccionados/", views.selected_codes_view, name="selected_codes"),
]
