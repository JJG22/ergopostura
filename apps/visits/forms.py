from django import forms
from django.utils import timezone

from apps.companies.models import Site

from . import rules
from .models import Visit


class VisitForm(forms.ModelForm):
    """La empresa agenda o reprograma una visita en una de sus sedes."""

    date = forms.DateField(label="Fecha", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))
    time = forms.TimeField(
        label="Hora de llegada",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time", "step": "1800"}),
        help_text=f"De lunes a sábado, entre las {rules.WORK_START:%H:%M} y las {rules.WORK_END:%H:%M}.",
    )

    field_order = ["date", "time", "duration_minutes", "site", "purpose", "contact_name", "contact_phone"]

    class Meta:
        model = Visit
        fields = ["site", "duration_minutes", "purpose", "contact_name", "contact_phone"]
        widgets = {
            "purpose": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Ej. Evaluar los puestos de empaque y despacho de la planta."}
            ),
            "contact_name": forms.TextInput(attrs={"placeholder": "Ej. Marta Salazar, jefe de SST"}),
            "contact_phone": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "Ej. 300 123 4567"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = user.company
        if self.instance.pk:
            local = timezone.localtime(self.instance.scheduled_at)
            self.initial.update(date=local.date(), time=local.time())
        else:
            self.instance.requested_by = user
        site = self.fields["site"]
        site.queryset = Site.objects.filter(company=self.company).select_related("municipality")
        site.empty_label = "Selecciona la sede"
        site.label_from_instance = lambda item: f"{item.name} · {item.municipality.name}"
        if site.queryset.count() == 1:
            site.initial = site.queryset.first().pk

    def clean(self):
        cleaned = super().clean()
        day, hour, minutes = cleaned.get("date"), cleaned.get("time"), cleaned.get("duration_minutes")
        if day is None or hour is None or minutes is None:
            return cleaned
        start = rules.combine(day, hour)
        unchanged = (
            self.instance.pk
            and start == self.instance.scheduled_at
            and minutes == self.instance.duration_minutes
        )
        if not unchanged:
            for problem in rules.schedule_problems(self.company, start, minutes, exclude_pk=self.instance.pk):
                self.add_error(None, problem)
        self.instance.scheduled_at = start
        return cleaned


class CompleteVisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["completion_notes"]
        widgets = {
            "completion_notes": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Qué se observó, qué puestos se evaluaron, acuerdos con la empresa."}
            )
        }
        labels = {"completion_notes": "Observaciones (opcional)"}


class CancelVisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["cancellation_reason"]
        widgets = {"cancellation_reason": forms.TextInput(attrs={"placeholder": "Ej. Cambio de prioridades en la planta"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cancellation_reason"].required = True
