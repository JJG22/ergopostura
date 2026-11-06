from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.permissions import Capability, has_capability

from .models import Visit


def visible_visits(user) -> QuerySet[Visit]:
    visits = Visit.objects.select_related("position__area__site__company")
    if has_capability(user, Capability.VISIT_VIEW_ALL):
        return visits
    if has_capability(user, Capability.VISIT_VIEW_OWN) and user.company_id:
        return visits.filter(position__area__site__company_id=user.company_id)
    return visits.none()


def upcoming_visits(user) -> QuerySet[Visit]:
    return visible_visits(user).filter(scheduled_at__gte=timezone.now())


def past_visits(user) -> QuerySet[Visit]:
    return visible_visits(user).filter(scheduled_at__lt=timezone.now()).order_by("-scheduled_at", "-pk")


def visits_between(user, start, end) -> QuerySet[Visit]:
    return visible_visits(user).filter(scheduled_at__gte=start, scheduled_at__lt=end).order_by("scheduled_at", "pk")
