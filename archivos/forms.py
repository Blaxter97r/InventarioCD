from pathlib import Path
from decimal import Decimal, InvalidOperation

from django import forms


class ExcelUploadForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel",
        help_text="Formato .xlsx, máximo 5 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if Path(archivo.name).suffix.lower() != ".xlsx":
            raise forms.ValidationError("El archivo debe tener extensión .xlsx.")
        if archivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo no puede superar los 5 MB.")
        return archivo


class InventoryCountUploadForm(ExcelUploadForm):
    archivo = forms.FileField(
        label="Archivo de conteo",
        help_text="Formato .xlsx, máximo 25 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if Path(archivo.name).suffix.lower() != ".xlsx":
            raise forms.ValidationError("El archivo debe tener extensión .xlsx.")
        if archivo.size > 25 * 1024 * 1024:
            raise forms.ValidationError("El archivo no puede superar los 25 MB.")
        return archivo


class InventoryCountQuantityForm(forms.Form):
    cantidad = forms.CharField(label="Cantidad contada", max_length=40)

    def clean_cantidad(self):
        raw = self.cleaned_data["cantidad"].strip().replace(",", ".")
        try:
            quantity = Decimal(raw)
        except InvalidOperation:
            raise forms.ValidationError("Ingresa una cantidad numérica válida.")
        if not quantity.is_finite() or quantity < 0 or quantity >= Decimal("100000000000000"):
            raise forms.ValidationError("La cantidad debe estar entre 0 y 99,999,999,999,999.9999.")
        if quantity != quantity.quantize(Decimal("0.0001")):
            raise forms.ValidationError("La cantidad admite hasta cuatro decimales.")
        return quantity


class RGEUploadForm(InventoryCountUploadForm):
    archivo = forms.FileField(
        label="Archivo RGE",
        help_text="Formato .xlsx, máximo 25 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )


class BECountUploadForm(InventoryCountUploadForm):
    archivo = forms.FileField(
        label="Archivo de conteo BE",
        help_text="Formato .xlsx, máximo 25 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )


class CostBaseUploadForm(InventoryCountUploadForm):
    archivo = forms.FileField(
        label="Archivo de costos",
        help_text="Formato .xlsx, máximo 25 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )
