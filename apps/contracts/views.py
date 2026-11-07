from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability, has_capability
from apps.companies.models import Company

from . import reader, selectors, services
from .forms import ContractForm
from .models import Contract, ContractStatus

VIEW_CAPABILITIES = (Capability.CONTRACT_MANAGE, Capability.CONTRACT_VIEW_OWN)


class ManageMixin(CapabilityRequiredMixin):
    required_capabilities = (Capability.CONTRACT_MANAGE,)


class ContractListView(ManageMixin, ListView):
    template_name = "contracts/list.html"
    context_object_name = "contracts"
    paginate_by = 15

    @property
    def status(self) -> str:
        value = self.request.GET.get("estado", "")
        return value if value in ContractStatus.values else ""

    def get_queryset(self):
        return selectors.search_contracts(self.request.user, self.request.GET.get("q", ""), self.status)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        counts = selectors.status_counts(self.request.user)
        for contract in context["contracts"]:
            contract.status = contract.status_on(today)
            contract.left = contract.days_left(today)
        context.update(
            query=self.request.GET.get("q", "").strip(),
            status=self.status,
            statuses=[(item.value, item.label, counts[item.value]) for item in ContractStatus],
            today=today,
        )
        return context


class ContractFormMixin(ManageMixin):
    form_class = ContractForm
    template_name = "contracts/form.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "actor": self.request.user}

    def get_context_data(self, **kwargs):
        return super().get_context_data(ai_ready=reader.is_configured(), **kwargs)

    def form_valid(self, form):
        company = form.company
        with transaction.atomic():
            # Bloquea la empresa: dos contratos guardados a la vez no pueden cruzarse.
            Company.objects.select_for_update().get(pk=company.pk)
            other = services.overlapping(
                company, form.cleaned_data["start_date"], form.cleaned_data["end_date"], form.instance.pk
            )
            if other is not None:
                form.add_error("start_date", f"Se cruza con el contrato {other.display_code}.")
                return self.form_invalid(form)
            self.object = form.save()
        messages.success(self.request, self.success_message)
        return redirect("contracts:detail", pk=self.object.pk)


class ContractCreateView(ContractFormMixin, CreateView):
    success_message = "Contrato registrado"

    @cached_property
    def company(self):
        value = self.request.GET.get("empresa", "")
        return Company.objects.filter(pk=value, is_active=True).first() if value.isdigit() else None

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "company": self.company}

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title="Registrar contrato", submit_label="Guardar contrato", cancel_url=reverse("contracts:list"), **kwargs
        )


class ContractUpdateView(ContractFormMixin, UpdateView):
    success_message = "Contrato actualizado"

    def get_queryset(self):
        return selectors.visible_contracts(self.request.user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title=f"Editar contrato {self.object.display_code}",
            submit_label="Guardar cambios",
            cancel_url=reverse("contracts:detail", args=[self.object.pk]),
            **kwargs,
        )


class ContractDetailView(CapabilityRequiredMixin, DetailView):
    required_capabilities = VIEW_CAPABILITIES
    template_name = "contracts/detail.html"
    context_object_name = "contract"

    def get_queryset(self):
        return selectors.visible_contracts(self.request.user).select_related("company__municipality__department")

    def get_context_data(self, **kwargs):
        contract = self.object
        today = timezone.localdate()
        can_manage = has_capability(self.request.user, Capability.CONTRACT_MANAGE)
        return super().get_context_data(
            can_manage=can_manage,
            status=contract.status_on(today),
            days_left=contract.days_left(today),
            comparison=services.comparison(contract) if can_manage else [],
            nit_mismatch=can_manage and services.nit_mismatch(contract),
            ai_ready=reader.is_configured(),
            history=services.contracts_of(contract.company).exclude(pk=contract.pk).order_by("-start_date"),
            **kwargs,
        )


class ContractFileView(CapabilityRequiredMixin, View):
    """Entrega el PDF solo a quien puede ver el contrato: nunca es una URL publica."""

    required_capabilities = VIEW_CAPABILITIES

    def get(self, request, pk):
        contract = get_object_or_404(selectors.visible_contracts(request.user).select_related(None).only("pk"), pk=pk)
        data, name = Contract.objects.values_list("file_data", "file_name").get(pk=contract.pk)
        response = HttpResponse(bytes(data), content_type="application/pdf")
        disposition = "attachment" if request.GET.get("descargar") else "inline"
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "._- ") or "contrato.pdf"
        response["Content-Disposition"] = f'{disposition}; filename="{safe_name}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ContractSummarizeView(ManageMixin, View):
    def post(self, request, pk):
        contract = get_object_or_404(selectors.visible_contracts(request.user), pk=pk)
        try:
            services.summarize(contract, request.user)
        except (reader.ReaderUnavailable, reader.ReadingFailed) as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Resumen generado")
        return redirect("contracts:detail", pk=contract.pk)


class ContractReadView(ManageMixin, View):
    """Lee el PDF elegido en el formulario y devuelve datos para llenar los campos.

    No guarda el contrato. La lectura queda asociada a la huella del archivo para que,
    al guardar, el resumen no se tenga que pedir otra vez.
    """

    def post(self, request):
        uploaded = request.FILES.get("document")
        if uploaded is None:
            return JsonResponse({"error": "Elige el PDF del contrato."}, status=400)
        try:
            pdf, sha256 = services.read_upload(uploaded)
            reading = services.read_document(pdf, sha256, request.user)
        except services.InvalidDocument as error:
            return JsonResponse({"error": str(error)}, status=400)
        except reader.ReaderUnavailable as error:
            return JsonResponse({"error": str(error)}, status=503)
        except reader.ReadingFailed as error:
            return JsonResponse({"error": str(error)}, status=502)

        summary = reading.summary
        company = Company.objects.filter(nit=summary.get("client_nit")).first() if summary.get("client_nit") else None
        return JsonResponse(
            {
                "fields": {
                    "code": summary.get("contract_code"),
                    "kind": summary.get("contract_type"),
                    "start_date": summary.get("start_date"),
                    "end_date": summary.get("end_date"),
                    "value": summary.get("value_cop"),
                    "service": summary.get("service"),
                    "responsible_name": summary.get("responsible_name"),
                    "responsible_role": summary.get("responsible_role"),
                    "responsible_email": summary.get("responsible_email"),
                    "responsible_phone": summary.get("responsible_phone"),
                    "company": company.pk if company and company.is_active else None,
                },
                "summary": summary.get("summary"),
                "client": summary.get("client_name"),
                "client_nit": summary.get("client_nit_text"),
                "company_found": company is not None,
                "alerts": summary.get("alerts", []),
            }
        )


class ContractDeleteView(ManageMixin, View):
    def post(self, request, pk):
        contract = get_object_or_404(selectors.visible_contracts(request.user), pk=pk)
        left_out = services.uncovered_visits(contract.company, contract_pk=contract.pk)
        if left_out:
            messages.error(
                request,
                f"Hay {len(left_out)} visita(s) programada(s) dentro de este contrato. "
                "Deben cancelarse o reprogramarse antes de eliminarlo.",
            )
            return redirect("contracts:detail", pk=contract.pk)
        contract.delete()
        messages.success(request, "Contrato eliminado")
        return redirect("contracts:list")
