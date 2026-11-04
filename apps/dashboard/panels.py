"""Un panel por rol. Agregar un rol o cambiar su vista no modifica la vista HTTP."""
from collections.abc import Callable
from dataclasses import dataclass

from apps.accounts.models import Role
from apps.accounts.selectors import users_by_role
from apps.companies import selectors as company_selectors
from apps.companies.structure import structure_counts
from apps.evaluations.selectors import visible_evaluations
from apps.tasks.selectors import pending_recommendations
from apps.visits.selectors import upcoming_visits


@dataclass(frozen=True)
class Panel:
    template: str
    build_context: Callable[[object], dict]


def _recent_evaluations(user):
    return visible_evaluations(user)[:5]


def _admin_context(user) -> dict:
    return {
        "totals": company_selectors.structure_totals(user),
        "users_by_role": users_by_role(),
        "recent_companies": company_selectors.search_companies(user).order_by("-created_at")[:5],
        "recent_evaluations": _recent_evaluations(user),
    }


def _engineer_context(user) -> dict:
    return {
        "totals": company_selectors.structure_totals(user),
        "recent_companies": company_selectors.search_companies(user).order_by("-created_at")[:5],
        "recent_evaluations": _recent_evaluations(user),
    }


def _company_context(user) -> dict:
    company = company_selectors.with_structure(company_selectors.visible_companies(user)).first()
    return {
        "company": company,
        "counts": structure_counts(company) if company else None,
        "upcoming_visits": upcoming_visits(user)[:5],
        "recent_evaluations": _recent_evaluations(user),
    }


def _evaluator_context(user) -> dict:
    return {
        "upcoming_visits": upcoming_visits(user)[:5],
        "recent_evaluations": _recent_evaluations(user),
    }


def _results_context(user) -> dict:
    return {"recent_evaluations": _recent_evaluations(user)}


def _tasks_context(user) -> dict:
    pending = pending_recommendations(user)
    return {"pending_count": pending.count(), "recommendations": pending[:5]}


PANELS: dict[str, Panel] = {
    Role.ADMIN: Panel("dashboard/admin.html", _admin_context),
    Role.ENGINEER: Panel("dashboard/engineer.html", _engineer_context),
    Role.COMPANY: Panel("dashboard/company.html", _company_context),
    Role.EVALUATOR: Panel("dashboard/evaluator.html", _evaluator_context),
    Role.RESULTS: Panel("dashboard/results.html", _results_context),
    Role.TASKS: Panel("dashboard/tasks.html", _tasks_context),
}


def panel_for(user) -> Panel:
    return PANELS[user.role]
