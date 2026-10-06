from pathlib import Path

from django import forms
from django.db.models import Exists, IntegerField, OuterRef
from django.db.models.functions import Cast
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from archivos.models import Linea
from .models import CargaDiferencias


class LineaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        pending = " · Pendiente de revisión" if getattr(obj, "tiene_pendiente", False) else ""
        return f"Línea {obj.nlinea} · {obj.descripcion}{pending}"


def validate_as400_pdf(archivo):
    if not archivo:
        return archivo
    if Path(archivo.name).suffix.lower() != ".pdf":
        raise forms.ValidationError("El archivo AS400 debe tener extensión .pdf.")
    if archivo.size > 20 * 1024 * 1024:
        raise forms.ValidationError("El PDF AS400 no puede superar los 20 MB.")
    try:
        reader = PdfReader(archivo)
        if reader.is_encrypted or not reader.pages:
            raise forms.ValidationError("El PDF AS400 debe tener páginas y no estar protegido.")
    except (PdfReadError, OSError, ValueError, TypeError) as error:
        raise forms.ValidationError("El archivo AS400 no es un PDF válido.") from error
    finally:
        archivo.seek(0)
    return archivo


class AS400ReplacementForm(forms.Form):
    archivo_as400 = forms.FileField(required=True)

    def clean_archivo_as400(self):
        return validate_as400_pdf(self.cleaned_data["archivo_as400"])


class DiferenciasUploadForm(forms.Form):
    linea = LineaChoiceField(
        label="Línea de producto",
        queryset=Linea.objects.none(),
        empty_label="Selecciona una línea",
    )
    archivo = forms.FileField(
        label="Archivo de diferencias",
        help_text="Formato .xlsx, máximo 10 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )
    archivo_as400 = forms.FileField(
        label="AS400 - Diferencias (PDF)",
        help_text="Opcional. Formato .pdf, máximo 20 MB.",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,application/pdf"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pending_loads = CargaDiferencias.objects.filter(
            linea_id=OuterRef("pk"),
            estado=CargaDiferencias.Estado.PENDIENTE,
        )
        self.fields["linea"].queryset = Linea.objects.filter(activa=True).annotate(
            orden_numerico=Cast("nlinea", IntegerField()),
            tiene_pendiente=Exists(pending_loads),
        ).order_by("orden_numerico", "nlinea")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if Path(archivo.name).suffix.lower() != ".xlsx":
            raise forms.ValidationError("El archivo debe tener extensión .xlsx.")
        if archivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("El archivo no puede superar los 10 MB.")
        return archivo

    def clean_archivo_as400(self):
        return validate_as400_pdf(self.cleaned_data.get("archivo_as400"))
