"""Reglas para agendar una visita. Se revisan en el formulario y otra vez al guardar.

- Con anticipacion minima, dentro del horario de trabajo, de lunes a sabado.
- Dentro de la vigencia de un contrato de la empresa: sin contrato no hay servicio.
- Sin cruzarse con otra visita: el ingeniero no puede estar en dos empresas a la vez.
  La empresa ve esos espacios como «Ocupado», sin saber de quien son.
"""
from datetime import datetime, time, timedelta

from django.db import connection
from django.utils import timezone

from apps.contracts.services import contract_on

from .models import Visit

MIN_NOTICE = timedelta(hours=1)
WORK_START = time(7, 0)
WORK_END = time(18, 0)
LAST_WORKING_WEEKDAY = 5  # sabado; el domingo no se atiende
MAX_DURATION = max(minutes for minutes, _ in Visit.DURATION_CHOICES)
# Que no la tomen dos solicitudes a la vez: se serializa el agendamiento en la base.
SCHEDULE_LOCK_KEY = 7_406_001


def lock_schedule() -> None:
    """Bloqueo de la agenda hasta el fin de la transaccion (PostgreSQL)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [SCHEDULE_LOCK_KEY])


def overlapping_visit(start: datetime, minutes: int, exclude_pk=None) -> Visit | None:
    end = start + timedelta(minutes=minutes)
    candidates = (
        Visit.objects.exclude(status=Visit.Status.CANCELLED)
        .exclude(pk=exclude_pk)
        .filter(scheduled_at__lt=end, scheduled_at__gt=start - timedelta(minutes=MAX_DURATION))
    )
    return next((visit for visit in candidates if visit.ends_at > start), None)


def schedule_problems(company, start: datetime, minutes: int, *, exclude_pk=None, now=None) -> list[str]:
    now = now or timezone.now()
    local = timezone.localtime(start)
    end = local + timedelta(minutes=minutes)
    problems = []

    if start < now + MIN_NOTICE:
        problems.append("Agenda la visita con al menos una hora de anticipación.")
    if local.weekday() > LAST_WORKING_WEEKDAY:
        problems.append("Las visitas se atienden de lunes a sábado.")
    if local.time() < WORK_START or end.time() > WORK_END or end.date() != local.date():
        problems.append(
            f"La visita debe empezar desde las {WORK_START:%H:%M} y terminar a más tardar a las {WORK_END:%H:%M}."
        )

    contract = contract_on(company, local.date())
    if contract is None:
        problems.append(
            "Esa fecha no está dentro de un contrato vigente con la empresa. "
            "Comunícate con el ingeniero para renovarlo."
        )

    if overlapping_visit(start, minutes, exclude_pk) is not None:
        problems.append("El ingeniero ya tiene una visita en ese horario. Elige otra hora.")
    return problems


def combine(day, hour) -> datetime:
    return timezone.make_aware(datetime.combine(day, hour))
