from django.contrib import admin

from .models import (
    CargaBaseCosto,
    CargaConteoInventario,
    CargaRGE,
    CostoProducto,
    DetalleConteoInventario,
    DetalleRGE,
    Linea,
    Sublinea,
    Ubicacion,
)


@admin.register(Linea)
class LineaAdmin(admin.ModelAdmin):
    list_display = ("id_linea", "nlinea", "descripcion")
    search_fields = ("id_linea", "nlinea", "descripcion")


@admin.register(Sublinea)
class SublineaAdmin(admin.ModelAdmin):
    list_display = ("id_sublinea", "linea", "numero", "descripcion")
    list_filter = ("linea",)
    search_fields = ("id_sublinea", "numero", "descripcion", "linea__nlinea")


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("ubicacion", "bodega", "sector", "tipo")
    list_filter = ("bodega", "sector", "tipo")
    search_fields = ("ubicacion", "bodega", "sector", "tipo")


@admin.register(CargaConteoInventario)
class CargaConteoInventarioAdmin(admin.ModelAdmin):
    list_display = ("archivo_nombre", "total_registros", "cargado_por", "fecha_carga")
    search_fields = ("archivo_nombre", "cargado_por__username")


@admin.register(DetalleConteoInventario)
class DetalleConteoInventarioAdmin(admin.ModelAdmin):
    list_display = ("bodega", "ubicacion", "codigo", "cantidad", "carga")
    list_filter = ("bodega",)
    search_fields = ("bodega", "ubicacion", "codigo")


@admin.register(CargaRGE)
class CargaRGEAdmin(admin.ModelAdmin):
    list_display = ("archivo_nombre", "total_registros", "total_codigos", "total_ubicaciones", "cargado_por", "fecha_carga")


@admin.register(DetalleRGE)
class DetalleRGEAdmin(admin.ModelAdmin):
    list_display = ("codigo", "ubicacion", "cantidad", "carga")
    search_fields = ("codigo", "ubicacion")


@admin.register(CargaBaseCosto)
class CargaBaseCostoAdmin(admin.ModelAdmin):
    list_display = ("archivo_nombre", "total_registros", "cargado_por", "fecha_carga")


@admin.register(CostoProducto)
class CostoProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "costo", "carga")
    search_fields = ("codigo",)
