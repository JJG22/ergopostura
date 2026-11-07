"""Reglas de los contratos: documento valido, vigencias sin cruces y visitas cubiertas."""
import hashlib
from datetime import date

from django.db.models import QuerySet
from django.utils import timezone

from apps.visits.models import Visit

from . import reader
from .models import Contract, ContractReading

MAX_FILE_BYTES = 10 * 1024 * 1024


class InvalidDocument(ValueError):
    pass


def read_upload(uploaded) -> tuple[bytes, str]:
    """Devuelve los bytes y la huella del PDF, o explica por que no se acepta."""
    if uploaded.size > MAX_FILE_BYTES:
        raise InvalidDocument("El contrato supera el límite de 10 MB.")
    data = uploaded.read()
    # Se revisa el contenido, no la extension: un archivo renombrado no pasa.
    if not data.startswith(b"%PDF-"):
        raise InvalidDocument("Sube el contrato en formato PDF.")
    return data, hashlib.sha256(data).hexdigest()


def contracts_of(company) -> QuerySet[Contract]:
    return Contract.objects.filter(company=company).defer("file_data")


def contract_on(company, day: date) -> Contract | None:
    return contracts_of(company).filter(start_date__lte=day, end_date__gte=day).first()


def current_contract(company) -> Contract | None:
    """El contrato vigente hoy o, si no hay, el proximo en empezar."""
    today = timezone.localdate()
    return contract_on(company, today) or contracts_of(company).filter(start_date__gt=today).order_by("start_date").first()


def overlapping(company, start: date, end: date, exclude_pk=None) -> Contract | None:
    return (
        contracts_of(company)
        .filter(start_date__lte=end, end_date__gte=start)
        .exclude(pk=exclude_pk)
        .order_by("start_date")
        .first()
    )


def uncovered_visits(company, *, contract_pk=None, start=None, end=None) -> list[Visit]:
    """Visitas pendientes de la empresa que quedarian sin contrato.

    Con start y end: si el contrato contract_pk pasara a esa vigencia.
    Sin ellos: si el contrato contract_pk se eliminara.
    """
    others = list(contracts_of(company).exclude(pk=contract_pk).values_list("start_date", "end_date"))
    visits = Visit.objects.filter(
        site__company=company, status=Visit.Status.SCHEDULED, scheduled_at__gte=timezone.now()
    ).select_related("site")
    result = []
    for visit in visits:
        day = timezone.localdate(visit.scheduled_at)
        covered = any(first <= day <= last for first, last in others)
        if start is not None and start <= day <= end:
            covered = True
        if not covered:
            result.append(visit)
    return result


def reading_for(sha256: str) -> ContractReading | None:
    return ContractReading.objects.filter(sha256=sha256).first()


def read_document(pdf: bytes, sha256: str, user) -> ContractReading:
    """Lee el PDF con la IA una sola vez por archivo; las siguientes veces usa lo guardado."""
    cached = reading_for(sha256)
    if cached is not None:
        return cached
    result = reader.read_contract(pdf)
    reading, _ = ContractReading.objects.update_or_create(
        sha256=sha256, defaults={"summary": result.summary, "model": result.model, "requested_by": user}
    )
    return reading


def attach_reading(contract: Contract, reading: ContractReading) -> None:
    contract.ai_summary = reading.summary
    contract.ai_model = reading.model
    contract.ai_generated_at = reading.created_at


def summarize(contract: Contract, user) -> Contract:
    """Genera (o reutiliza) la lectura del documento guardado y la asocia al contrato."""
    pdf = bytes(Contract.objects.values_list("file_data", flat=True).get(pk=contract.pk))
    reading = read_document(pdf, contract.file_sha256, user)
    attach_reading(contract, reading)
    contract.save(update_fields=["ai_summary", "ai_model", "ai_generated_at", "updated_at"])
    return contract


# --- Comparacion entre lo leido y lo registrado ----------------------------------

def _simplify(value) -> str:
    return " ".join(str(value or "").lower().replace(".", " ").replace(",", " ").split())


def _same_text(left, right) -> bool:
    return _simplify(left) == _simplify(right)


def _as_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def comparison(contract: Contract) -> list[dict]:
    """Filas «leido en el documento» frente a «registrado», con las diferencias marcadas."""
    summary = contract.ai_summary or {}
    if not summary:
        return []
    company = contract.company
    kind_labels = dict(Contract.Kind.choices)
    rows = [
        ("Empresa", summary.get("client_name"), company.name, _same_text),
        (
            "NIT",
            summary.get("client_nit_text"),
            company.nit_display,
            lambda _read, _registered: summary.get("client_nit") == company.nit,
        ),
        (
            "Tipo de contrato",
            kind_labels.get(summary.get("contract_type")),
            contract.get_kind_display(),
            lambda read, registered: read == registered,
        ),
        ("Inicio", _as_date(summary.get("start_date")), contract.start_date, lambda a, b: a == b),
        ("Fin", _as_date(summary.get("end_date")), contract.end_date, lambda a, b: a == b),
        ("Encargado", summary.get("responsible_name"), contract.responsible_name, _same_text),
        (
            "Valor",
            summary.get("value_cop"),
            int(contract.value) if contract.value is not None else None,
            lambda a, b: a == b,
        ),
    ]
    return [
        {
            "label": label,
            "read": read,
            "registered": registered,
            "missing": read in (None, ""),
            "differs": read not in (None, "") and registered not in (None, "") and not matches(read, registered),
        }
        for label, read, registered, matches in rows
    ]


def nit_mismatch(contract: Contract) -> bool:
    summary = contract.ai_summary or {}
    return bool(summary.get("client_nit_text")) and summary.get("client_nit") != contract.company.nit
