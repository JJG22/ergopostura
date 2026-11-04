"""Seleccion de un puesto con listas dependientes: empresa, sede, area y puesto.

Las opciones se calculan en el servidor a partir de lo elegido y de las empresas permitidas.
Enviar a mano un puesto de otra empresa, o que no corresponda a la sede elegida, lo deja
fuera de las opciones y el formulario lo rechaza.
"""
from django import forms
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from apps.accounts.mixins import CapabilityRequiredMixin

from .models import Area, Company, Position, Site


def pick(queryset, value):
    """Devuelve el registro elegido si pertenece a las opciones permitidas."""
    try:
        return queryset.filter(pk=value).first()
    except (TypeError, ValueError):
        return None


class PositionCascadeForm(forms.ModelForm):
    company = forms.ModelChoiceField(
        Company.objects.none(), label="Empresa", empty_label="Selecciona una empresa"
    )
    site = forms.ModelChoiceField(Site.objects.none(), label="Sede")
    area = forms.ModelChoiceField(Area.objects.none(), label="Área de trabajo")
    position = forms.ModelChoiceField(Position.objects.none(), label="Puesto de trabajo")

    cascade_url_name: str
    cascade_triggers = ("company", "site", "area")

    @property
    def cascade_source(self):
        return self.data if self.is_bound else self.initial

    def load_initial_from_position(self, position: Position):
        area = position.area
        self.initial.update(
            company=area.site.company_id, site=area.site_id, area=area.pk, position=position.pk
        )

    def configure_cascade(self, companies, *, lock_to_single_company: bool = False):
        """Limita cada lista segun la anterior. Devuelve el puesto elegido, si es valido."""
        source = self.cascade_source
        if lock_to_single_company:
            del self.fields["company"]
            company = companies.first()
        else:
            self.fields["company"].queryset = companies
            company = pick(companies, source.get("company"))

        site = self._configure_child(
            "site", Site.objects.filter(company=company) if company else None,
            "Selecciona una sede", "Selecciona primero una empresa",
        )
        area = self._configure_child(
            "area", Area.objects.filter(site=site) if site else None,
            "Selecciona un área", "Selecciona primero una sede",
        )
        position = self._configure_child(
            "position", Position.objects.filter(area=area) if area else None,
            "Selecciona un puesto", "Selecciona primero un área",
        )
        self._attach_triggers()
        return position

    def _configure_child(self, name, queryset, label, waiting_label):
        field = self.fields[name]
        if queryset is None:
            field.empty_label = waiting_label
            field.widget.attrs["disabled"] = True
            return None
        field.queryset = queryset
        field.empty_label = label
        return pick(queryset, self.cascade_source.get(name))

    def _attach_triggers(self):
        for name in self.cascade_triggers:
            if name in self.fields:
                self.fields[name].widget.attrs.update(
                    {
                        "hx-get": reverse(self.cascade_url_name),
                        "hx-trigger": "change",
                        "hx-target": "#form-fields",
                        # Sin espera: un cambio justo despues del reemplazo no debe perderse.
                        "hx-swap": "innerHTML settle:0ms",
                        "hx-include": "closest form",
                        "hx-params": "not csrfmiddlewaretoken",
                    }
                )


class PositionCascadeView(CapabilityRequiredMixin, View):
    """Vuelve a dibujar los campos cuando cambia una lista, conservando lo escrito."""

    form_class = None

    def get(self, request):
        form = self.form_class(initial=request.GET.dict(), user=request.user)
        return render(request, "core/partials/form_fields.html", {"form": form})
