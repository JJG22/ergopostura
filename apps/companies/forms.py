from django import forms
from django.utils import timezone

from apps.geography.forms import LocationFieldsMixin

from .models import Area, Company, Position, Site, Worker
from .nit import InvalidNit, Nit


def normalize_name(value: str) -> str:
    return " ".join(value.split())


class CompanyForm(LocationFieldsMixin, forms.ModelForm):
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
        fields = ["name", "nit", "municipality", "is_active"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Ej. Café Montaña S.A.S."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["nit"] = self.instance.nit_display
        else:
            # Una empresa nueva siempre nace activa.
            del self.fields["is_active"]
        self.setup_location()

    def clean_name(self):
        return normalize_name(self.cleaned_data["name"])

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


class SiteForm(LocationFieldsMixin, SiblingUniqueNameForm):
    parent_field = "company"
    duplicate_message = "Esta empresa ya tiene una sede con ese nombre."

    class Meta:
        model = Site
        fields = ["name", "municipality", "address"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Ej. Planta Armenia"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.is_bound:
            # Lo usual es que la sede quede donde esta la empresa; el usuario lo puede cambiar.
            company = getattr(self.instance, "company", None)
            if company is not None:
                self.initial.setdefault("municipality", company.municipality_id)
                self.initial.setdefault("department", company.municipality.department_id)
        self.setup_location()


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


class WorkerForm(forms.ModelForm):
    """El puesto viene de la URL. El documento no se repite dentro de la misma empresa."""

    class Meta:
        model = Worker
        fields = ["first_name", "last_name", "document_type", "document_number", "hired_on", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "off"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "off"}),
            "document_number": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
            "hired_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        if parent is not None:
            self.instance.position = parent
        if not self.instance.pk:
            del self.fields["is_active"]

    def clean_first_name(self):
        return normalize_name(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return normalize_name(self.cleaned_data["last_name"])

    def clean_document_number(self):
        # Se acepta con puntos o espacios, como suele escribirse una cedula.
        return "".join(ch for ch in self.cleaned_data["document_number"] if ch.isalnum()).upper()

    def clean_hired_on(self):
        value = self.cleaned_data.get("hired_on")
        if value and value > timezone.localdate():
            raise forms.ValidationError("La fecha de ingreso no puede ser futura.")
        return value

    def clean(self):
        cleaned = super().clean()
        number, kind = cleaned.get("document_number"), cleaned.get("document_type")
        if number and kind:
            company = self.instance.position.area.site.company
            duplicates = Worker.objects.filter(
                position__area__site__company=company, document_type=kind, document_number=number
            ).exclude(pk=self.instance.pk)
            other = duplicates.select_related("position").first()
            if other is not None:
                self.add_error(
                    "document_number",
                    f"Este documento ya está registrado en la empresa ({other.full_name}, puesto {other.position}).",
                )
        return cleaned
