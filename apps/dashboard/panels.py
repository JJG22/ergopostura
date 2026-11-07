"""Un panel por rol. Agregar un rol o cambiar su vista no modifica la vista HTTP."""
from collections.abc import Callable
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.selectors import users_by_role
from apps.companies import selectors as company_selectors
from apps.companies.structure import structure_counts
from apps.contracts import reader
from apps.contracts import selectors as contract_selectors
from apps.contracts.services import current_contract
from apps.evaluations.models import Evaluation
from apps.evaluations.selectors import visible_evaluations
from apps.tasks.selectors import pending_recommendations
from apps.visits import selectors as visit_selectors


@dataclass(frozen=True)
class Panel:
    template: str
    build_context: Callable[[object], dict]


def _with_levels(visits):
    now = timezone.now()
    visits = list(visits)
    for visit in visits:
        visit.current_level = visit.level_at(now)
    return visits


def _admin_context(user) -> dict:
    User = get_user_model()
    return {
        "users_by_role": users_by_role(),
        "has_engineer": User.objects.filter(role=Role.ENGINEER, is_active=True).exists(),
        "recent_accounts": User.objects.select_related("company").order_by("-date_joined")[:6],
        "ai_ready": reader.is_configured(),
    }


def _engineer_context(user) -> dict:
    totals = company_selectors.structure_totals(user)
    counts = contract_selectors.status_counts(user)
    evaluations = visible_evaluations(user)
    to_close = visit_selectors.visits_to_close(user)
    steps = [
        ("Registra una empresa cliente con sus sedes, áreas, puestos y trabajadores", totals["companies"] > 0),
        ("Sube su contrato de servicio", sum(counts.values()) > 0),
        ("Crea el acceso de la empresa para que agende visitas", get_user_model().objects.filter(role=Role.COMPANY).exists()),
        ("Registra la visita como realizada y crea la evaluación RULA", evaluations.exists()),
    ]
    return {
        "totals": totals,
        "contract_counts": counts,
        "steps": steps,
        "onboarding": not all(done for _, done in steps),
        "to_close": _with_levels(to_close[:5]),
        "to_close_count": len(to_close),
        "upcoming_visits": _with_levels(visit_selectors.upcoming_visits(user)[:4]),
        "without_evaluation": visit_selectors.completed_without_evaluation(user)[:5],
        "expiring_contracts": contract_selectors.expiring_contracts(user)[:5],
        "drafts_count": evaluations.filter(status=Evaluation.Status.DRAFT).count(),
        "recent_evaluations": evaluations[:5],
    }


def _company_context(user) -> dict:
    company = company_selectors.with_structure(company_selectors.visible_companies(user)).first()
    contract = current_contract(company) if company else None
    today = timezone.localdate()
    return {
        "company": company,
        "counts": structure_counts(company) if company else None,
        "contract": contract,
        "contract_status": contract.status_on(today) if contract else None,
        "contract_days_left": contract.days_left(today) if contract else None,
        "upcoming_visits": _with_levels(visit_selectors.upcoming_visits(user)[:5]),
        "recent_evaluations": visible_evaluations(user)[:5],
        "pending_count": pending_recommendations(user).count(),
    }


PANELS: dict[str, Panel] = {
    Role.ADMIN: Panel("dashboard/admin.html", _admin_context),
    Role.ENGINEER: Panel("dashboard/engineer.html", _engineer_context),
    Role.COMPANY: Panel("dashboard/company.html", _company_context),
}


def panel_for(user) -> Panel:
    return PANELS[user.role]
