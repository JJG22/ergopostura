from django.conf import settings
from django.db import models

from apps.companies.models import Position
from apps.core.models import TimeStampedModel


class Visit(TimeStampedModel):
    """Constancia de una visita acordada (RF-006). No es una agenda ni envia notificaciones.

    Solo se guarda el puesto: la sede y la empresa salen de la jerarquia, de modo que
    una visita no puede quedar con un puesto de una empresa y la sede de otra.
    """

    position = models.ForeignKey(
        Position, verbose_name="puesto de trabajo", on_delete=models.PROTECT, related_name="visits"
    )
    scheduled_at = models.DateTimeField("fecha y hora")
    contact_name = models.CharField("contacto de la empresa", max_length=150, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_visits",
    )

    class Meta:
        verbose_name = "visita"
        verbose_name_plural = "visitas"
        ordering = ["scheduled_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["position", "scheduled_at"], name="visit_unique_position_datetime"),
        ]

    def __str__(self):
        return f"{self.position} · {self.scheduled_at:%Y-%m-%d %H:%M}"

    @property
    def area(self):
        return self.position.area

    @property
    def site(self):
        return self.position.area.site

    @property
    def company(self):
        return self.position.area.site.company
