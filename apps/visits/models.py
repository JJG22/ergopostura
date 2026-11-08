"""Visitas del ingeniero a las empresas cliente.

La empresa agenda la visita en una de sus sedes; el ingeniero la atiende y registra si se
hizo. Solo despues de una visita realizada se puede crear una evaluacion: sin visita no
hubo observacion en campo y no puede haber resultado.

El estado guardado es lo que paso (programada, realizada, cancelada). El nivel que se
muestra (cercana, hoy, en curso, por cerrar) se calcula con la hora actual, para que
nunca quede desactualizado.
"""
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.companies.models import Site
from apps.core.models import TimeStampedModel

# Hasta cuantos dias antes una visita programada se considera cercana.
NEAR_DAYS = 3


@dataclass(frozen=True)
class Level:
    key: str
    label: str
    tone: str  # clase de color en la interfaz


LEVELS = {
    "programada": Level("programada", "Programada", "blue"),
    "cercana": Level("cercana", "Cercana", "amber"),
    "hoy": Level("hoy", "Hoy", "orange"),
    "en_curso": Level("en_curso", "En curso", "teal"),
    "por_cerrar": Level("por_cerrar", "Por cerrar", "red"),
    "realizada": Level("realizada", "Realizada", "green"),
    "cancelada": Level("cancelada", "Cancelada", "neutral"),
}


class ScheduleLock(models.Model):
    """Una sola fila que se bloquea mientras se agenda. No guarda ningun dato."""

    ROW = 1

    class Meta:
        verbose_name = "bloqueo de agenda"


class Visit(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "programada", "Programada"
        COMPLETED = "realizada", "Realizada"
        CANCELLED = "cancelada", "Cancelada"

    DURATION_CHOICES = [(60, "1 hora"), (120, "2 horas"), (180, "3 horas"), (240, "4 horas"), (480, "Jornada (8 horas)")]

    site = models.ForeignKey(Site, verbose_name="sede", on_delete=models.PROTECT, related_name="visits")
    scheduled_at = models.DateTimeField("fecha y hora")
    duration_minutes = models.PositiveSmallIntegerField("duración", choices=DURATION_CHOICES, default=120)
    purpose = models.TextField(
        "motivo de la visita",
        help_text="Qué áreas o puestos quieren que se evalúen, o qué necesitan del servicio.",
    )
    contact_name = models.CharField("persona que recibe la visita", max_length=150)
    contact_phone = models.CharField("teléfono de contacto", max_length=30, blank=True)
    status = models.CharField("estado", max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="agendada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_visits",
        editable=False,
    )
    completed_at = models.DateTimeField("registrada como realizada el", null=True, blank=True, editable=False)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_visits",
        editable=False,
    )
    completion_notes = models.TextField("observaciones de la visita", blank=True)
    cancelled_at = models.DateTimeField("cancelada el", null=True, blank=True, editable=False)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="cancelada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_visits",
        editable=False,
    )
    cancellation_reason = models.CharField("motivo de la cancelación", max_length=300, blank=True)

    class Meta:
        verbose_name = "visita"
        verbose_name_plural = "visitas"
        ordering = ["scheduled_at", "pk"]
        constraints = [
            models.CheckConstraint(
                name="visit_completed_has_date",
                condition=~Q(status="realizada") | Q(completed_at__isnull=False),
            ),
            models.CheckConstraint(
                name="visit_cancelled_has_reason",
                condition=~Q(status="cancelada") | (Q(cancelled_at__isnull=False) & ~Q(cancellation_reason="")),
            ),
            models.CheckConstraint(name="visit_duration_positive", condition=Q(duration_minutes__gt=0)),
        ]
        indexes = [models.Index(fields=["status", "scheduled_at"], name="visit_status_start")]

    def __str__(self):
        return f"{self.company} · {timezone.localtime(self.scheduled_at):%Y-%m-%d %H:%M}"

    @property
    def company(self):
        return self.site.company

    @property
    def ends_at(self):
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)

    @property
    def is_scheduled(self) -> bool:
        return self.status == self.Status.SCHEDULED

    @property
    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED

    def level_at(self, now) -> Level:
        if self.status == self.Status.COMPLETED:
            return LEVELS["realizada"]
        if self.status == self.Status.CANCELLED:
            return LEVELS["cancelada"]
        if self.ends_at <= now:
            return LEVELS["por_cerrar"]
        if self.scheduled_at <= now:
            return LEVELS["en_curso"]
        if timezone.localdate(self.scheduled_at) == timezone.localdate(now):
            return LEVELS["hoy"]
        if self.scheduled_at - now <= timedelta(days=NEAR_DAYS):
            return LEVELS["cercana"]
        return LEVELS["programada"]

    @property
    def level(self) -> Level:
        return self.level_at(timezone.now())
