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


ROLE_CAPABILITIES: dict[str, frozenset[Capability]] = {
    Role.ADMIN: frozenset(Capability),
    Role.ENGINEER: frozenset(
        {Capability.COMPANY_VIEW_ALL, Capability.COMPANY_MANAGE, Capability.VISIT_VIEW_ALL}
    ),
    # RF-006: la empresa registra sus visitas acordadas.
    Role.COMPANY: frozenset(
        {Capability.COMPANY_VIEW_OWN, Capability.VISIT_VIEW_OWN, Capability.VISIT_MANAGE}
    ),
    Role.EVALUATOR: frozenset({Capability.VISIT_VIEW_ALL}),
    # Sin permisos hasta construir sus modulos: indicadores y tareas.
    Role.RESULTS: frozenset(),
    Role.TASKS: frozenset(),
}


def capabilities_of(user) -> frozenset[Capability]:
    if not user.is_authenticated or not user.is_active:
        return frozenset()
    return ROLE_CAPABILITIES.get(user.role, frozenset())


def has_capability(user, capability: Capability) -> bool:
    return capability in capabilities_of(user)
