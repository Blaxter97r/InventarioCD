from django.contrib import admin

from .models import CargaDiferencias, Diferencia, ValidacionUbicacion


@admin.register(CargaDiferencias)
class CargaDiferenciasAdmin(admin.ModelAdmin):
    list_display = ("id", "linea", "numero_reconteo", "estado", "archivo_nombre", "total_registros", "cargado_por", "fecha_carga")
    list_filter = ("estado", "linea", "fecha_carga")
    search_fields = ("archivo_nombre", "linea__nlinea", "linea__descripcion")


@admin.register(Diferencia)
class DiferenciaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "sublinea", "ultimo_conteo", "existencia", "diferencia", "fecha_generacion")
    list_filter = ("carga__linea", "fecha_generacion")
    search_fields = ("codigo", "sublinea", "ubicacion_1", "ubicacion_2")


@admin.register(ValidacionUbicacion)
class ValidacionUbicacionAdmin(admin.ModelAdmin):
    list_display = (
        "ubicacion", "validada", "modificar_rge", "carga_rge",
        "validada_por", "fecha_validacion",
    )
    list_filter = ("validada", "modificar_rge", "fecha_validacion")
    search_fields = ("ubicacion", "validada_por__username")
