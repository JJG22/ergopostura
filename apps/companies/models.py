"""Jerarquia empresa > sede > area > puesto.

Cada nivel conoce solo a su padre, y la empresa de un puesto se obtiene recorriendo
esa cadena. Al no duplicar el dato, una evaluacion no podra quedar asociada a un
puesto de una empresa y presentarse como de otra (RNF-002).

PROTECT impide borrar un nivel con hijos, para no perder historia (RNF-001).
"""
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.core.models import TimeStampedModel
from apps.geography.models import Municipality

from .nit import Nit


class Company(TimeStampedModel):
    name = models.CharField("razón social", max_length=200)
    nit = models.CharField(
        "NIT",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^[1-9][0-9]{5,9}$", "Escribe un NIT válido.")],
        error_messages={"unique": "Ya existe una empresa con este NIT."},
    )
    municipality = models.ForeignKey(
        Municipality, verbose_name="municipio", on_delete=models.PROTECT, related_name="companies"
    )
    is_active = models.BooleanField("empresa activa", default=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(
                name="company_nit_format",
                condition=Q(nit__regex=r"^[1-9][0-9]{5,9}$"),
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def nit_display(self) -> str:
        return str(Nit(self.nit))

    @property
    def node_key(self) -> str:
        return "empresa"


class Site(TimeStampedModel):
    company = models.ForeignKey(
        Company, verbose_name="empresa", on_delete=models.PROTECT, related_name="sites"
    )
    name = models.CharField("nombre", max_length=150)
    municipality = models.ForeignKey(
        Municipality, verbose_name="municipio", on_delete=models.PROTECT, related_name="sites"
    )
    address = models.CharField("dirección", max_length=200, blank=True)

    class Meta:
        verbose_name = "sede"
        verbose_name_plural = "sedes"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint("company", Lower("name"), name="site_unique_name_in_company"),
        ]

    def __str__(self):
        return self.name

    @property
    def node_key(self) -> str:
        return f"sede-{self.pk}"


class Area(TimeStampedModel):
    site = models.ForeignKey(Site, verbose_name="sede", on_delete=models.PROTECT, related_name="areas")
    name = models.CharField("nombre", max_length=150)
    description = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "área"
        verbose_name_plural = "áreas"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint("site", Lower("name"), name="area_unique_name_in_site"),
        ]

    def __str__(self):
        return self.name

    @property
    def company(self) -> Company:
        return self.site.company

    @property
    def node_key(self) -> str:
        return f"area-{self.pk}"


class Position(TimeStampedModel):
    area = models.ForeignKey(Area, verbose_name="área", on_delete=models.PROTECT, related_name="positions")
    name = models.CharField("nombre", max_length=150)
    description = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "puesto de trabajo"
        verbose_name_plural = "puestos de trabajo"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint("area", Lower("name"), name="position_unique_name_in_area"),
        ]

    def __str__(self):
        return self.name

    @property
    def company(self) -> Company:
        return self.area.site.company

    @property
    def node_key(self) -> str:
        return f"puesto-{self.pk}"


class Worker(TimeStampedModel):
    """Persona que ocupa un puesto. Son datos personales (Ley 1581 de 2012): solo los ven
    el ingeniero y la propia empresa, y nunca aparecen en indicadores agregados.
    """

    class DocumentType(models.TextChoices):
        CC = "CC", "Cédula de ciudadanía"
        CE = "CE", "Cédula de extranjería"
        PPT = "PPT", "Permiso por protección temporal"
        PA = "PA", "Pasaporte"
        TI = "TI", "Tarjeta de identidad"

    position = models.ForeignKey(
        Position, verbose_name="puesto de trabajo", on_delete=models.PROTECT, related_name="workers"
    )
    first_name = models.CharField("nombres", max_length=120)
    last_name = models.CharField("apellidos", max_length=120)
    document_type = models.CharField(
        "tipo de documento", max_length=3, choices=DocumentType.choices, default=DocumentType.CC
    )
    document_number = models.CharField(
        "número de documento",
        max_length=20,
        validators=[RegexValidator(r"^[A-Za-z0-9]{4,20}$", "Escribe solo letras y números, sin puntos.")],
    )
    hired_on = models.DateField("fecha de ingreso al puesto", null=True, blank=True)
    is_active = models.BooleanField("trabaja actualmente en el puesto", default=True)

    class Meta:
        verbose_name = "trabajador"
        verbose_name_plural = "trabajadores"
        ordering = ["last_name", "first_name", "pk"]
        constraints = [
            # La misma persona no se registra dos veces en un puesto. Que no se repita en la
            # empresa lo valida el formulario, porque la empresa sale de la jerarquia.
            models.UniqueConstraint(
                fields=["position", "document_type", "document_number"], name="worker_unique_document_in_position"
            ),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def company(self) -> Company:
        return self.position.area.site.company

    @property
    def document_display(self) -> str:
        return f"{self.document_type} {self.document_number}"
