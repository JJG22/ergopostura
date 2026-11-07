from datetime import timedelta

from django import forms

from apps.companies.models import Company

from . import services
from .models import Contract


def _date_widget():
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})


class ContractForm(forms.ModelForm):
    document = forms.FileField(
        label="Contrato firmado (PDF)",
        required=False,
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
        help_text="Máximo 10 MB.",
    )

    field_order = [
        "document", "company", "code", "kind", "start_date", "end_date", "value", "service",
        "responsible_name", "responsible_role", "responsible_email", "responsible_phone", "notes",
    ]

    class Meta:
        model = Contract
        fields = [
            "company", "code", "kind", "service", "start_date", "end_date", "value",
            "responsible_name", "responsible_role", "responsible_email", "responsible_phone", "notes",
        ]
        widgets = {
            "start_date": _date_widget(),
            "end_date": _date_widget(),
            "service": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "code": forms.TextInput(attrs={"placeholder": "Ej. CPS-2026-014"}),
            "value": forms.NumberInput(attrs={"step": "1", "min": "0", "inputmode": "numeric"}),
        }

    def __init__(self, *args, actor, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self._pdf = None
        self.reading = None
        companies = Company.objects.filter(is_active=True)
        if self.instance.pk:
            # Un contrato no cambia de empresa: si se registro mal, se elimina y se crea otro.
            del self.fields["company"]
            self.fields["document"].help_text = "Déjalo vacío para conservar el documento actual. Máximo 10 MB."
        else:
            self.fields["document"].required = True
            self.fields["company"].queryset = companies.order_by("name")
            self.fields["company"].empty_label = "Selecciona la empresa"
            if company is not None:
                self.fields["company"].initial = company.pk

    @property
    def company(self):
        return self.instance.company if self.instance.pk else self.cleaned_data.get("company")

    def clean_document(self):
        uploaded = self.cleaned_data.get("document")
        if not uploaded:
            return None
        try:
            self._pdf = services.read_upload(uploaded)
        except services.InvalidDocument as error:
            raise forms.ValidationError(str(error)) from error
        return uploaded

    def clean(self):
        cleaned = super().clean()
        company = self.company
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if not (company and start and end):
            return cleaned
        if end < start:
            self.add_error("end_date", "El fin de la vigencia no puede ser anterior al inicio.")
            return cleaned

        other = services.overlapping(company, start, end, exclude_pk=self.instance.pk)
        if other is not None:
            self.add_error(
                "start_date",
                f"Se cruza con el contrato {other.display_code} ({other.start_date:%d/%m/%Y} – "
                f"{other.end_date:%d/%m/%Y}). Una empresa tiene un solo contrato a la vez: "
                f"si es una renovación, haz que empiece el {other.end_date + timedelta(days=1):%d/%m/%Y} o después.",
            )
        elif self.instance.pk:
            left_out = services.uncovered_visits(company, contract_pk=self.instance.pk, start=start, end=end)
            if left_out:
                self.add_error(
                    None,
                    f"Con esa vigencia, {len(left_out)} visita(s) programada(s) quedarían sin contrato. "
                    "La empresa debe reprogramarlas o cancelarlas antes de acortar el contrato.",
                )
        return cleaned

    def save(self, commit=True):
        contract = super().save(commit=False)
        if self._pdf is not None:
            data, sha256 = self._pdf
            uploaded = self.cleaned_data["document"]
            changed = sha256 != contract.file_sha256
            contract.file_data = data
            contract.file_sha256 = sha256
            contract.file_size = len(data)
            contract.file_name = uploaded.name[:255]
            if changed:
                # Otro documento: el resumen anterior ya no lo describe.
                contract.ai_summary, contract.ai_model, contract.ai_generated_at = {}, "", None
                reading = services.reading_for(sha256)
                if reading is not None:
                    services.attach_reading(contract, reading)
        if not contract.pk:
            contract.created_by = self.actor
        if commit:
            contract.save()
        return contract
