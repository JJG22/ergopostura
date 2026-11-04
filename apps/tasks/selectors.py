"""Tareas del proceso (RF-029, decision D8). Se derivan de los datos: no hay tareas aparte.

- Evaluaciones en curso: tarea del profesional que las creo.
- Recomendaciones de evaluaciones terminadas: tarea de quien debe atenderlas.
"""
from django.db.models import Q, QuerySet

from apps.accounts.permissions import Capability, has_capability
from apps.evaluations import selectors as evaluation_selectors
from apps.evaluations.models import Evaluation, Recommendation
from apps.evaluations.services import completion_problems


def recommendations_for(user) -> QuerySet[Recommendation]:
    recommendations = Recommendation.objects.select_related(
        "posture__assessment",
        "posture__evaluation__position__area__site__company",
        "attended_by",
    ).filter(posture__evaluation__status=Evaluation.Status.COMPLETED)
    if has_capability(user, Capability.TASK_VIEW_ALL):
        return recommendations
    if has_capability(user, Capability.TASK_VIEW_OWN) and user.company_id:
        return recommendations.filter(posture__evaluation__position__area__site__company_id=user.company_id)
    return recommendations.none()


def pending_recommendations(user, query: str = "") -> QuerySet[Recommendation]:
    # Primero lo de mayor riesgo; a igual riesgo, lo mas antiguo.
    return _search(recommendations_for(user).filter(attended_at__isnull=True), query).order_by(
        "-posture__assessment__grand_score", "pk"
    )


def attended_recommendations(user, query: str = "") -> QuerySet[Recommendation]:
    return _search(recommendations_for(user).filter(attended_at__isnull=False), query).order_by("-attended_at", "-pk")


def _search(recommendations: QuerySet[Recommendation], query: str) -> QuerySet[Recommendation]:
    query = query.strip()
    if not query:
        return recommendations
    return recommendations.filter(
        Q(text__icontains=query)
        | Q(posture__evaluation__position__name__icontains=query)
        | Q(posture__evaluation__position__area__site__company__name__icontains=query)
    )


def evaluations_in_progress(user) -> list[dict]:
    evaluations = evaluation_selectors.with_details(evaluation_selectors.editable_evaluations(user))
    return [
        {"evaluation": evaluation, "problems": completion_problems(evaluation)}
        for evaluation in evaluations.order_by("evaluated_on", "pk")
    ]
