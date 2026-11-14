"""Menu lateral por capacidades. El cliente React lo recibe en la sesion (apps.api.presenters)."""
from dataclasses import dataclass

from apps.accounts.permissions import Capability


@dataclass(frozen=True)
class NavItem:
    label: str
    # Ruta de la pantalla en el cliente React.
    route: str
    icon: str
    namespace: str
    # Basta con una de estas capacidades. Vacio significa cualquier usuario con sesion.
    capabilities: tuple[Capability, ...] = ()


NAV_ITEMS = (
    NavItem("Panel principal", "/", "house", "dashboard"),
    NavItem("Usuarios", "/usuarios", "users", "accounts", (Capability.USER_MANAGE,)),
    NavItem("Empresas", "/empresas", "building-complex", "companies", (Capability.COMPANY_VIEW_ALL,)),
    NavItem("Contratos", "/contratos", "file-signature", "contracts", (Capability.CONTRACT_MANAGE,)),
    NavItem(
        "Visitas", "/visitas", "calendar-days", "visits",
        (Capability.VISIT_VIEW_ALL, Capability.VISIT_VIEW_OWN),
    ),
    NavItem(
        "Evaluaciones", "/evaluaciones", "clipboard-check", "evaluations",
        (Capability.EVALUATION_VIEW_ALL, Capability.EVALUATION_VIEW_OWN),
    ),
    NavItem("Indicadores", "/indicadores", "chart-column", "indicators", (Capability.INDICATORS_VIEW,)),
    NavItem(
        "Tareas pendientes", "/tareas", "layout-list", "tasks",
        (Capability.TASK_VIEW_ALL, Capability.TASK_VIEW_OWN, Capability.EVALUATION_MANAGE),
    ),
    NavItem("Accesos de empresas", "/usuarios", "key-round", "accounts", (Capability.COMPANY_USER_MANAGE,)),
)
