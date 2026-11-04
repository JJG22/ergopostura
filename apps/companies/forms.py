from django import forms

from .models import Area, Company, Position, Site
from .nit import InvalidNit, Nit


def normalize_name(value: str) -> str:
    return " ".join(value.split())


class CompanyForm(forms.ModelForm):
    # Campo de texto libre: acepta el NIT con puntos y guion, y guarda solo el numero base.
    # La unicidad la valida el modelo, sobre el valor ya normalizado.
    nit = forms.CharField(
        label="NIT",
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "Ej. 900.123.456-8"}),
        error_messages={"required": "El NIT es obligatorio."},
    )

    class Meta:
        model = Company
        fields = ["name", "nit", "city", "department", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ej. Café Montaña S.A.S."}),
            "city": forms.TextInput(attrs={"placeholder": "Ej. Armenia"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["nit"] = self.instance.nit_display
        else:
            # Una empresa nueva siempre nace activa.
            del self.fields["is_active"]

    def clean_name(self):
        return normalize_name(self.cleaned_data["name"])

    def clean_city(self):
        return normalize_name(self.cleaned_data["city"])

    def clean_nit(self):
        try:
            return Nit.parse(self.cleaned_data["nit"]).number
        except InvalidNit as error:
            raise forms.ValidationError(str(error)) from error


class SiblingUniqueNameForm(forms.ModelForm):
    """Base de sede, area y puesto: el padre viene de la URL, no del formulario.

    Por eso el usuario no puede cambiarlo, y por eso la unicidad del nombre se revisa
    aqui: Django omite las restricciones que incluyen campos fuera del formulario.
    """

    parent_field: str
    duplicate_message: str
    grid_class = ""

    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        if parent is not None:
            setattr(self.instance, self.parent_field, parent)

    def clean_name(self):
        name = normalize_name(self.cleaned_data["name"])
        siblings = type(self.instance).objects.filter(
            **{self.parent_field: getattr(self.instance, self.parent_field), "name__iexact": name}
        )
        if siblings.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(self.duplicate_message)
        return name


class SiteForm(SiblingUniqueNameForm):
    parent_field = "company"
    duplicate_message = "Esta empresa ya tiene una sede con ese nombre."

    class Meta:
        model = Site
        fields = ["name", "city", "department", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ej. Planta Armenia"}),
            "city": forms.TextInput(attrs={"placeholder": "Ej. Armenia"}),
        }

    def clean_city(self):
        return normalize_name(self.cleaned_data["city"])


class AreaForm(SiblingUniqueNameForm):
    parent_field = "site"
    duplicate_message = "Esta sede ya tiene un área con ese nombre."
    grid_class = "single"

    class Meta:
        model = Area
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ej. Empaque"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class PositionForm(SiblingUniqueNameForm):
    parent_field = "area"
    duplicate_message = "Esta área ya tiene un puesto con ese nombre."
    grid_class = "single"

    class Meta:
        model = Position
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ej. Operario de empaque"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
