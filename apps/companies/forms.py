import re

from django import forms
from django.utils import timezone

from apps.geography.forms import LocationFieldsMixin

from .models import CEDULA_PATTERN, Area, Company, Position, Site, Worker
from .nit import InvalidNit, Nit


def normalize_name(value: str) -> str:
    return " ".join(value.split())


class CompanyForm(LocationFieldsMixin, forms.ModelForm):
    """Persona jurídica con NIT o persona natural con cédula.

    Los dos documentos son campos de texto libre: aceptan puntos, espacios y, en el NIT, el
    guion con el dígito de verificación; se guarda solo el número. Solo se usa el documento
    del tipo elegido y el otro queda vacío. La unicidad la valida el modelo, sobre el valor
    ya normalizado.
    """

    person_type = forms.ChoiceField(
        label="Tipo de persona",
        choices=Company.PersonType.choices,
        error_messages={
            "required": "Elige si la empresa es persona natural o jurídica.",
            "invalid_choice": "Elige si la empresa es persona natural o jurídica.",
        },
    )
    nit = forms.CharField(
        label="NIT",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. 900.123.456-8"}),
    )
    cedula = forms.CharField(
        label="Cédula",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. 1.094.887.654", "inputmode": "numeric"}),
    )

    class Meta:
        model = Company
        fields = ["person_type", "name", "nit", "cedula", "municipality", "is_active"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Ej. Café Montaña S.A.S."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["nit"] = self.instance.nit_display
            self.initial["cedula"] = self.instance.cedula_display
        else:
            # Una empresa nueva siempre nace activa.
            del self.fields["is_active"]
        self.setup_location()

    def clean_name(self):
        return normalize_name(self.cleaned_data["name"])

    def clean_nit(self):
        raw = self.cleaned_data["nit"].strip()
        if not raw or self.data.get("person_type") != Company.PersonType.JURIDICA:
            return None
        try:
            return Nit.parse(raw).number
        except InvalidNit as error:
            raise forms.ValidationError(str(error)) from error

    def clean_cedula(self):
        raw = self.cleaned_data["cedula"].strip()
        if not raw or self.data.get("person_type") != Company.PersonType.NATURAL:
            return None
        number = re.sub(r"[\s.]", "", raw)
        if not re.fullmatch(CEDULA_PATTERN, number):
            raise forms.ValidationError("Escribe una cédula válida: solo números, entre 4 y 10 dígitos.")
        return number

    def clean(self):
        cleaned = super().clean()
        person_type = cleaned.get("person_type")
        if person_type == Company.PersonType.JURIDICA:
            field, other_field, missing = "nit", "cedula", "El NIT es obligatorio."
        elif person_type == Company.PersonType.NATURAL:
            field, other_field, missing = "cedula", "nit", "La cédula es obligatoria."
        else:
            return cleaned
        if field in self.errors:
            return cleaned
        if not cleaned.get(field):
            self.add_error(field, missing)
            return cleaned
        # El NIT de una persona natural es su cédula: el mismo número con los dos tipos
        # sería el mismo cliente registrado dos veces.
        other = Company.objects.filter(**{other_field: cleaned[field]}).exclude(pk=self.instance.pk).first()
        if other is not None:
            taken_as = "el NIT" if other_field == "nit" else "la cédula"
            self.add_error(field, f"Este número ya está registrado como {taken_as} de {other.name.rstrip('.')}.")
        return cleaned


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
