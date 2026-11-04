from datetime import datetime

from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.accounts.permissions import Capability, has_capability
from apps.companies.cascade import PositionCascadeForm
from apps.companies.selectors import visible_companies

from .models import Visit


class VisitForm(PositionCascadeForm):
    date = forms.DateField(
        label="Fecha", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    time = forms.TimeField(
        label="Hora", widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"})
    )

    cascade_url_name = "visits:cascade"
    field_order = ["date", "time", "company", "site", "area", "position", "contact_name"]

    class Meta:
        model = Visit
        fields = ["position", "contact_name"]
        widgets = {"contact_name": forms.TextInput(attrs={"placeholder": "Ej. Marta Salazar"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_scheduled_at = self.instance.scheduled_at
        if self.instance.pk:
            local = timezone.localtime(self.instance.scheduled_at)
            self.initial.update(date=local.date(), time=local.time())
            self.load_initial_from_position(self.instance.position)
        else:
            self.instance.created_by = user

        allowed = Q(is_active=True)
        if self.instance.pk:
            # Una visita ya registrada se puede corregir aunque la empresa se haya desactivado.
            allowed |= Q(pk=self.instance.company.pk)
        self.configure_cascade(
            visible_companies(user).filter(allowed),
            lock_to_single_company=not has_capability(user, Capability.COMPANY_VIEW_ALL),
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
