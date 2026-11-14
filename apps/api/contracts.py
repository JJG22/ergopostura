"""Contratos: PDF firmado, vigencias sin cruces, lectura con IA y comparación.

Las reglas viven en apps.contracts (formulario y servicios). El formulario recibe el PDF
como multipart; el resto de la API sigue siendo JSON.
"""
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import Capability, has_capability
from apps.companies.models import Company
from apps.contracts import reader, selectors, services
from apps.contracts.forms import ContractForm
from apps.contracts.models import Contract, ContractStatus

from . import presenters
from .common import choices, invalid, paginate
from .errors import error_response
from .permissions import HasCapability

MANAGE = (Capability.CONTRACT_MANAGE,)
VIEW = (Capability.CONTRACT_MANAGE, Capability.CONTRACT_VIEW_OWN)


def row(contract, today) -> dict:
    status_value = contract.status_on(today)
    return {
        "id": contract.pk,
        "code": contract.display_code,
        "company": {"id": contract.company_id, "name": contract.company.name},
        "kind": contract.kind,
        "kind_label": contract.get_kind_display(),
        "start_date": presenters.iso(contract.start_date),
        "end_date": presenters.iso(contract.end_date),
        "duration_label": contract.duration_label,
        "status": str(status_value),
        "status_label": status_value.label,
        "days_left": contract.days_left(today),
        "responsible_name": contract.responsible_name,
        "has_summary": bool(contract.ai_summary),
    }


def comparison_rows(contract) -> list[dict]:
    def plain(value):
        return presenters.iso(value) if hasattr(value, "isoformat") else value
    return [{**r, "read": plain(r["read"]), "registered": plain(r["registered"])} for r in services.comparison(contract)]


def detail(contract, user) -> dict:
    today = timezone.localdate()
    manages = has_capability(user, Capability.CONTRACT_MANAGE)
    company = contract.company
    data = {
        **row(contract, today),
        "company": {"id": company.pk, "name": company.name, "nit": company.nit_display},
        "code_value": contract.code,
        "service": contract.service,
        "value": int(contract.value) if contract.value is not None else None,
        "responsible_role": contract.responsible_role,
        "responsible_email": contract.responsible_email,
        "responsible_phone": contract.responsible_phone,
        "notes": contract.notes,
        "file_name": contract.file_name,
        "file_size": contract.file_size,
        "file_url": f"/api/v1/contracts/{contract.pk}/file/",
        "can_manage": manages,
        "ai_ready": reader.is_configured(),
    }
    if manages:
        data.update(
            created_at=presenters.iso(contract.created_at),
            created_by=str(contract.created_by) if contract.created_by else None,
            ai_summary=contract.ai_summary or None,
            ai_model=contract.ai_model,
            ai_generated_at=presenters.iso(contract.ai_generated_at),
            comparison=comparison_rows(contract),
            nit_mismatch=services.nit_mismatch(contract),
            history=[row(c, today) for c in services.contracts_of(company).select_related("company")
                     .exclude(pk=contract.pk).order_by("-start_date")],
        )
    return data


def options() -> dict:
    return {
        "companies": [{"id": c.pk, "name": c.name} for c in Company.objects.filter(is_active=True).order_by("name")],
        "kinds": choices(Contract.Kind.choices),
        "ai_ready": reader.is_configured(),
    }


def save_contract(form) -> Response | Contract:
    """Mismo cuidado que la pantalla actual: con la empresa bloqueada, dos contratos no se cruzan."""
    if not form.is_valid():
        return invalid(form)
    company = form.company
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=company.pk)
        other = services.overlapping(company, form.cleaned_data["start_date"], form.cleaned_data["end_date"], form.instance.pk)
        if other is not None:
            form.add_error("start_date", f"Se cruza con el contrato {other.display_code}.")
            return invalid(form)
        return form.save()


class ContractListView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request):
        value = request.query_params.get("status", "")
        value = value if value in ContractStatus.values else ""
        today = timezone.localdate()
        contracts = selectors.search_contracts(request.user, request.query_params.get("q", ""), value)
        data = paginate(request, contracts, lambda c: row(c, today), per_page=15)
        counts = selectors.status_counts(request.user)
        data["statuses"] = [{"value": s.value, "label": s.label, "total": counts[s.value]} for s in ContractStatus]
        return Response(data)

    def post(self, request):
        form = ContractForm(data=request.data, files=request.FILES, actor=request.user)
        result = save_contract(form)
        if isinstance(result, Response):
            return result
        return Response({"id": result.pk}, status=status.HTTP_201_CREATED)


class ContractOptionsView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def get(self, request):
        return Response(options())


class ContractDetailView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    parser_classes = [MultiPartParser, JSONParser]

    def get_permissions(self):
        self.required_capabilities = VIEW if self.request.method == "GET" else MANAGE
        return super().get_permissions()

    def contract(self, pk):
        return get_object_or_404(
            selectors.visible_contracts(self.request.user).select_related("company__municipality__department"), pk=pk
        )

    def get(self, request, pk):
        return Response(detail(self.contract(pk), request.user))

    def put(self, request, pk):
        form = ContractForm(data=request.data, files=request.FILES, instance=self.contract(pk), actor=request.user)
        result = save_contract(form)
        if isinstance(result, Response):
            return result
        return Response({"id": result.pk})

    def delete(self, request, pk):
        contract = self.contract(pk)
        left_out = services.uncovered_visits(contract.company, contract_pk=contract.pk)
        if left_out:
            return error_response(
                "conflict",
                f"Hay {len(left_out)} visita(s) programada(s) dentro de este contrato. "
                "Deben cancelarse o reprogramarse antes de eliminarlo.",
                status.HTTP_409_CONFLICT,
            )
        contract.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def reader_error(error) -> Response:
    if isinstance(error, reader.ReaderUnavailable):
        return error_response("ai_unavailable", str(error), status.HTTP_503_SERVICE_UNAVAILABLE)
    return error_response("ai_failed", str(error), status.HTTP_502_BAD_GATEWAY)


class ContractSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def post(self, request, pk):
        contract = get_object_or_404(selectors.visible_contracts(request.user), pk=pk)
        try:
            services.summarize(contract, request.user)
        except (reader.ReaderUnavailable, reader.ReadingFailed) as error:
            return reader_error(error)
        contract = selectors.visible_contracts(request.user).select_related("company__municipality__department").get(pk=pk)
        return Response(detail(contract, request.user))


class ContractReadView(APIView):
    """Lee el PDF elegido en el formulario y propone los datos. No guarda el contrato."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("document")
        if uploaded is None:
            return error_response("validation_error", "Elige el PDF del contrato.", status.HTTP_400_BAD_REQUEST,
                                  {"document": ["Elige el PDF del contrato."]})
        try:
            pdf, sha256 = services.read_upload(uploaded)
            reading = services.read_document(pdf, sha256, request.user)
        except services.InvalidDocument as error:
            return error_response("validation_error", str(error), status.HTTP_400_BAD_REQUEST, {"document": [str(error)]})
        except (reader.ReaderUnavailable, reader.ReadingFailed) as error:
            return reader_error(error)

        summary = reading.summary
        nit = summary.get("client_nit")
        company = Company.objects.filter(nit=nit).first() if nit else None
        return Response({
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
        })


class ContractFileView(APIView):
    """El PDF solo se entrega a quien puede ver el contrato: nunca es una URL pública."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = VIEW

    def get(self, request, pk):
        contract = get_object_or_404(selectors.visible_contracts(request.user).select_related(None).only("pk"), pk=pk)
        data, name = Contract.objects.values_list("file_data", "file_name").get(pk=contract.pk)
        response = HttpResponse(bytes(data), content_type="application/pdf")
        disposition = "attachment" if request.query_params.get("descargar") else "inline"
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "._- ") or "contrato.pdf"
        response["Content-Disposition"] = f'{disposition}; filename="{safe_name}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
