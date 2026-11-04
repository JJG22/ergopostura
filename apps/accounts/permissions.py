"""Politica de acceso: que puede hacer cada rol, en un solo lugar.

Las vistas preguntan por capacidades, nunca por roles. Cambiar lo que puede
hacer un rol o agregar uno nuevo solo requiere modificar ROLE_CAPABILITIES.
"""
from enum import StrEnum

from .models import Role


class Capability(StrEnum):
    COMPANY_VIEW_ALL = "company.view_all"
    COMPANY_VIEW_OWN = "company.view_own"
    COMPANY_MANAGE = "company.manage"
    USER_MANAGE = "user.manage"
    VISIT_VIEW_ALL = "visit.view_all"
    VISIT_VIEW_OWN = "visit.view_own"
    VISIT_MANAGE = "visit.manage"
    # Evaluaciones en cualquier estado.
    EVALUATION_VIEW_ALL = "evaluation.view_all"
    # Solo evaluaciones terminadas: de todas las empresas o de la propia.
    EVALUATION_VIEW_COMPLETED = "evaluation.view_completed"
    EVALUATION_VIEW_OWN = "evaluation.view_own"
    # Aplicar RULA: lo hacen el ingeniero industrial y el evaluador.
    EVALUATION_MANAGE = "evaluation.manage"
    EVALUATION_REOPEN = "evaluation.reopen"
    # El alcance de los datos lo siguen dando las evaluaciones que el usuario puede ver.
    INDICATORS_VIEW = "indicators.view"
    # Recomendaciones de evaluaciones terminadas por atender.
    TASK_VIEW_ALL = "task.view_all"
    TASK_VIEW_OWN = "task.view_own"
    TASK_ATTEND = "task.attend"


ROLE_CAPABILITIES: dict[str, frozenset[Capability]] = {
    Role.ADMIN: frozenset(Capability) - {Capability.EVALUATION_MANAGE},
    Role.ENGINEER: frozenset(
        {
            Capability.COMPANY_VIEW_ALL,
            Capability.COMPANY_MANAGE,
            Capability.VISIT_VIEW_ALL,
            Capability.EVALUATION_VIEW_ALL,
            Capability.EVALUATION_MANAGE,
            Capability.INDICATORS_VIEW,
        }
    ),
    # RF-006: la empresa registra sus visitas acordadas.
    Role.COMPANY: frozenset(
        {
            Capability.COMPANY_VIEW_OWN,
            Capability.VISIT_VIEW_OWN,
            Capability.VISIT_MANAGE,
            Capability.EVALUATION_VIEW_OWN,
            Capability.INDICATORS_VIEW,
            Capability.TASK_VIEW_OWN,
            Capability.TASK_ATTEND,
        }
    ),
    Role.EVALUATOR: frozenset(
        {Capability.VISIT_VIEW_ALL, Capability.EVALUATION_VIEW_ALL, Capability.EVALUATION_MANAGE}
    ),
    Role.RESULTS: frozenset({Capability.EVALUATION_VIEW_COMPLETED, Capability.INDICATORS_VIEW}),
    Role.TASKS: frozenset({Capability.TASK_VIEW_ALL, Capability.TASK_ATTEND}),
}


def capabilities_of(user) -> frozenset[Capability]:
    if not user.is_authenticated or not user.is_active:
        return frozenset()
    return ROLE_CAPABILITIES.get(user.role, frozenset())


def has_capability(user, capability: Capability) -> bool:
    return capability in capabilities_of(user)
