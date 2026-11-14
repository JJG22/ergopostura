"""Convierte los objetos del dominio en datos JSON para el cliente.

Cada función devuelve un diccionario simple. Las reglas (alcance, niveles, estados) vienen de
los modelos y selectores existentes: aquí solo se decide qué campos viajan al cliente.
`url` es la ruta de la pantalla en el cliente React.
"""
from django.utils import timezone

from apps.accounts.permissions import capabilities_of
from apps.core.navigation import NAV_ITEMS
from apps.rula.risk import action_level_for



def iso(value):
    return value.isoformat() if value else None


def user_data(user) -> dict:
    company = getattr(user, "company", None)
    return {
        "id": user.pk,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name() or user.email,
        "initials": user.initials,
        "role": user.role,
        "role_label": user.get_role_display(),
        "company": {"id": company.pk, "name": company.name} if company else None,
        "must_change_password": user.must_change_password,
        "is_staff": user.is_staff,
    }


def navigation(user) -> list[dict]:
    capabilities = capabilities_of(user)
    items = []
    for item in NAV_ITEMS:
        if item.capabilities and not capabilities.intersection(item.capabilities):
            continue
        items.append({"label": item.label, "icon": item.icon, "to": item.route, "href": None})
    return items


def session_data(user) -> dict:
    return {
        "user": user_data(user),
        "capabilities": sorted(str(c) for c in capabilities_of(user)),
        "navigation": navigation(user),
        "admin_url": "/admin/" if user.is_staff else None,
    }


def level_data(level) -> dict:
    return {"key": level.key, "label": level.label, "tone": level.tone}


def visit_data(visit, now=None) -> dict:
    now = now or timezone.now()
    return {
        "id": visit.pk,
        "company": visit.company.name,
        "site": visit.site.name,
        "municipality": visit.site.municipality.name,
        "starts_at": iso(visit.scheduled_at),
        "ends_at": iso(visit.ends_at),
        "contact_name": visit.contact_name,
        "status": visit.status,
        "level": level_data(visit.level_at(now)),
        "url": f"/visitas/{visit.pk}",
    }


def risk_data(score) -> dict | None:
    if score is None:
        return None
    action = action_level_for(score)
    return {
        "score": score,
        "level": action.level,
        "traffic_light": str(action.traffic_light),
        "label": action.traffic_light_meaning,
    }


def evaluation_data(evaluation) -> dict:
    position = evaluation.position
    return {
        "id": evaluation.pk,
        "code": evaluation.code,
        "company": position.area.site.company.name,
        "area": position.area.name,
        "position": position.name,
        "evaluated_on": iso(evaluation.evaluated_on),
        "status": evaluation.status,
        "status_label": evaluation.get_status_display(),
        "risk": risk_data(getattr(evaluation, "worst_score", None)),
        "url": f"/evaluaciones/{evaluation.pk}",
    }


def contract_data(contract, today=None) -> dict:
    today = today or timezone.localdate()
    status = contract.status_on(today)
    return {
        "id": contract.pk,
        "code": contract.display_code,
        "company": contract.company.name,
        "kind_label": contract.get_kind_display(),
        "start_date": iso(contract.start_date),
        "end_date": iso(contract.end_date),
        "status": str(status),
        "status_label": status.label,
        "days_left": contract.days_left(today),
        "url": f"/contratos/{contract.pk}",
    }
