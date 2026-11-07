import hashlib
from datetime import datetime, time, timedelta
from itertools import count

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Role
from apps.companies.models import Area, Company, Position, Site, Worker
from apps.contracts.models import Contract
from apps.core.demo.pdf import text_pdf
from apps.geography.models import Municipality
from apps.visits.models import Visit

_sequence = count(1)
PASSWORD = "Prueba-segura-2026"


def municipality(name="Armenia", department="Quindío"):
    """El catalogo lo carga la migracion de geography, asi que existe en toda prueba."""
    return Municipality.objects.get(name=name, department__name=department)


def make_company(name="Café Montaña S.A.S.", nit=None, **fields):
    nit = nit or str(800_000_000 + next(_sequence))
    fields.setdefault("municipality", municipality())
    return Company.objects.create(name=name, nit=nit, **fields)


def make_site(company=None, name="Planta Armenia"):
    return Site.objects.create(company=company or make_company(), name=name, municipality=municipality())


def make_area(site=None, name="Empaque"):
    return Area.objects.create(site=site or make_site(), name=name)


def make_position(area=None, name="Operario de empaque"):
    return Position.objects.create(area=area or make_area(), name=name)


def make_user(role=Role.ENGINEER, company=None, **fields):
    email = fields.pop("email", f"usuario{next(_sequence)}@ergopostura.test")
    if role == Role.COMPANY and company is None:
        company = make_company()
    return get_user_model().objects.create_user(
        email=email, password=PASSWORD, role=role, company=company, **fields
    )


def make_worker(position=None, document_number=None, **fields):
    fields.setdefault("first_name", "Carolina")
    fields.setdefault("last_name", "Gómez")
    return Worker.objects.create(
        position=position or make_position(),
        document_number=document_number or str(10_000_000 + next(_sequence)),
        **fields,
    )


def sample_pdf(text="Contrato de prueba"):
    return text_pdf("Contrato", [text])


def make_contract(company=None, start=None, end=None, **fields):
    today = timezone.localdate()
    start = start or today - timedelta(days=30)
    end = end or start + timedelta(days=364)
    pdf = fields.pop("pdf", None) or sample_pdf(f"Contrato {next(_sequence)}")
    fields.setdefault("service", "Evaluación ergonómica con RULA.")
    fields.setdefault("responsible_name", "Marta Salazar")
    return Contract.objects.create(
        company=company or make_company(),
        start_date=start,
        end_date=end,
        file_data=pdf,
        file_name="contrato.pdf",
        file_size=len(pdf),
        file_sha256=hashlib.sha256(pdf).hexdigest(),
        **fields,
    )


def at(day, hour=9, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def make_visit(site=None, scheduled_at=None, status=Visit.Status.SCHEDULED, **fields):
    """Por defecto, programada para pasado manana a las 9:00."""
    site = site or make_site()
    scheduled_at = scheduled_at or at(timezone.localdate() + timedelta(days=2))
    fields.setdefault("purpose", "Evaluar los puestos de empaque.")
    fields.setdefault("contact_name", "Marta Salazar")
    visit = Visit(site=site, scheduled_at=scheduled_at, status=status, **fields)
    if status == Visit.Status.COMPLETED:
        visit.completed_at = visit.completed_at or scheduled_at + timedelta(hours=2)
    elif status == Visit.Status.CANCELLED:
        visit.cancelled_at = visit.cancelled_at or timezone.now()
        visit.cancellation_reason = visit.cancellation_reason or "Cambio de planes."
    visit.save()
    return visit


def completed_visit(position=None, days_ago=3):
    """Visita realizada en la sede del puesto: el requisito para evaluarlo."""
    position = position or make_position()
    return make_visit(
        site=position.area.site,
        scheduled_at=at(timezone.localdate() - timedelta(days=days_ago)),
        status=Visit.Status.COMPLETED,
    )
