"""Indicadores de riesgo y tareas pendientes.

Indicadores: un puesto cuenta una vez (su evaluación terminada más reciente, por su postura de
mayor riesgo). Tareas: evaluaciones en curso del ingeniero y recomendaciones por atender. Las
reglas son las de apps.indicators y apps.tasks; aquí solo se entregan en JSON.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import Capability, capabilities_of, has_capability
from apps.indicators import selectors as indicator_selectors
from apps.indicators.metrics import distribution
from apps.tasks import selectors as task_selectors

from . import presenters
from .common import paginate
from .permissions import HasCapability


def risk(rows) -> dict:
    result = distribution(rows)
    return {
        "green": result.green, "yellow": result.yellow, "red": result.red, "total": result.total,
        "follow_up": result.follow_up, "follow_up_percent": result.follow_up_percent,
    }


class IndicatorsView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.INDICATORS_VIEW,)

    def get(self, request):
        user = request.user
        rows = indicator_selectors.evaluated_rows(user)
        companies = {row.company_id: row.company_name for row in rows}
        # Quien no ve las evaluaciones de todas las empresas ve solo la suya.
        limited = not has_capability(user, Capability.EVALUATION_VIEW_ALL)
        if limited:
            selected = user.company_id
        else:
            value = request.query_params.get("company", "")
            # Solo se aceptan empresas presentes en los datos que el usuario ya puede ver.
            selected = int(value) if value.isdigit() and int(value) in companies else None

        data = {
            "totals": risk(rows),
            "company_count": len(companies),
            "area_count": len({row.area_id for row in rows}),
            "shows_all_companies": not limited,
            "selected_company": {"id": selected, "name": companies.get(selected, "")} if selected is not None else None,
            "companies": [
                {"id": pk, "label": name, "risk": risk([r for r in rows if r.company_id == pk])}
                for pk, name in sorted(companies.items(), key=lambda item: item[1].casefold())
            ] if not limited else [],
            "areas": None,
        }
        if selected is not None:
            data["areas"] = [
                {"id": None, "label": f"{area.site.name} · {area.name}", "risk": risk([r for r in rows if r.area_id == area.pk])}
                for area in indicator_selectors.company_areas(selected)
            ]
        return Response(data)


def recommendation_data(recommendation, can_open: bool) -> dict:
    posture = recommendation.posture
    evaluation = posture.evaluation
    assessment = getattr(posture, "assessment", None)
    return {
        "id": recommendation.pk,
        "text": recommendation.text,
        "posture": posture.name,
        "company": evaluation.position.area.site.company.name,
        "position": evaluation.position.name,
        "evaluation": {"id": evaluation.pk, "code": evaluation.code} if can_open else {"id": None, "code": evaluation.code},
        "risk": presenters.risk_data(assessment.grand_score if assessment else None),
        "attended_at": presenters.iso(recommendation.attended_at),
        "attended_by": str(recommendation.attended_by) if recommendation.attended_by else None,
    }


class TasksView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.TASK_VIEW_ALL, Capability.TASK_VIEW_OWN, Capability.EVALUATION_MANAGE)

    def get(self, request):
        user = request.user
        capabilities = capabilities_of(user)
        attended = request.query_params.get("view") == "atendidas"
        query = request.query_params.get("q", "").strip()
        shows_recommendations = bool(capabilities & {Capability.TASK_VIEW_ALL, Capability.TASK_VIEW_OWN})
        # El responsable de tarea atiende recomendaciones sin acceder a la evidencia.
        can_open = bool(capabilities & {Capability.EVALUATION_VIEW_ALL, Capability.EVALUATION_VIEW_OWN})
        select = task_selectors.attended_recommendations if attended else task_selectors.pending_recommendations
        data = paginate(request, select(user, query), lambda r: recommendation_data(r, can_open), per_page=15) \
            if shows_recommendations else {"results": [], "count": 0, "page": 1, "pages": 1}
        data.update(
            view="atendidas" if attended else "pendientes",
            shows_recommendations=shows_recommendations,
            can_attend=Capability.TASK_ATTEND in capabilities,
            manages_evaluations=Capability.EVALUATION_MANAGE in capabilities,
            in_progress=[
                {
                    "id": item["evaluation"].pk,
                    "code": item["evaluation"].code,
                    "company": item["evaluation"].company.name,
                    "position": item["evaluation"].position.name,
                    "problems": item["problems"],
                }
                for item in task_selectors.evaluations_in_progress(user)
            ] if Capability.EVALUATION_MANAGE in capabilities else [],
        )
        return Response(data)


class AttendView(APIView):
    """Body: {"attended": bool}. Cambiar el estado no altera el resultado de la evaluación."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.TASK_ATTEND,)

    def post(self, request, pk):
        recommendation = get_object_or_404(task_selectors.recommendations_for(request.user), pk=pk)
        attended = request.data.get("attended") is True
        recommendation.attended_at = timezone.now() if attended else None
        recommendation.attended_by = request.user if attended else None
        recommendation.save(update_fields=["attended_at", "attended_by", "updated_at"])
        return Response(recommendation_data(recommendation, True))
