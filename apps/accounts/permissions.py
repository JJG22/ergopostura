"""Politica de acceso: que puede hacer cada rol, en un solo lugar.

Las vistas preguntan por capacidades, nunca por roles. Cambiar lo que puede
hacer un rol o agregar uno nuevo solo requiere modificar ROLE_CAPABILITIES.
"""
from enum import StrEnum

from .models import Role


class Capability(StrEnum):
    # Cuentas: soporte gestiona todas; el ingeniero, las de sus empresas cliente.
    USER_MANAGE = "user.manage"
    COMPANY_USER_MANAGE = "company_user.manage"

    COMPANY_VIEW_ALL = "company.view_all"
    COMPANY_VIEW_OWN = "company.view_own"
    # Empresas, sedes, areas, puestos y trabajadores.
    COMPANY_MANAGE = "company.manage"

    CONTRACT_MANAGE = "contract.manage"
    CONTRACT_VIEW_OWN = "contract.view_own"

    VISIT_VIEW_ALL = "visit.view_all"
    VISIT_VIEW_OWN = "visit.view_own"
    # Agendar, reprogramar o cancelar: lo hace la empresa que recibe la visita.
    VISIT_SCHEDULE = "visit.schedule"
    # Registrar si la visita se hizo, o cancelarla: lo hace el ingeniero.
    VISIT_ATTEND = "visit.attend"

    EVALUATION_VIEW_ALL = "evaluation.view_all"
    # Solo evaluaciones terminadas de la propia empresa.
    EVALUATION_VIEW_OWN = "evaluation.view_own"
    EVALUATION_MANAGE = "evaluation.manage"
    EVALUATION_REOPEN = "evaluation.reopen"

    # El alcance de los datos lo siguen dando las evaluaciones que el usuario puede ver.
    INDICATORS_VIEW = "indicators.view"
    # Recomendaciones de evaluaciones terminadas por atender.
    TASK_VIEW_ALL = "task.view_all"
    TASK_VIEW_OWN = "task.view_own"
    TASK_ATTEND = "task.attend"


ROLE_CAPABILITIES: dict[str, frozenset[Capability]] = {
    # Soporte mantiene el sistema: no ve datos de las empresas ni hace trabajo tecnico.
    Role.ADMIN: frozenset({Capability.USER_MANAGE}),
    Role.ENGINEER: frozenset(
        {
            Capability.COMPANY_USER_MANAGE,
            Capability.COMPANY_VIEW_ALL,
            Capability.COMPANY_MANAGE,
            Capability.CONTRACT_MANAGE,
            Capability.VISIT_VIEW_ALL,
            Capability.VISIT_ATTEND,
            Capability.EVALUATION_VIEW_ALL,
            Capability.EVALUATION_MANAGE,
            Capability.EVALUATION_REOPEN,
            Capability.INDICATORS_VIEW,
            Capability.TASK_VIEW_ALL,
        }
    ),
    Role.COMPANY: frozenset(
        {
            Capability.COMPANY_VIEW_OWN,
            Capability.CONTRACT_VIEW_OWN,
            Capability.VISIT_VIEW_OWN,
            Capability.VISIT_SCHEDULE,
            Capability.EVALUATION_VIEW_OWN,
            Capability.INDICATORS_VIEW,
            Capability.TASK_VIEW_OWN,
            Capability.TASK_ATTEND,
        }
    ),
}


def capabilities_of(user) -> frozenset[Capability]:
    if not user.is_authenticated or not user.is_active:
        return frozenset()
    return ROLE_CAPABILITIES.get(user.role, frozenset())


def has_capability(user, capability: Capability) -> bool:
    return capability in capabilities_of(user)
