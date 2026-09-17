from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group


ROLE_CHOICES = (
    ("Supervisores", "Supervisor"),
    ("Gerente", "Gerente"),
    ("Editores", "Editor"),
)


class ManagedUserCreateForm(UserCreationForm):
    role = forms.ChoiceField(label="Grupo de trabajo", choices=ROLE_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "role", "is_active")
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "is_active": "Usuario activo",
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo.")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.groups.set([Group.objects.get(name=self.cleaned_data["role"])])
        return user


class ManagedUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(label="Grupo de trabajo", choices=ROLE_CHOICES)
    new_password = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput,
        help_text="Déjala vacía para conservar la contraseña actual.",
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "role", "is_active")
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "is_active": "Usuario activo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_group = self.instance.groups.filter(name__in=dict(ROLE_CHOICES)).first()
        if current_group:
            self.fields["role"].initial = current_group.name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        duplicate = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("Ya existe un usuario con este correo.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
            user.groups.set([Group.objects.get(name=self.cleaned_data["role"])])
        return user
