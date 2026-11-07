import json
import math

from django import forms
from django.urls import reverse
from django.utils import timezone

from apps.companies.cascade import pick
from apps.companies.forms import normalize_name
from apps.companies.models import Area, Position, Worker
from apps.rula.scoring import RulaInputError, calculate
from apps.visits.models import Visit

from .models import Evaluation, Posture, Recommendation, RulaAssessment, rula_input_from


class VisitChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, visit):
        local = timezone.localtime(visit.scheduled_at)
        return f"{local:%d/%m/%Y} · {visit.site.company.name} · {visit.site.name}"


class EvaluationForm(forms.ModelForm):
    """La evaluacion parte de una visita realizada; el puesto sale de la sede visitada.

    Las listas se recalculan en el servidor con lo elegido, de modo que un puesto de otra
    sede, o un trabajador de otro puesto, quedan fuera de las opciones y se rechazan.
    """

    visit = VisitChoiceField(
        Visit.objects.none(),
        label="Visita realizada",
        empty_label="Selecciona la visita",
        help_text="Solo aparecen visitas registradas como realizadas.",
    )
    area = forms.ModelChoiceField(Area.objects.none(), label="Área de trabajo")

    cascade_url_name = "evaluations:cascade"
    field_order = [
        "visit", "area", "position", "worker", "evaluated_on",
        "activity_description", "worker_context",
        "carries_load", "load_weight_kg", "repetitive_movements", "repetition_notes",
    ]

    class Meta:
        model = Evaluation
        fields = [
            "visit", "position", "worker", "evaluated_on", "activity_description", "worker_context",
            "carries_load", "load_weight_kg", "repetitive_movements", "repetition_notes",
        ]
        widgets = {
            "evaluated_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "activity_description": forms.Textarea(attrs={"rows": 3}),
            "worker_context": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            area = self.instance.position.area
            self.initial.setdefault("area", area.pk)
        else:
            self.instance.evaluator = user

        visits = Visit.objects.filter(status=Visit.Status.COMPLETED, site__company__is_active=True)
        if self.instance.pk:
            visits = visits | Visit.objects.filter(pk=self.instance.visit_id)
        visits = visits.select_related("site__company").order_by("-scheduled_at")
        self.fields["visit"].queryset = visits

        source = self.data if self.is_bound else self.initial
        visit = pick(visits, source.get("visit"))
        area = self._child("area", Area.objects.filter(site=visit.site) if visit else None,
                           "Selecciona un área", "Selecciona primero la visita", source)
        position = self._child("position", Position.objects.filter(area=area) if area else None,
                               "Selecciona un puesto", "Selecciona primero un área", source)
        worker = self.fields["worker"]
        worker.required = False
        if position is not None:
            worker.queryset = Worker.objects.filter(position=position, is_active=True)
            if self.instance.worker_id:
                worker.queryset = worker.queryset | Worker.objects.filter(pk=self.instance.worker_id)
            worker.empty_label = "Sin indicar"
            worker.label_from_instance = lambda item: f"{item.full_name} · {item.document_display}"
        else:
            worker.queryset = Worker.objects.none()
            worker.empty_label = "Selecciona primero un puesto"
            worker.widget.attrs["disabled"] = True

        if visit is not None and not self.is_bound and not self.instance.pk:
            self.initial.setdefault("evaluated_on", timezone.localdate(visit.scheduled_at))
        self.initial.setdefault("evaluated_on", timezone.localdate())
        if visit is not None and not self.fields["area"].queryset.exists():
            self.fields["area"].help_text = "La sede visitada aún no tiene áreas. Regístralas en Empresas."

        for name in ("visit", "area", "position"):
            self.fields[name].widget.attrs.update(
                {
                    "hx-get": reverse(self.cascade_url_name),
                    "hx-trigger": "change",
                    "hx-target": "#form-fields",
                    "hx-swap": "innerHTML settle:0ms",
                    "hx-include": "closest form",
                    "hx-params": "not csrfmiddlewaretoken",
                }
            )

    def _child(self, name, queryset, label, waiting_label, source):
        field = self.fields[name]
        if queryset is None:
            field.queryset = field.queryset.none()
            field.empty_label = waiting_label
            field.widget.attrs["disabled"] = True
            return None
        field.queryset = queryset
        field.empty_label = label
        return pick(queryset, source.get(name))

    def clean(self):
        cleaned = super().clean()
        visit, evaluated_on = cleaned.get("visit"), cleaned.get("evaluated_on")
        if visit is not None and evaluated_on is not None:
            visit_day = timezone.localdate(visit.scheduled_at)
            if evaluated_on < visit_day:
                self.add_error("evaluated_on", f"La evaluación no puede ser anterior a la visita ({visit_day:%d/%m/%Y}).")
            if evaluated_on > timezone.localdate():
                self.add_error("evaluated_on", "La fecha de la evaluación no puede ser futura.")
        if cleaned.get("load_weight_kg") and not cleaned.get("carries_load"):
            self.add_error("load_weight_kg", "Indica que la actividad incluye carga, o deja vacío el peso.")
        if not cleaned.get("repetitive_movements"):
            cleaned["repetition_notes"] = ""
        return cleaned


class PostureForm(forms.ModelForm):
    class Meta:
        model = Posture
        fields = ["name", "side", "duration_value", "duration_unit"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Ej. Empaque en banda"})}

    def __init__(self, *args, evaluation=None, **kwargs):
        super().__init__(*args, **kwargs)
        if evaluation is not None:
            self.instance.evaluation = evaluation

    def clean(self):
        cleaned = super().clean()
        name, side = cleaned.get("name"), cleaned.get("side")
        if name and side:
            name = normalize_name(name)
            cleaned["name"] = name
            # Django omite esta restriccion porque la evaluacion no esta en el formulario.
            duplicates = Posture.objects.filter(
                evaluation=self.instance.evaluation, name__iexact=name, side=side
            ).exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error("name", "Esta evaluación ya tiene esa postura para el mismo lado.")
        return cleaned


class PhotoChoiceField(forms.ModelChoiceField):
    widget = forms.RadioSelect


class RulaAssessmentForm(forms.ModelForm):
    photo = PhotoChoiceField(
        None,
        label="Fotografía analizada",
        empty_label=None,
        error_messages={"required": "Elige la fotografía que se analiza."},
    )

    GROUPS = (
        ("Grupo A · Brazo y antebrazo", ("upper_arm_angle", "shoulder_raised", "upper_arm_abducted", "arm_supported", "lower_arm_angle", "lower_arm_across_midline_or_out")),
        ("Grupo A · Muñeca", ("wrist_angle", "wrist_bent_from_midline", "wrist_twist_near_end")),
        ("Grupo A · Actividad", ("arm_static_or_repeated", "arm_load")),
        ("Grupo B · Cuello y tronco", ("neck_angle", "neck_twisted", "neck_side_bent", "trunk_angle", "trunk_supported_seated", "trunk_twisted", "trunk_side_bent")),
        ("Grupo B · Piernas y actividad", ("legs_supported_and_balanced", "body_static_or_repeated", "body_load")),
    )
    ANGLE_HELP = {
        "upper_arm_angle": "Grados. Positivo es flexión; negativo, extensión.",
        "lower_arm_angle": "Grados de flexión del codo.",
        "wrist_angle": "Grados desde la posición neutra, 0 si está recta.",
        "neck_angle": "Grados. Positivo es flexión; negativo, extensión.",
        "trunk_angle": "Grados de flexión, 0 si está erguido.",
    }

    class Meta:
        model = RulaAssessment
        exclude = ["posture"]

    # La llena el navegador si el evaluador pide la sugerencia de angulos con IA.
    ai_suggestion = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, posture, photos, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.posture = posture
        self.fields["photo"].queryset = photos
        if self.instance.ai_suggestion:
            self.initial["ai_suggestion"] = json.dumps(self.instance.ai_suggestion)
        for name, help_text in self.ANGLE_HELP.items():
            field = self.fields[name]
            field.help_text = help_text
            field.widget.attrs.update(step="0.5", inputmode="decimal")

    @property
    def groups(self):
        return [(title, [self[name] for name in names]) for title, names in self.GROUPS]

    def clean_ai_suggestion(self):
        """Solo se guarda una sugerencia con la forma esperada; lo demas se descarta.

        Viene del navegador, asi que se trata como dato no confiable: no afecta el calculo,
        solo deja constancia de lo que se propuso.
        """
        raw = self.cleaned_data.get("ai_suggestion") or ""
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            return {}
        if not isinstance(data, dict) or not isinstance(data.get("angles"), dict):
            return {}
        angles = {}
        for name in RulaAssessment.ANGLE_FIELDS:
            value = data["angles"].get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                angles[name] = None
            elif math.isfinite(value) and -180 <= value <= 180:
                angles[name] = round(float(value) * 2) / 2
            else:
                angles[name] = None
        if all(value is None for value in angles.values()):
            return {}
        photo = data.get("photo")
        model = data.get("model")
        return {
            "angles": angles,
            "photo": photo if isinstance(photo, int) and not isinstance(photo, bool) else None,
            "side": data.get("side") if data.get("side") in ("derecho", "izquierdo") else None,
            "model": model[:60] if isinstance(model, str) else "",
            "frontal": data.get("frontal") is True,
        }

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        try:
            calculate(rula_input_from(cleaned))
        except RulaInputError as error:
            self.add_error(None, str(error))
        return cleaned

    def save(self, commit=True):
        self.instance.ai_suggestion = self.cleaned_data.get("ai_suggestion") or {}
        self.instance.recalculate()
        return super().save(commit=commit)


class RecommendationForm(forms.ModelForm):
    class Meta:
        model = Recommendation
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Qué mejorar en el puesto, según lo observado"}
            )
        }

    def clean_text(self):
        return " ".join(self.cleaned_data["text"].split())
