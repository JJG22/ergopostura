"""Contratos de servicio entre el ingeniero industrial y cada empresa cliente.

Una empresa tiene un solo contrato a la vez: las vigencias de sus contratos no se cruzan.
Asi, al renovar se registra un contrato nuevo y el anterior queda como historia.

El PDF se guarda en MySQL, como las fotografias: el servidor no tiene disco
persistente y el documento solo se entrega a quien puede ver el contrato.
"""
from calendar import monthrange
from datetime import date, timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.companies.models import Company
from apps.core.models import TimeStampedModel

# Desde cuantos dias antes del vencimiento se avisa que el contrato esta por terminar.
EXPIRING_SOON_DAYS = 30


class ContractStatus(models.TextChoices):
    UPCOMING = "por_iniciar", "Por iniciar"
    ACTIVE = "vigente", "Vigente"
    EXPIRING = "por_vencer", "Por vencer"
    EXPIRED = "vencido", "Vencido"


class Contract(TimeStampedModel):
    class Kind(models.TextChoices):
        SERVICES = "prestacion_servicios", "Prestación de servicios"
        CONSULTING = "consultoria", "Consultoría"
        WORK = "obra_labor", "Obra o labor determinada"
        FRAMEWORK = "marco", "Contrato marco"
        OTHER = "otro", "Otro"

    company = models.ForeignKey(
        Company, verbose_name="empresa", on_delete=models.PROTECT, related_name="contracts"
    )
    code = models.CharField("número o código", max_length=50, blank=True)
    kind = models.CharField("tipo de contrato", max_length=30, choices=Kind.choices, default=Kind.SERVICES)
    service = models.TextField(
        "servicio contratado", help_text="Qué se evaluará y con qué alcance, según el contrato."
    )
    start_date = models.DateField("inicio de la vigencia")
    end_date = models.DateField("fin de la vigencia")
    value = models.DecimalField(
        "valor total (COP)",
        max_digits=14,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    responsible_name = models.CharField("encargado por la empresa", max_length=150)
    responsible_role = models.CharField("cargo del encargado", max_length=120, blank=True)
    responsible_email = models.EmailField("correo del encargado", blank=True)
    responsible_phone = models.CharField("teléfono del encargado", max_length=30, blank=True)
    notes = models.TextField("notas", blank=True)

    file_data = models.BinaryField("documento", editable=False)
    file_name = models.CharField("archivo", max_length=255, editable=False)
    file_size = models.PositiveIntegerField("tamaño", editable=False)
    file_sha256 = models.CharField(max_length=64, editable=False)

    # Lo que leyo la IA del documento. Se guarda aparte de los datos registrados: el
    # ingeniero los confirma o corrige, y la comparacion deja ver cualquier diferencia.
    ai_summary = models.JSONField("resumen de la IA", default=dict, blank=True, editable=False)
    ai_model = models.CharField("modelo de IA", max_length=60, blank=True, editable=False)
    ai_generated_at = models.DateTimeField("resumen generado el", null=True, blank=True, editable=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_contracts",
        editable=False,
    )

    class Meta:
        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        ordering = ["-start_date", "-pk"]
        constraints = [
            models.CheckConstraint(
                name="contract_dates_in_order",
                condition=Q(end_date__gte=models.F("start_date")),
                violation_error_message="El fin de la vigencia no puede ser anterior al inicio.",
            ),
        ]

    def __str__(self):
        return f"{self.display_code} · {self.company}"

    @property
    def display_code(self) -> str:
        return self.code or f"CT-{self.pk:04d}"

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def duration_label(self) -> str:
        return duration_label(self.start_date, self.end_date)

    def status_on(self, day: date) -> ContractStatus:
        if day < self.start_date:
            return ContractStatus.UPCOMING
        if day > self.end_date:
            return ContractStatus.EXPIRED
        if self.end_date - day <= timedelta(days=EXPIRING_SOON_DAYS):
            return ContractStatus.EXPIRING
        return ContractStatus.ACTIVE

    def days_left(self, day: date) -> int:
        return (self.end_date - day).days

    def covers(self, day: date) -> bool:
        return self.start_date <= day <= self.end_date


class ContractReading(TimeStampedModel):
    """Lectura de la IA de un PDF, por su huella SHA-256.

    El formulario pide la lectura antes de guardar el contrato, para llenar los campos.
    Al guardar, la lectura del mismo archivo se asocia al contrato sin pagarla dos veces.
    """

    sha256 = models.CharField(max_length=64, unique=True)
    summary = models.JSONField(default=dict)
    model = models.CharField(max_length=60)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "lectura de contrato"
        verbose_name_plural = "lecturas de contratos"


def duration_label(start: date, end: date) -> str:
    """Duracion en meses y dias calendario, contando ambos extremos, como en un contrato."""
    end_exclusive = end + timedelta(days=1)
    months = (end_exclusive.year - start.year) * 12 + (end_exclusive.month - start.month)
    if _add_months(start, months) > end_exclusive:
        months -= 1
    days = (end_exclusive - _add_months(start, months)).days
    parts = []
    if months:
        parts.append(f"{months} {'mes' if months == 1 else 'meses'}")
    if days or not parts:
        parts.append(f"{days} {'día' if days == 1 else 'días'}")
    return " y ".join(parts)


def _add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))
