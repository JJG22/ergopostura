"""Consultas de lectura. Todo acceso a datos pasa por el alcance del usuario.

Si una empresa esta fuera del alcance, la consulta no la encuentra y la vista
responde 404. Asi no se puede ver otra empresa cambiando el numero en la URL.
"""
import re

from django.db.models import Count, Prefetch, Q, QuerySet

from apps.accounts.permissions import Capability, has_capability

from .models import Area, Company, Position, Site, Worker


def visible_companies(user) -> QuerySet[Company]:
    if has_capability(user, Capability.COMPANY_VIEW_ALL):
        return Company.objects.all()
    if has_capability(user, Capability.COMPANY_VIEW_OWN) and user.company_id:
        return Company.objects.filter(pk=user.company_id)
    return Company.objects.none()


def visible_sites(user) -> QuerySet[Site]:
    return Site.objects.filter(company__in=visible_companies(user)).select_related("company")


def visible_areas(user) -> QuerySet[Area]:
    return Area.objects.filter(site__company__in=visible_companies(user)).select_related("site__company")


def visible_positions(user) -> QuerySet[Position]:
    return Position.objects.filter(
        area__site__company__in=visible_companies(user)
    ).select_related("area__site__company")


def visible_workers(user) -> QuerySet[Worker]:
    return Worker.objects.filter(
        position__area__site__company__in=visible_companies(user)
    ).select_related("position__area__site__company")


def search_companies(user, query: str = "") -> QuerySet[Company]:
    # Django ignora Meta.ordering al agrupar: sin este orden la paginacion seria inestable.
    companies = (
        visible_companies(user)
        .select_related("municipality__department")
        .annotate(site_count=Count("sites"))
        .order_by("name", "pk")
    )
    query = query.strip()
    if not query:
        return companies

    condition = Q(name__icontains=query)
    # Lo que va despues del guion es el digito de verificacion, que no se almacena.
    digits = re.sub(r"\D", "", query.split("-")[0])
    if digits:
        condition |= Q(nit__contains=digits)
    return companies.filter(condition)


def with_structure(companies: QuerySet[Company]) -> QuerySet[Company]:
    sites = Site.objects.select_related("municipality__department")
    return companies.select_related("municipality__department").prefetch_related(
        Prefetch("sites", queryset=sites), "sites__areas__positions__workers"
    )


def structure_totals(user) -> dict[str, int]:
    companies = visible_companies(user)
    return {
        "companies": companies.count(),
        "sites": Site.objects.filter(company__in=companies).count(),
        "areas": Area.objects.filter(site__company__in=companies).count(),
        "positions": Position.objects.filter(area__site__company__in=companies).count(),
    }
