from django.conf import settings
from django.db import models


class Linea(models.Model):
    id_linea = models.CharField("ID de línea", max_length=30, primary_key=True)
    nlinea = models.CharField("Número de línea", max_length=30)
    descripcion = models.CharField("Descripción", max_length=255)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        ordering = ("nlinea", "id_linea")
        verbose_name = "línea"
        verbose_name_plural = "líneas"

    def __str__(self):
        return f"{self.nlinea} - {self.descripcion}"


class Sublinea(models.Model):
    id_sublinea = models.CharField("ID de sublínea", max_length=30, primary_key=True)
    linea = models.ForeignKey(
        Linea,
        on_delete=models.PROTECT,
        related_name="sublineas",
        db_column="id_linea",
        verbose_name="línea",
    )
    numero = models.CharField("Número de sublínea", max_length=30)
    descripcion = models.CharField("Descripción", max_length=255)

    class Meta:
        ordering = ("linea_id", "numero", "id_sublinea")
        verbose_name = "sublínea"
        verbose_name_plural = "sublíneas"
        constraints = [
            models.UniqueConstraint(
                fields=("linea", "numero"),
                name="archivos_sublinea_linea_numero_unico",
            ),
        ]

    def __str__(self):
        return f"{self.linea_id}.{self.numero} - {self.descripcion}"


class Ubicacion(models.Model):
    ubicacion = models.CharField("Ubicación", max_length=50, primary_key=True)
    bodega = models.CharField("Bodega", max_length=100)
    sector = models.CharField("Sector", max_length=100)
    tipo = models.CharField("Tipo", max_length=100)

    class Meta:
        ordering = ("bodega", "sector", "ubicacion")
        verbose_name = "ubicación"
        verbose_name_plural = "ubicaciones"

    def __str__(self):
        return f"{self.ubicacion} - {self.bodega} / {self.sector}"


class CargaConteoInventario(models.Model):
    archivo_nombre = models.CharField("archivo", max_length=255)
    total_registros = models.PositiveIntegerField("registros", default=0)
    total_codigos = models.PositiveIntegerField("códigos distintos", default=0)
    total_bodegas = models.PositiveIntegerField("bodegas", default=0)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_conteo_inventario",
        verbose_name="cargado por",
    )
    fecha_carga = models.DateTimeField("fecha de carga", auto_now_add=True)

    class Meta:
        ordering = ("-fecha_carga", "-pk")
        verbose_name = "carga de conteo de inventario"
        verbose_name_plural = "cargas de conteo de inventario"

    def __str__(self):
        return f"{self.archivo_nombre} ({self.total_registros} registros)"


class DetalleConteoInventario(models.Model):
    carga = models.ForeignKey(
        CargaConteoInventario,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="carga",
    )
    bodega = models.CharField("bodega", max_length=100)
    ubicacion = models.CharField("ubicación", max_length=100)
    codigo = models.CharField("código", max_length=100)
    cantidad = models.DecimalField("cantidad", max_digits=18, decimal_places=4)

    class Meta:
        ordering = ("bodega", "ubicacion", "codigo", "pk")
        verbose_name = "detalle de conteo de inventario"
        verbose_name_plural = "detalles de conteo de inventario"
        indexes = [
            models.Index(fields=("codigo",), name="arch_conteo_codigo_idx"),
            models.Index(fields=("ubicacion",), name="arch_conteo_ubic_idx"),
            models.Index(fields=("carga", "codigo"), name="arch_carga_codigo_idx"),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.ubicacion}: {self.cantidad}"


class AjusteCantidadConteoInventario(models.Model):
    detalle = models.ForeignKey(
        DetalleConteoInventario,
        on_delete=models.CASCADE,
        related_name="ajustes_cantidad",
    )
    cantidad_anterior = models.DecimalField(max_digits=18, decimal_places=4)
    cantidad_nueva = models.DecimalField(max_digits=18, decimal_places=4)
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ajustes_conteo_inventario",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha", "-pk")
        verbose_name = "ajuste de cantidad contada"
        verbose_name_plural = "ajustes de cantidades contadas"


class CargaConteoBE(models.Model):
    registro_unico = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    archivo_nombre = models.CharField("archivo", max_length=255)
    total_registros = models.PositiveIntegerField("registros", default=0)
    total_codigos = models.PositiveIntegerField("códigos distintos", default=0)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_conteo_be",
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha_carga", "-pk")
        verbose_name = "carga de conteo BE"
        verbose_name_plural = "cargas de conteo BE"

    def __str__(self):
        return f"{self.archivo_nombre} ({self.total_registros} registros)"


class DetalleConteoBE(models.Model):
    carga = models.ForeignKey(
        CargaConteoBE,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    bodega = models.CharField(max_length=20)
    codigo = models.CharField(max_length=100)
    cantidad = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        ordering = ("bodega", "codigo", "pk")
        verbose_name = "detalle de conteo BE"
        verbose_name_plural = "detalles de conteo BE"
        constraints = [
            models.UniqueConstraint(fields=("carga", "bodega", "codigo"), name="arch_be_carga_bodega_codigo_unico"),
        ]
        indexes = [models.Index(fields=("codigo",), name="arch_be_codigo_idx")]

    def __str__(self):
        return f"{self.bodega} · {self.codigo}: {self.cantidad}"


class CargaRGE(models.Model):
    registro_unico = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    archivo_nombre = models.CharField("archivo", max_length=255)
    total_registros = models.PositiveIntegerField("registros", default=0)
    total_codigos = models.PositiveIntegerField("códigos distintos", default=0)
    total_ubicaciones = models.PositiveIntegerField("ubicaciones distintas", default=0)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_rge",
        verbose_name="cargado por",
    )
    fecha_carga = models.DateTimeField("fecha de carga", auto_now_add=True)

    class Meta:
        ordering = ("-fecha_carga", "-pk")
        verbose_name = "carga RGE"
        verbose_name_plural = "cargas RGE"

    def __str__(self):
        return f"{self.archivo_nombre} ({self.total_registros} registros)"


class DetalleRGE(models.Model):
    carga = models.ForeignKey(
        CargaRGE,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="carga",
    )
    codigo = models.CharField("código", max_length=100)
    ubicacion = models.CharField("ubicación", max_length=100)
    cantidad = models.DecimalField(
        "cantidad",
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("ubicacion", "codigo", "pk")
        verbose_name = "detalle RGE"
        verbose_name_plural = "detalles RGE"
        constraints = [
            models.UniqueConstraint(
                fields=("carga", "codigo", "ubicacion"),
                name="arch_rge_carga_codigo_ubic_unico",
            ),
        ]
        indexes = [
            models.Index(fields=("codigo",), name="arch_rge_codigo_idx"),
            models.Index(fields=("ubicacion",), name="arch_rge_ubic_idx"),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.ubicacion}"


class CargaBaseCosto(models.Model):
    registro_unico = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    archivo_nombre = models.CharField("archivo", max_length=255)
    total_registros = models.PositiveIntegerField("registros", default=0)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_base_costo",
        verbose_name="cargado por",
    )
    fecha_carga = models.DateTimeField("fecha de carga", auto_now_add=True)

    class Meta:
        ordering = ("-fecha_carga", "-pk")
        verbose_name = "carga de base de costo"
        verbose_name_plural = "cargas de base de costo"

    def __str__(self):
        return f"{self.archivo_nombre} ({self.total_registros} registros)"


class CostoProducto(models.Model):
    codigo = models.CharField("código", max_length=100, primary_key=True)
    carga = models.ForeignKey(
        CargaBaseCosto,
        on_delete=models.CASCADE,
        related_name="costos",
        verbose_name="carga",
    )
    costo = models.DecimalField("costo MCOSUC", max_digits=18, decimal_places=4)

    class Meta:
        ordering = ("codigo",)
        verbose_name = "costo de producto"
        verbose_name_plural = "costos de productos"

    def __str__(self):
        return f"{self.codigo}: {self.costo}"
