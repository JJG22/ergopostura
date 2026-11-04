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

from .constants import DEPARTMENT_CHOICES
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
    city = models.CharField("ciudad", max_length=100)
    department = models.CharField("departamento", max_length=60, choices=DEPARTMENT_CHOICES)
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
    city = models.CharField("ciudad", max_length=100)
    department = models.CharField("departamento", max_length=60, choices=DEPARTMENT_CHOICES)
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
