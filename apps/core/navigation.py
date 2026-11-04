"""Menu lateral. Un modulo nuevo se agrega con una entrada, sin tocar las plantillas."""
from dataclasses import dataclass

from django.urls import reverse

from apps.accounts.permissions import Capability, capabilities_of


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    icon: str
    namespace: str
    # Basta con una de estas capacidades. Vacio significa cualquier usuario con sesion.
    capabilities: tuple[Capability, ...] = ()


NAV_ITEMS = (
    NavItem("Panel principal", "dashboard:home", "house", "dashboard"),
    NavItem("Empresas", "companies:list", "building-complex", "companies", (Capability.COMPANY_VIEW_ALL,)),
    NavItem(
        "Visitas", "visits:list", "calendar-days", "visits",
        (Capability.VISIT_VIEW_ALL, Capability.VISIT_VIEW_OWN),
    ),
    NavItem(
        "Evaluaciones", "evaluations:list", "clipboard-check", "evaluations",
        (
            Capability.EVALUATION_VIEW_ALL,
            Capability.EVALUATION_VIEW_COMPLETED,
            Capability.EVALUATION_VIEW_OWN,
        ),
    ),
    NavItem("Usuarios","admin:accounts_user_changelist", "users", "admin", (Capability.USER_MANAGE,)),
)


def items_for(user, current_namespace: str | None) -> list[dict]:
    capabilities = capabilities_of(user)
    return [
        {
            "label": item.label,
            "url": reverse(item.url_name),
            "icon": item.icon,
            "active": item.namespace == current_namespace,
        }
        for item in NAV_ITEMS
        if not item.capabilities or capabilities.intersection(item.capabilities)
    ]
