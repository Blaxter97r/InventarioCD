from pathlib import Path
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
    cantidad = forms.IntegerField(
        label="Cantidad contada",
        min_value=-99_999_999_999_999,
        max_value=99_999_999_999_999,
        error_messages={
            "invalid": "Ingresa una cantidad entera válida.",
            "min_value": "La cantidad no puede ser menor a -99,999,999,999,999.",
            "max_value": "La cantidad no puede superar 99,999,999,999,999.",
        },
    )


class InventoryCountLocationForm(forms.Form):
    WAREHOUSE_CHOICES = (
        ("CENTRAL", "CENTRAL"),
        ("RANSA", "RANSA"),
        ("PEDREGAL", "PEDREGAL"),
    )

    codigo = forms.CharField(label="Código", max_length=100, strip=True)
    bodega = forms.ChoiceField(label="Bodega", choices=WAREHOUSE_CHOICES)
    ubicacion = forms.CharField(label="Nueva ubicación", max_length=100, strip=True)
    cantidad = InventoryCountQuantityForm.base_fields["cantidad"]

    def clean_codigo(self):
        return self.cleaned_data["codigo"].upper()

    def clean_ubicacion(self):
        return self.cleaned_data["ubicacion"].upper()


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
