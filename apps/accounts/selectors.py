from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet

from .models import Role
from .permissions import Capability, has_capability


def users_by_role() -> list[dict]:
    counts = dict(
        get_user_model()
        .objects.filter(is_active=True)
        .order_by()
        .values_list("role")
        .annotate(total=Count("pk"))
    )
    return [{"role": role.value, "label": role.label, "total": counts.get(role.value, 0)} for role in Role]


def manageable_users(actor) -> QuerySet:
    """Cuentas que el usuario puede ver y administrar.

    Soporte gestiona todas. El ingeniero solo las de las empresas cliente: nunca la suya
    ni las de soporte, para que no pueda darse permisos que no tiene.
    """
    users = get_user_model().objects.select_related("company", "created_by")
    if has_capability(actor, Capability.USER_MANAGE):
        return users
    if has_capability(actor, Capability.COMPANY_USER_MANAGE):
        return users.filter(role=Role.COMPANY)
    return users.none()


def search_users(actor, query: str = "", role: str = "") -> QuerySet:
    users = manageable_users(actor).order_by("-is_active", "role", "email")
    if role in Role.values:
        users = users.filter(role=role)
    query = query.strip()
    if query:
        users = users.filter(
            Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(company__name__icontains=query)
        )
    return users


def company_accounts(company) -> QuerySet:
    return get_user_model().objects.filter(company=company).order_by("-is_active", "email")


def is_last_active_admin(user) -> bool:
    if user.role != Role.ADMIN or not user.is_active:
        return False
    return not get_user_model().objects.filter(role=Role.ADMIN, is_active=True).exclude(pk=user.pk).exists()
