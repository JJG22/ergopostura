from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability, has_capability
from apps.accounts.selectors import company_accounts
from apps.contracts.services import current_contract
from apps.core.views import ModalFormMixin

from . import selectors
from .forms import AreaForm, CompanyForm, PositionForm, SiteForm, WorkerForm
from .models import Company
from .structure import select_node, structure_counts


def company_detail_url(company: Company, node_key: str | None = None) -> str:
    url = reverse("companies:detail", args=[company.pk])
    return f"{url}?{urlencode({'nodo': node_key})}" if node_key else url


class ManageMixin(CapabilityRequiredMixin):
    required_capabilities = (Capability.COMPANY_MANAGE,)


class CompanyListView(CapabilityRequiredMixin, ListView):
    required_capabilities = (Capability.COMPANY_VIEW_ALL,)
    template_name = "companies/list.html"
    context_object_name = "companies"
    paginate_by = 15

    def get_queryset(self):
        return selectors.search_companies(self.request.user, self.request.GET.get("q", ""))

    def get_context_data(self, **kwargs):
        return super().get_context_data(query=self.request.GET.get("q", "").strip(), **kwargs)


class CompanyDetailView(CapabilityRequiredMixin, DetailView):
    required_capabilities = (Capability.COMPANY_VIEW_ALL, Capability.COMPANY_VIEW_OWN)
    template_name = "companies/detail.html"
    context_object_name = "company"

    def get_queryset(self):
        return selectors.with_structure(selectors.visible_companies(self.request.user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        company = self.object
        manages_accounts = has_capability(user, Capability.COMPANY_USER_MANAGE)
        contract = current_contract(company) if (
            has_capability(user, Capability.CONTRACT_MANAGE) or has_capability(user, Capability.CONTRACT_VIEW_OWN)
        ) else None
        context.update(
            selection=select_node(company, self.request.GET.get("nodo")),
            counts=structure_counts(company),
            manages_accounts=manages_accounts,
            accounts=company_accounts(company) if manages_accounts else [],
            contract=contract,
            contract_status=contract.status_on(timezone.localdate()) if contract else None,
            manages_contracts=has_capability(user, Capability.CONTRACT_MANAGE),
        )
        return context


class CompanyCreateView(ManageMixin, ModalFormMixin, CreateView):
    form_class = CompanyForm
    title = "Registrar empresa"
    submit_label = "Registrar empresa"
    note = "Las sedes son opcionales. Podrás agregarlas después desde el detalle de la empresa."
    success_title = "Empresa registrada"
    integrity_error_message = "Ya existe una empresa con este NIT."

    def get_cancel_url(self):
        return reverse("companies:list")

    def get_success_url(self):
        return company_detail_url(self.object)


class CompanyUpdateView(ManageMixin, ModalFormMixin, UpdateView):
    form_class = CompanyForm
    title = "Editar empresa"
    success_title = "Empresa actualizada"
    integrity_error_message = "Ya existe una empresa con este NIT."

    def get_queryset(self):
        return selectors.visible_companies(self.request.user)

    def get_cancel_url(self):
        return company_detail_url(self.object)

    def get_success_url(self):
        return company_detail_url(self.object)


class StructureCreateView(ManageMixin, ModalFormMixin, CreateView):
    """Crea un hijo bajo un padre que el usuario tiene permitido ver."""

    parent_selector = None

    @cached_property
    def parent(self):
        return get_object_or_404(type(self).parent_selector(self.request.user), pk=self.kwargs["parent_pk"])

    def get_form_kwargs(self):
        if not self.parent_company.is_active:
            raise PermissionDenied("No se puede agregar estructura a una empresa inactiva.")
        return {**super().get_form_kwargs(), "parent": self.parent}

    @property
    def parent_company(self) -> Company:
        return self.parent if isinstance(self.parent, Company) else self.parent.company

    def get_cancel_url(self):
        return company_detail_url(self.parent_company, self.parent.node_key)

    def get_success_url(self):
        return company_detail_url(self.parent_company, self.object.node_key)


class StructureUpdateView(ManageMixin, ModalFormMixin, UpdateView):
    object_selector = None
    success_title = "Cambios guardados"

    def get_queryset(self):
        return type(self).object_selector(self.request.user)

    def _detail_url(self):
        return company_detail_url(self.object.company, self.object.node_key)

    def get_cancel_url(self):
        return self._detail_url()

    def get_success_url(self):
        return self._detail_url()


DUPLICATE_NAME = "Ya existe un registro con ese nombre en este mismo nivel."


class SiteCreateView(StructureCreateView):
    parent_selector = selectors.visible_companies
    form_class = SiteForm
    title = "Agregar sede"
    success_title = "Sede registrada"
    integrity_error_message = DUPLICATE_NAME


class SiteUpdateView(StructureUpdateView):
    object_selector = selectors.visible_sites
    form_class = SiteForm
    title = "Editar sede"
    integrity_error_message = DUPLICATE_NAME


class AreaCreateView(StructureCreateView):
    parent_selector = selectors.visible_sites
    form_class = AreaForm
    title = "Agregar área"
    success_title = "Área registrada"
    integrity_error_message = DUPLICATE_NAME


class AreaUpdateView(StructureUpdateView):
    object_selector = selectors.visible_areas
    form_class = AreaForm
    title = "Editar área"
    integrity_error_message = DUPLICATE_NAME


class PositionCreateView(StructureCreateView):
    parent_selector = selectors.visible_areas
    form_class = PositionForm
    title = "Agregar puesto de trabajo"
    success_title = "Puesto registrado"
    integrity_error_message = DUPLICATE_NAME


class PositionUpdateView(StructureUpdateView):
    object_selector = selectors.visible_positions
    form_class = PositionForm
    title = "Editar puesto de trabajo"
    integrity_error_message = DUPLICATE_NAME


class WorkerCreateView(StructureCreateView):
    parent_selector = selectors.visible_positions
    form_class = WorkerForm
    title = "Agregar trabajador"
    success_title = "Trabajador registrado"
    integrity_error_message = "Este documento ya está registrado en el puesto."
    note = "Son datos personales: solo los verán el ingeniero y la propia empresa."

    def get_success_url(self):
        return company_detail_url(self.parent_company, self.parent.node_key)


class WorkerUpdateView(StructureUpdateView):
    object_selector = selectors.visible_workers
    form_class = WorkerForm
    title = "Editar trabajador"
    integrity_error_message = "Este documento ya está registrado en el puesto."

    def _detail_url(self):
        return company_detail_url(self.object.company, self.object.position.node_key)
