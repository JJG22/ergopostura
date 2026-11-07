from datetime import timedelta

from django.db.models import Count, QuerySet
from django.utils import timezone

from apps.accounts.permissions import Capability, has_capability

from .models import Visit
from .rules import MAX_DURATION


def visible_visits(user) -> QuerySet[Visit]:
    visits = Visit.objects.select_related("site__company", "site__municipality")
    if has_capability(user, Capability.VISIT_VIEW_ALL):
        return visits
    if has_capability(user, Capability.VISIT_VIEW_OWN) and user.company_id:
        return visits.filter(site__company_id=user.company_id)
    return visits.none()


def upcoming_visits(user) -> QuerySet[Visit]:
    """Programadas que no han terminado: incluye la que esta en curso."""
    now = timezone.now()
    return visible_visits(user).filter(
        status=Visit.Status.SCHEDULED, scheduled_at__gte=now - timedelta(minutes=MAX_DURATION)
    ).order_by("scheduled_at", "pk")


def visits_to_close(user) -> list[Visit]:
    """Programadas cuya hora ya paso: el ingeniero debe registrar si se hicieron."""
    now = timezone.now()
    candidates = visible_visits(user).filter(status=Visit.Status.SCHEDULED, scheduled_at__lt=now)
    return [visit for visit in candidates.order_by("scheduled_at") if visit.ends_at <= now]


def past_visits(user) -> QuerySet[Visit]:
    return visible_visits(user).exclude(status=Visit.Status.SCHEDULED).order_by("-scheduled_at", "-pk")


def completed_without_evaluation(user) -> QuerySet[Visit]:
    return (
        visible_visits(user)
        .filter(status=Visit.Status.COMPLETED)
        .annotate(evaluation_count=Count("evaluations"))
        .filter(evaluation_count=0)
        .order_by("-scheduled_at")
    )


def visits_between(user, start, end) -> QuerySet[Visit]:
    return visible_visits(user).filter(scheduled_at__gte=start, scheduled_at__lt=end).order_by("scheduled_at", "pk")


def busy_between(user, start, end) -> list[tuple]:
    """Horarios ocupados por visitas de otras empresas, sin ningun dato de ellas."""
    if has_capability(user, Capability.VISIT_VIEW_ALL) or not user.company_id:
        return []
    return list(
        Visit.objects.exclude(status=Visit.Status.CANCELLED)
        .exclude(site__company_id=user.company_id)
        .filter(scheduled_at__gte=start, scheduled_at__lt=end)
        .values_list("scheduled_at", "duration_minutes")
    )
