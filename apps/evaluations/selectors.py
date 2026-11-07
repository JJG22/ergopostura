"""Consultas de lectura, siempre limitadas a lo que el usuario puede ver o modificar."""
import re

from django.db.models import Max, Prefetch, Q, QuerySet

from apps.accounts.permissions import Capability, has_capability

from .models import Evaluation, Posture, PosturePhoto, Recommendation


def visible_evaluations(user) -> QuerySet[Evaluation]:
    evaluations = (
        Evaluation.objects.select_related("position__area__site__company", "evaluator", "visit", "worker")
        # Una evaluacion muestra su peor postura. Nunca se promedian puntajes (RF-019).
        .annotate(worst_score=Max("postures__assessment__grand_score"))
        .order_by("-evaluated_on", "-pk")
    )
    if has_capability(user, Capability.EVALUATION_VIEW_ALL):
        return evaluations
    if has_capability(user, Capability.EVALUATION_VIEW_OWN) and user.company_id:
        # La empresa ve solo resultados definitivos, nunca una evaluacion en curso.
        return evaluations.filter(status=Evaluation.Status.COMPLETED).filter(position__area__site__company_id=user.company_id)
    return evaluations.none()


def editable_evaluations(user) -> QuerySet[Evaluation]:
    """Cada profesional modifica solo sus evaluaciones, y solo mientras esten en curso."""
    if not has_capability(user, Capability.EVALUATION_MANAGE):
        return Evaluation.objects.none()
    return Evaluation.objects.select_related("position__area__site__company").filter(
        evaluator=user, status=Evaluation.Status.DRAFT
    )


def editable_postures(user) -> QuerySet[Posture]:
    return Posture.objects.select_related("evaluation__position__area__site__company").filter(
        evaluation__in=editable_evaluations(user)
    )


def _photos_without_data() -> QuerySet[PosturePhoto]:
    # Los bytes de cada imagen se piden aparte: traerlos aqui llenaria la memoria.
    return PosturePhoto.objects.defer("data")


def with_details(evaluations: QuerySet[Evaluation]) -> QuerySet[Evaluation]:
    postures = Posture.objects.select_related("assessment").prefetch_related(
        Prefetch("photos", _photos_without_data()),
        Prefetch("recommendations", Recommendation.objects.select_related("author")),
    )
    return evaluations.prefetch_related(Prefetch("postures", postures))


def posture_photos(posture: Posture) -> QuerySet[PosturePhoto]:
    return _photos_without_data().filter(posture=posture)


def search_evaluations(user, query: str = "") -> QuerySet[Evaluation]:
    evaluations = visible_evaluations(user)
    query = query.strip()
    if not query:
        return evaluations
    condition = (
        Q(position__name__icontains=query)
        | Q(position__area__name__icontains=query)
        | Q(position__area__site__company__name__icontains=query)
    )
    code = re.fullmatch(r"(?:EV-?)?0*(\d+)", query, re.IGNORECASE)
    if code:
        condition |= Q(pk=int(code.group(1)))
    return evaluations.filter(condition)
