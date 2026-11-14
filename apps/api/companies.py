"""Empresas y su estructura: sede > área > puesto > trabajador.

El alcance lo dan los selectores de apps.companies: un registro fuera del alcance del usuario
no se encuentra y la respuesta es 404, igual que en la pantalla actual.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import Capability, has_capability
from apps.accounts.selectors import company_accounts
from apps.companies import selectors
from apps.companies.forms import AreaForm, CompanyForm, PositionForm, SiteForm, WorkerForm
from apps.companies.models import Company, Worker
from apps.companies.structure import structure_counts
from apps.contracts.services import current_contract

from . import presenters
from .common import choices, paginate, save_form
from .permissions import HasCapability

DUPLICATE_NAME = "Ya existe un registro con ese nombre en este mismo nivel."
DUPLICATE_DOCUMENT = "Este documento ya está registrado en el puesto."
INACTIVE = "La empresa está inactiva: no se le puede agregar estructura."


def place(municipality) -> dict:
    return {
        "municipality": {"id": municipality.pk, "name": municipality.name},
        "department": {"id": municipality.department_id, "name": municipality.department.name},
        "location": municipality.full_name,
    }


def company_row(company) -> dict:
    return {
        "id": company.pk,
        "name": company.name,
        "nit": company.nit_display,
        "is_active": company.is_active,
        "site_count": getattr(company, "site_count", None),
        **place(company.municipality),
    }


def worker_data(worker) -> dict:
    return {
        "id": worker.pk,
        "first_name": worker.first_name,
        "last_name": worker.last_name,
        "full_name": worker.full_name,
        "initials": (worker.first_name[:1] + worker.last_name[:1]).upper(),
        "document_type": worker.document_type,
        "document_number": worker.document_number,
        "document_display": worker.document_display,
        "hired_on": presenters.iso(worker.hired_on),
        "is_active": worker.is_active,
    }


def position_data(position) -> dict:
    return {
        "id": position.pk,
        "key": position.node_key,
        "name": position.name,
        "description": position.description,
        "workers": [worker_data(w) for w in position.workers.all()],
    }


def area_data(area) -> dict:
    return {
        "id": area.pk,
        "key": area.node_key,
        "name": area.name,
        "description": area.description,
        "positions": [position_data(p) for p in area.positions.all()],
    }


def site_data(site) -> dict:
    return {
        "id": site.pk,
        "key": site.node_key,
        "name": site.name,
        "address": site.address,
        **place(site.municipality),
        "areas": [area_data(a) for a in site.areas.all()],
    }


def account_data(account) -> dict:
    return {
        **presenters.user_data(account),
        "is_active": account.is_active,
        "last_login": presenters.iso(account.last_login),
    }


def company_detail(company, user) -> dict:
    can = lambda capability: has_capability(user, capability)  # noqa: E731
    shows_contract = can(Capability.CONTRACT_MANAGE) or can(Capability.CONTRACT_VIEW_OWN)
    contract = current_contract(company) if shows_contract else None
    manages_accounts = can(Capability.COMPANY_USER_MANAGE)
    return {
        **company_row(company),
        "counts": structure_counts(company),
        "sites": [site_data(s) for s in company.sites.all()],
        "shows_contract": shows_contract,
        "contract": presenters.contract_data(contract, timezone.localdate()) if contract else None,
        "accounts": [account_data(a) for a in company_accounts(company)] if manages_accounts else None,
        "permissions": {
            "view_all": can(Capability.COMPANY_VIEW_ALL),
            "manage": can(Capability.COMPANY_MANAGE),
            "manage_accounts": manages_accounts,
            "manage_contracts": can(Capability.CONTRACT_MANAGE),
        },
        "document_types": choices(Worker.DocumentType.choices),
    }


def load_detail(user, pk) -> Company:
    return get_object_or_404(selectors.with_structure(selectors.visible_companies(user)), pk=pk)


class CompanyListView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]

    def get_permissions(self):
        self.required_capabilities = (
            (Capability.COMPANY_MANAGE,) if self.request.method == "POST" else (Capability.COMPANY_VIEW_ALL,)
        )
        return super().get_permissions()

    def get(self, request):
        companies = selectors.search_companies(request.user, request.query_params.get("q", ""))
        return Response(paginate(request, companies, company_row, per_page=15))

    def post(self, request):
        form = CompanyForm(data=request.data)
        return save_form(form, lambda c: {"id": c.pk}, integrity_message="Ya existe una empresa con este NIT.", created=True)


class CompanyDetailView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]

    def get_permissions(self):
        self.required_capabilities = (
            (Capability.COMPANY_MANAGE,) if self.request.method == "PUT"
            else (Capability.COMPANY_VIEW_ALL, Capability.COMPANY_VIEW_OWN)
        )
        return super().get_permissions()

    def get(self, request, pk):
        return Response(company_detail(load_detail(request.user, pk), request.user))

    def put(self, request, pk):
        company = get_object_or_404(selectors.visible_companies(request.user), pk=pk)
        form = CompanyForm(data=request.data, instance=company)
        return save_form(form, lambda c: {"id": c.pk}, integrity_message="Ya existe una empresa con este NIT.")


class StructureView(APIView):
    """POST crea un hijo bajo `parent_pk`; PUT edita el registro `pk`. Solo quien gestiona empresas."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.COMPANY_MANAGE,)
    parent_selector = None
    object_selector = None
    form_class = None
    integrity_message = DUPLICATE_NAME

    @staticmethod
    def company_of(obj) -> Company:
        return obj if isinstance(obj, Company) else obj.company

    def present(self, obj) -> dict:
        return {"id": obj.pk, "key": obj.node_key, "company_id": self.company_of(obj).pk}

    def post(self, request, parent_pk):
        parent = get_object_or_404(type(self).parent_selector(request.user), pk=parent_pk)
        if not self.company_of(parent).is_active:
            raise exceptions.PermissionDenied(INACTIVE)
        form = self.form_class(data=request.data, parent=parent)
        return save_form(form, self.present, integrity_message=self.integrity_message, created=True)

    def put(self, request, pk):
        obj = get_object_or_404(type(self).object_selector(request.user), pk=pk)
        form = self.form_class(data=request.data, instance=obj)
        return save_form(form, self.present, integrity_message=self.integrity_message)


class SiteView(StructureView):
    parent_selector = selectors.visible_companies
    object_selector = selectors.visible_sites
    form_class = SiteForm


class AreaView(StructureView):
    parent_selector = selectors.visible_sites
    object_selector = selectors.visible_areas
    form_class = AreaForm


class PositionView(StructureView):
    parent_selector = selectors.visible_areas
    object_selector = selectors.visible_positions
    form_class = PositionForm


class WorkerView(StructureView):
    parent_selector = selectors.visible_positions
    object_selector = selectors.visible_workers
    form_class = WorkerForm
    integrity_message = DUPLICATE_DOCUMENT

    def present(self, worker) -> dict:
        # Al guardar un trabajador se vuelve a su puesto en el árbol.
        return {"id": worker.pk, "key": worker.position.node_key, "company_id": worker.company.pk}
