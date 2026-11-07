from datetime import timedelta

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.permissions import Capability, has_capability

from .models import EXPIRING_SOON_DAYS, Contract, ContractStatus


def visible_contracts(user) -> QuerySet[Contract]:
    # Los bytes del PDF solo se piden al descargarlo.
    contracts = Contract.objects.select_related("company", "created_by").defer("file_data")
    if has_capability(user, Capability.CONTRACT_MANAGE):
        return contracts
    if has_capability(user, Capability.CONTRACT_VIEW_OWN) and user.company_id:
        return contracts.filter(company_id=user.company_id)
    return contracts.none()


def status_condition(status: str) -> Q | None:
    today = timezone.localdate()
    soon = today + timedelta(days=EXPIRING_SOON_DAYS)
    return {
        ContractStatus.UPCOMING: Q(start_date__gt=today),
        ContractStatus.ACTIVE: Q(start_date__lte=today, end_date__gt=soon),
        ContractStatus.EXPIRING: Q(start_date__lte=today, end_date__gte=today, end_date__lte=soon),
        ContractStatus.EXPIRED: Q(end_date__lt=today),
    }.get(status)


def search_contracts(user, query: str = "", status: str = "") -> QuerySet[Contract]:
    contracts = visible_contracts(user).order_by("end_date", "pk")
    condition = status_condition(status)
    if condition is not None:
        contracts = contracts.filter(condition)
    query = query.strip()
    if query:
        contracts = contracts.filter(
            Q(company__name__icontains=query) | Q(code__icontains=query) | Q(responsible_name__icontains=query)
        )
    return contracts


def status_counts(user) -> dict[str, int]:
    contracts = visible_contracts(user)
    return {status.value: contracts.filter(status_condition(status)).count() for status in ContractStatus}


def expiring_contracts(user) -> QuerySet[Contract]:
    return visible_contracts(user).filter(status_condition(ContractStatus.EXPIRING)).order_by("end_date")
