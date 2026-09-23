from django.conf import settings
from django.db import models
from pathlib import Path
from uuid import uuid4

from archivos.models import Linea


def difference_file_path(instance, filename):
    safe_name = Path(filename).name
    return f"conteo/diferencias/linea_{instance.linea_id}/{uuid4().hex}_{safe_name}"


class CargaDiferencias(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        RECONTEO = "RECONTEO", "Pendiente de reconteo"
        FINALIZADO = "FINALIZADO", "Finalizado"

    linea = models.ForeignKey(
        Linea,
        on_delete=models.PROTECT,
        related_name="cargas_diferencias",
        verbose_name="línea",
    )
    archivo_nombre = models.CharField("archivo", max_length=255)
    archivo_original = models.FileField(
        "archivo original",
        upload_to=difference_file_path,
        max_length=500,
        blank=True,
    )
    archivo_as400 = models.FileField(
        "PDF AS400 - Diferencias",
        upload_to=difference_file_path,
        max_length=500,
        blank=True,
    )
    numero_reconteo = models.PositiveIntegerField("número de reconteo")
    estado = models.CharField(
        "estado",
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    total_registros = models.PositiveIntegerField("registros", default=0)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_diferencias",
        verbose_name="cargado por",
    )
    fecha_carga = models.DateTimeField("fecha de carga", auto_now_add=True)
    seleccionado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reconteos_seleccionados",
        verbose_name="seleccionado por",
        null=True,
        blank=True,
    )
    fecha_seleccion = models.DateTimeField("fecha de selección", null=True, blank=True)
    finalizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lineas_reconteo_finalizadas",
        verbose_name="finalizado por",
        null=True,
        blank=True,
    )
    fecha_finalizacion = models.DateTimeField("fecha de finalización", null=True, blank=True)

    class Meta:
        ordering = ("-fecha_carga",)
        verbose_name = "carga de diferencias"
        verbose_name_plural = "cargas de diferencias"
        constraints = [
            models.UniqueConstraint(
                fields=("linea", "numero_reconteo"),
                name="conteo_reconteo_numero_unico_linea",
            ),
            models.UniqueConstraint(
                fields=("linea",),
                condition=models.Q(estado="PENDIENTE"),
                name="conteo_un_pendiente_por_linea",
            ),
        ]

    def __str__(self):
        return f"{self.linea.nlinea} · Reconteo #{self.numero_reconteo}"


class Diferencia(models.Model):
    carga = models.ForeignKey(
        CargaDiferencias,
        on_delete=models.CASCADE,
        related_name="diferencias",
        verbose_name="carga",
    )
    sublinea = models.CharField("sublínea", max_length=50)
    item = models.CharField("item", max_length=100, blank=True)
    codigo = models.CharField("código", max_length=100)
    descripcion = models.CharField("descripción", max_length=255, blank=True)
    ultimo_conteo = models.DecimalField("último conteo", max_digits=18, decimal_places=4)
    existencia = models.DecimalField("existencia", max_digits=18, decimal_places=4)
    diferencia = models.DecimalField("diferencia", max_digits=18, decimal_places=4)
    ubicacion_1 = models.CharField("ubicación 1", max_length=100, blank=True)
    ubicacion_2 = models.CharField("ubicación 2", max_length=100, blank=True)
    ubicacion_3 = models.CharField("ubicación 3", max_length=100, blank=True)
    ubicacion_4 = models.CharField("ubicación 4", max_length=100, blank=True)
    fecha_generacion = models.DateField("fecha de generación")
    hora_generacion = models.TimeField("hora de generación")
    seleccionada = models.BooleanField("seleccionada por gerente", default=False)

    class Meta:
        ordering = ("sublinea", "codigo")
        verbose_name = "diferencia"
        verbose_name_plural = "diferencias"
        indexes = [
            models.Index(fields=("codigo",), name="conteo_dif_codigo_idx"),
            models.Index(fields=("sublinea",), name="conteo_dif_sublinea_idx"),
        ]

    @property
    def linea(self):
        return self.carga.linea

    def __str__(self):
        return f"{self.codigo}: {self.diferencia}"


class InicioReconteoBodega(models.Model):
    carga = models.ForeignKey(
        CargaDiferencias, on_delete=models.CASCADE, related_name="inicios_bodega"
    )
    bodega = models.CharField(max_length=10, choices=(("central", "Bodega Central"), ("ransa", "RANSA")))
    iniciado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    finalizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="reconteos_bodega_finalizados", null=True, blank=True,
    )
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("carga", "bodega"), name="conteo_inicio_unico_carga_bodega")
        ]


class ValidacionUbicacion(models.Model):
    carga_rge = models.ForeignKey(
        "archivos.CargaRGE",
        on_delete=models.CASCADE,
        related_name="ubicaciones_validadas",
        verbose_name="carga RGE",
    )
    ubicacion = models.CharField("ubicación", max_length=100)
    validada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ubicaciones_validadas",
        verbose_name="validada por",
    )
    fecha_validacion = models.DateTimeField("fecha de validación", auto_now_add=True)
    validada = models.BooleanField("ubicación validada", default=True)
    modificar_rge = models.BooleanField("requiere modificar RGE", default=False)

    class Meta:
        ordering = ("ubicacion",)
        verbose_name = "validación de ubicación"
        verbose_name_plural = "validaciones de ubicaciones"
        constraints = [
            models.UniqueConstraint(
                fields=("carga_rge", "ubicacion"),
                name="conteo_validacion_unica_rge_ubicacion",
            )
        ]
        indexes = [
            models.Index(
                fields=("carga_rge", "ubicacion"),
                name="conteo_val_rge_ubic_idx",
            )
        ]

    def __str__(self):
        return f"{self.ubicacion} · {self.validada_por}"
