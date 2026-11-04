from apps.companies.models import Area
from apps.evaluations.models import Evaluation
from apps.evaluations.selectors import visible_evaluations

from .metrics import EvaluationRow, latest_per_position


def evaluated_rows(user) -> list[EvaluationRow]:
    """Una fila por puesto, limitada a las evaluaciones que el usuario puede ver."""
    rows = (
        visible_evaluations(user)
        .filter(status=Evaluation.Status.COMPLETED, worst_score__isnull=False)
        .values(
            "position_id",
            "position__area_id",
            "position__area__site__company_id",
            "position__area__site__company__name",
            "worst_score",
        )
    )
    return latest_per_position(
        [
            EvaluationRow(
                position_id=row["position_id"],
                area_id=row["position__area_id"],
                company_id=row["position__area__site__company_id"],
                company_name=row["position__area__site__company__name"],
                worst_score=row["worst_score"],
            )
            for row in rows
        ]
    )


def company_areas(company_id: int):
    return Area.objects.filter(site__company_id=company_id).select_related("site").order_by("site__name", "name")
