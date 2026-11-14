"""Lista dependiente departamento > municipio para cualquier formulario con `municipality`."""
from django import forms

from .models import Department, Municipality

EMPTY_LABEL = "Selecciona un municipio"
WAITING_LABEL = "Selecciona primero un departamento"


def municipality_choices(department_id):
    """Devuelve el departamento elegido y sus municipios; nada si el valor no es valido."""
    department = None
    if department_id:
        try:
            department = Department.objects.filter(pk=department_id).first()
        except (TypeError, ValueError):
            department = None
    if department is None:
        return None, Municipality.objects.none()
    return department, department.municipalities.all()


class LocationFieldsMixin:
    """Agrega «Departamento» antes de «Municipio» y limita los municipios al departamento.

    Solo se guarda el municipio; el departamento sale de el. Asi una sede no puede quedar
    con un municipio de un departamento y el nombre de otro. Si alguien envia a mano un
    municipio de otro departamento, queda fuera de las opciones y el formulario lo rechaza.
    """

    def setup_location(self):
        if self.instance.pk and self.instance.municipality_id:
            self.initial.setdefault("department", self.instance.municipality.department_id)

        department_field = forms.ModelChoiceField(
            Department.objects.all(),
            label="Departamento",
            empty_label="Selecciona un departamento",
            error_messages={"required": "Selecciona el departamento."},
        )
        fields = {}
        for name, field in self.fields.items():
            if name == "municipality":
                fields["department"] = department_field
            fields[name] = field
        self.fields = fields

        if self.is_bound:
            chosen = self.data.get(self.add_prefix("department"))
        else:
            chosen = self.initial.get("department")
        _, municipalities = municipality_choices(chosen)
        municipality = self.fields["municipality"]
        municipality.queryset = municipalities
        municipality.label = "Municipio"
        municipality.empty_label = EMPTY_LABEL if chosen and municipalities.exists() else WAITING_LABEL
        municipality.error_messages["required"] = "Selecciona el municipio."
        municipality.error_messages["invalid_choice"] = "El municipio no pertenece al departamento elegido."
