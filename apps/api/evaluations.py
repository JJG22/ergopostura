"""Evaluaciones RULA: datos de la observación, posturas, fotografías, análisis y recomendaciones.

Todo pasa por los selectores de apps.evaluations: cada ingeniero modifica solo sus
evaluaciones en curso, y la empresa ve solo las terminadas de su empresa. Los formularios y
servicios son los mismos de la pantalla actual, así que el cálculo RULA no se duplica.
"""
import json

from django.db import IntegrityError, transaction
from django.db.models import RestrictedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import Capability, has_capability
from apps.evaluations import selectors, services
from apps.evaluations.forms import EvaluationForm, PostureForm, RecommendationForm, RulaAssessmentForm
from apps.evaluations.models import Evaluation, Posture, PosturePhoto, Recommendation, RulaAssessment
from apps.evaluations.photos import InvalidPhoto
from apps.rula.risk import ACTION_LEVELS

from . import presenters
from .common import choices, invalid, paginate, save_form
from .errors import error_response
from .permissions import HasCapability

VIEW = (Capability.EVALUATION_VIEW_ALL, Capability.EVALUATION_VIEW_OWN)
MANAGE = (Capability.EVALUATION_MANAGE,)
DUPLICATE_POSTURE = "Esta evaluación ya tiene esa postura para el mismo lado."


def photo_url(pk) -> str:
    return f"/api/v1/evaluations/photos/{pk}/"


def number(value):
    return float(value) if value is not None else None


def result_data(result) -> dict | None:
    if result is None:
        return None
    action = result.action
    suggestion = result.ai_suggestion or {}
    return {
        "photo_id": result.photo_id,
        "grand_score": result.grand_score,
        "action_level": result.action_level,
        "description": action.description,
        "risk": presenters.risk_data(result.grand_score),
        "partial_scores": result.partial_scores,
        "method": result.method,
        "ai_trace": {
            "on_other_photo": result.ai_on_other_photo,
            "frontal": bool(suggestion.get("frontal")),
            "rows": [{**row, "label": str(row["label"]), "suggested": number(row["suggested"]), "registered": number(row["registered"])}
                     for row in result.ai_comparison],
        } if suggestion.get("angles") else None,
    }


def posture_data(posture) -> dict:
    return {
        "id": posture.pk,
        "name": posture.name,
        "side": posture.side,
        "side_label": posture.get_side_display(),
        "duration_value": number(posture.duration_value),
        "duration_unit": posture.duration_unit,
        "duration_unit_label": posture.get_duration_unit_display(),
        "photos": [{"id": p.pk, "url": photo_url(p.pk), "width": p.width, "height": p.height} for p in posture.photos.all()],
        "result": result_data(posture.result),
        "recommendations": [
            {"id": r.pk, "text": r.text, "attended": r.attended_at is not None} for r in posture.recommendations.all()
        ],
    }


def row(evaluation) -> dict:
    return {**presenters.evaluation_data(evaluation), "company_id": evaluation.company.pk}


def detail(evaluation, user) -> dict:
    can_edit = (
        evaluation.is_draft and evaluation.evaluator_id == user.pk and has_capability(user, Capability.EVALUATION_MANAGE)
    )
    position = evaluation.position
    company = position.area.site.company
    worker = evaluation.worker
    return {
        **row(evaluation),
        "company": company.name,
        "company_nit": company.nit_display,
        "site": position.area.site.name,
        "evaluator": str(evaluation.evaluator),
        "visit": {"id": evaluation.visit_id, "date": presenters.iso(timezone.localdate(evaluation.visit.scheduled_at))},
        "visit_id": evaluation.visit_id,
        "area_id": position.area_id,
        "position_id": position.pk,
        "worker": {"id": worker.pk, "full_name": worker.full_name} if worker else None,
        "activity_description": evaluation.activity_description,
        "worker_context": evaluation.worker_context,
        "carries_load": evaluation.carries_load,
        "load_weight_kg": number(evaluation.load_weight_kg),
        "repetitive_movements": evaluation.repetitive_movements,
        "repetition_notes": evaluation.repetition_notes,
        "completed_at": presenters.iso(evaluation.completed_at),
        "postures": [posture_data(p) for p in evaluation.postures.all()],
        "can_edit": can_edit,
        "can_reopen": not evaluation.is_draft and has_capability(user, Capability.EVALUATION_REOPEN),
        "completion_problems": services.completion_problems(evaluation) if can_edit else [],
        "posture_options": {
            "sides": choices(Posture.Side.choices),
            "units": choices(Posture.DurationUnit.choices),
        },
    }


def load_detail(user, pk, **filters) -> Evaluation:
    return get_object_or_404(selectors.with_details(selectors.visible_evaluations(user).filter(**filters)), pk=pk)


class EvaluationListView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]

    def get_permissions(self):
        self.required_capabilities = MANAGE if self.request.method == "POST" else VIEW
        return super().get_permissions()

    def get(self, request):
        evaluations = selectors.search_evaluations(request.user, request.query_params.get("q", ""))
        return Response(paginate(request, evaluations, row, per_page=15))

    def post(self, request):
        form = EvaluationForm(data=request.data, user=request.user)
        return save_form(form, lambda e: {"id": e.pk}, integrity_message="No se pudo guardar. Intenta de nuevo.", created=True)


class EvaluationOptionsView(APIView):
    """Listas dependientes del formulario: visita > área > puesto > trabajador.

    Se calculan con el mismo formulario, así que solo aparecen visitas realizadas y lo que
    corresponde a la sede visitada.
    """

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def get(self, request):
        params = {k: request.query_params.get(k) for k in ("visit", "area", "position") if request.query_params.get(k)}
        instance = None
        if request.query_params.get("evaluation"):
            instance = get_object_or_404(selectors.editable_evaluations(request.user), pk=request.query_params["evaluation"])
        form = EvaluationForm(initial=params, user=request.user, instance=instance)
        disabled = lambda name: bool(form.fields[name].widget.attrs.get("disabled"))  # noqa: E731
        options = lambda name: [] if disabled(name) else [  # noqa: E731
            {"value": str(item.pk), "label": form.fields[name].label_from_instance(item)} for item in form.fields[name].queryset
        ]
        return Response({
            "visits": options("visit"),
            "areas": options("area"),
            "positions": options("position"),
            "workers": options("worker"),
            "area_hint": str(form.fields["area"].help_text or ""),
            "evaluated_on": presenters.iso(form.initial.get("evaluated_on")),
        })


class EvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]

    def get_permissions(self):
        self.required_capabilities = VIEW if self.request.method == "GET" else MANAGE
        return super().get_permissions()

    def get(self, request, pk):
        return Response(detail(load_detail(request.user, pk), request.user))

    def put(self, request, pk):
        evaluation = get_object_or_404(selectors.editable_evaluations(request.user), pk=pk)
        form = EvaluationForm(data=request.data, instance=evaluation, user=request.user)
        return save_form(form, lambda e: {"id": e.pk}, integrity_message="No se pudo guardar. Intenta de nuevo.")


class EvaluationCompleteView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def post(self, request, pk):
        evaluation = get_object_or_404(selectors.with_details(selectors.editable_evaluations(request.user)), pk=pk)
        try:
            services.complete_evaluation(evaluation)
        except services.EvaluationIncomplete as error:
            return error_response("conflict", str(error), status.HTTP_409_CONFLICT, {"__all__": error.problems})
        return Response(detail(load_detail(request.user, pk), request.user))


class EvaluationReopenView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.EVALUATION_REOPEN,)

    def post(self, request, pk):
        evaluation = get_object_or_404(selectors.visible_evaluations(request.user), pk=pk)
        services.reopen_evaluation(evaluation)
        return Response(detail(load_detail(request.user, pk), request.user))


class PostureView(APIView):
    """POST crea una postura en la evaluación; PUT la edita; DELETE la elimina con todo lo suyo."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def post(self, request, pk):
        evaluation = get_object_or_404(selectors.editable_evaluations(request.user), pk=pk)
        form = PostureForm(data=request.data, evaluation=evaluation)
        return save_form(form, lambda p: {"id": p.pk}, integrity_message=DUPLICATE_POSTURE, created=True)

    def put(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user), pk=pk)
        return save_form(PostureForm(data=request.data, instance=posture), lambda p: {"id": p.pk}, integrity_message=DUPLICATE_POSTURE)

    def delete(self, request, pk):
        get_object_or_404(selectors.editable_postures(request.user), pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PhotoUploadView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE
    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user), pk=pk)
        uploaded = request.FILES.get("photo")
        if uploaded is None:
            return error_response("validation_error", "Elige una fotografía.", status.HTTP_400_BAD_REQUEST, {"photo": ["Elige una fotografía."]})
        try:
            photo = services.add_photo(posture, uploaded)
        except InvalidPhoto as error:
            return error_response("validation_error", str(error), status.HTTP_400_BAD_REQUEST, {"photo": [str(error)]})
        return Response({"id": photo.pk, "url": photo_url(photo.pk)}, status=status.HTTP_201_CREATED)


class PhotoView(APIView):
    """GET entrega la imagen solo a quien puede ver la evaluación; DELETE la elimina si se puede."""

    permission_classes = [IsAuthenticated, HasCapability]

    def get_permissions(self):
        self.required_capabilities = VIEW if self.request.method == "GET" else MANAGE
        return super().get_permissions()

    def get(self, request, pk):
        photo = get_object_or_404(
            PosturePhoto.objects.filter(posture__evaluation__in=selectors.visible_evaluations(request.user).values("pk")), pk=pk
        )
        response = HttpResponse(bytes(photo.data), content_type=photo.content_type)
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def delete(self, request, pk):
        photo = get_object_or_404(
            PosturePhoto.objects.defer("data").filter(posture__in=selectors.editable_postures(request.user)), pk=pk
        )
        try:
            with transaction.atomic():
                photo.delete()
        except RestrictedError:
            return error_response(
                "conflict", "Esta fotografía sustenta el análisis. Elige otra en el análisis antes de eliminarla.",
                status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


def field_spec(bound) -> dict:
    field = bound.field
    widget = field.widget.__class__.__name__
    kind = "checkbox" if widget == "CheckboxInput" else "select" if widget == "Select" else "number"
    spec = {"name": bound.name, "label": str(field.label), "type": kind, "help": str(field.help_text or "")}
    if kind == "select":
        spec["choices"] = choices(field.choices)
    return spec


def assessment_values(form) -> dict:
    values = {}
    for name in form.fields:
        if name in ("photo", "ai_suggestion"):
            continue
        value = form[name].value()
        values[name] = number(value) if name in RulaAssessment.ANGLE_FIELDS and value not in (None, "") else value
    return values


class AssessmentView(APIView):
    """GET: lo necesario para el análisis (fotos, campos y valores). PUT: calcula y guarda."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def context(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user), pk=pk)
        photos = selectors.posture_photos(posture)
        if not photos.exists():
            return posture, photos, error_response(
                "conflict", "Agrega una fotografía antes de hacer el análisis.", status.HTTP_409_CONFLICT
            )
        return posture, photos, None

    def get(self, request, pk):
        posture, photos, problem = self.context(request, pk)
        if problem:
            return problem
        assessment = RulaAssessment.objects.filter(posture=posture).first()
        form = RulaAssessmentForm(instance=assessment, posture=posture, photos=photos,
                                  initial={} if assessment else {"photo": photos.first()})
        photo = form["photo"].value()
        return Response({
            "evaluation_id": posture.evaluation_id,
            "posture": {"id": posture.pk, "name": posture.name, "side": posture.side, "side_label": posture.get_side_display()},
            "photos": [{"id": p.pk, "url": photo_url(p.pk)} for p in photos],
            "photo": photo.pk if hasattr(photo, "pk") else (int(photo) if photo else None),
            "groups": [{"title": title, "fields": [field_spec(form[name]) for name in names]} for title, names in form.GROUPS],
            "values": assessment_values(form),
            "has_result": assessment is not None,
            "action_levels": [{"level": a.level, "min": a.min_score, "max": a.max_score, "description": a.description} for a in ACTION_LEVELS],
        })

    def put(self, request, pk):
        posture, photos, problem = self.context(request, pk)
        if problem:
            return problem
        assessment = RulaAssessment.objects.filter(posture=posture).first()
        data = dict(request.data)
        # La sugerencia de la IA llega como objeto; el formulario la espera como texto JSON.
        if isinstance(data.get("ai_suggestion"), dict):
            data["ai_suggestion"] = json.dumps(data["ai_suggestion"])
        form = RulaAssessmentForm(data=data, instance=assessment, posture=posture, photos=photos)
        if not form.is_valid():
            return invalid(form)
        try:
            with transaction.atomic():
                saved = form.save()
        except IntegrityError:
            form.add_error(None, "Otra sesión guardó este análisis. Recarga la página.")
            return invalid(form)
        return Response({"evaluation_id": posture.evaluation_id, "result": result_data(saved)})


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def post(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user).select_related("assessment"), pk=pk)
        # Se escribe después de ver el resultado (D5).
        if posture.result is None:
            return error_response("conflict", "Primero haz el análisis RULA de esta postura.", status.HTTP_409_CONFLICT)
        form = RecommendationForm(data=request.data)
        if not form.is_valid():
            return invalid(form)
        form.instance.posture = posture
        form.instance.author = request.user
        recommendation = form.save()
        return Response({"id": recommendation.pk, "text": recommendation.text, "attended": False}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        recommendation = get_object_or_404(
            Recommendation.objects.filter(posture__in=selectors.editable_postures(request.user)), pk=pk
        )
        recommendation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

