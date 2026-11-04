from datetime import datetime

from django import forms
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.permissions import Capability, has_capability
from apps.companies.models import Area, Company, Position, Site
from apps.companies.selectors import visible_companies

from .models import Visit


def _pick(queryset, value):
    """Devuelve el registro elegido si pertenece a las opciones permitidas."""
    try:
        return queryset.filter(pk=value).first()
    except (TypeError, ValueError):
        return None


class VisitForm(forms.ModelForm):
    """Cada lista depende de la anterior: empresa, sede, area y puesto.

    Las opciones se calculan en el servidor a partir de lo elegido y del alcance del
    usuario. Enviar a mano un puesto de otra empresa, o que no corresponda a la sede
    elegida, lo deja fuera de las opciones y el formulario lo rechaza.
    """

    date = forms.DateField(
        label="Fecha", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    time = forms.TimeField(
        label="Hora", widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"})
    )
    company = forms.ModelChoiceField(
        Company.objects.none(), label="Empresa", empty_label="Selecciona una empresa"
    )
    site = forms.ModelChoiceField(Site.objects.none(), label="Sede")
    area = forms.ModelChoiceField(Area.objects.none(), label="Área de trabajo")
    position = forms.ModelChoiceField(Position.objects.none(), label="Puesto de trabajo")

    field_order = ["date", "time", "company", "site", "area", "position", "contact_name"]

    class Meta:
        model = Visit
        fields = ["position", "contact_name"]
        widgets = {"contact_name": forms.TextInput(attrs={"placeholder": "Ej. Marta Salazar"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self._original_scheduled_at = self.instance.scheduled_at
        if self.instance.pk:
            self._load_initial_from_instance()
        else:
            self.instance.created_by = user

        source = self.data if self.is_bound else self.initial
        company = self._configure_company(source)
        site = self._configure_child(
            "site", Site.objects.filter(company=company) if company else None, source,
            "Selecciona una sede", "Selecciona primero una empresa",
        )
        area = self._configure_child(
            "area", Area.objects.filter(site=site) if site else None, source,
            "Selecciona un área", "Selecciona primero una sede",
        )
        self._configure_child(
            "position", Position.objects.filter(area=area) if area else None, source,
            "Selecciona un puesto", "Selecciona primero un área",
        )
        self._attach_cascade("company", "site", "area")

    def _load_initial_from_instance(self):
        local = timezone.localtime(self.instance.scheduled_at)
        visit = self.instance
        self.initial.update(
            date=local.date(),
            time=local.time(),
            company=visit.company.pk,
            site=visit.site.pk,
            area=visit.area.pk,
            position=visit.position_id,
        )

    def _configure_company(self, source):
        allowed = Q(is_active=True)
        if self.instance.pk:
            # Una visita ya registrada se puede corregir aunque la empresa se haya desactivado.
            allowed |= Q(pk=self.instance.company.pk)
        companies = visible_companies(self.user).filter(allowed)

        if not has_capability(self.user, Capability.COMPANY_VIEW_ALL):
            del self.fields["company"]
            return companies.first()

        self.fields["company"].queryset = companies
        return _pick(companies, source.get("company"))

    def _configure_child(self, name, queryset, source, label, waiting_label):
        field = self.fields[name]
        if queryset is None:
            field.empty_label = waiting_label
            field.widget.attrs["disabled"] = True
            return None
        field.queryset = queryset
        field.empty_label = label
        return _pick(queryset, source.get(name))

    def _attach_cascade(self, *names):
        for name in names:
            if name in self.fields:
                self.fields[name].widget.attrs.update(
                    {
                        "hx-get": reverse("visits:cascade"),
                        "hx-trigger": "change",
                        "hx-target": "#form-fields",
                        # Sin espera: un cambio justo despues del reemplazo no debe perderse.
                        "hx-swap": "innerHTML settle:0ms",
                        "hx-include": "closest form",
                        "hx-params": "not csrfmiddlewaretoken",
                    }
                )

    def clean(self):
        cleaned = super().clean()
        date, time = cleaned.get("date"), cleaned.get("time")
        if date is None or time is None:
            return cleaned

        scheduled_at = timezone.make_aware(datetime.combine(date, time))
        changed = scheduled_at != self._original_scheduled_at
        # Corregir otro dato de una visita ya pasada no debe obligar a cambiar su fecha.
        if changed and scheduled_at < timezone.now():
            self.add_error("date", "La fecha y la hora de la visita ya pasaron.")

        position = cleaned.get("position")
        if position is not None:
            duplicates = Visit.objects.filter(position=position, scheduled_at=scheduled_at)
            if duplicates.exclude(pk=self.instance.pk).exists():
                self.add_error(None, "Ya hay una visita registrada para este puesto en esa fecha y hora.")

        self.instance.scheduled_at = scheduled_at
        return cleaned
