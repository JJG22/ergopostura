"""Departamentos y municipios de Colombia, tomados de api-colombia.com.

Se guardan en la base para que los formularios no dependan de que la API responda.
api_id es el identificador de la API: permite actualizar el catalogo sin duplicar.
PROTECT impide borrar un municipio que ya use una empresa o una sede.
"""
from django.db import models
from django.db.models.functions import Lower


class Department(models.Model):
    api_id = models.PositiveIntegerField("id en la API", unique=True)
    name = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Municipality(models.Model):
    api_id = models.PositiveIntegerField("id en la API", unique=True)
    department = models.ForeignKey(
        Department, verbose_name="departamento", on_delete=models.PROTECT, related_name="municipalities"
    )
    name = models.CharField("nombre", max_length=100)

    class Meta:
        verbose_name = "municipio"
        verbose_name_plural = "municipios"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint("department", Lower("name"), name="municipality_unique_name_in_department"),
        ]

    def __str__(self):
        return self.name

    @property
    def full_name(self) -> str:
        """«Armenia, Quindío». Bogotá es a la vez municipio y departamento: no se repite."""
        department = self.department.name
        if self.name.lower().startswith(department.lower()):
            return self.name
        return f"{self.name}, {department}"
