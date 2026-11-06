"""Convierte el elemento elegido en el arbol en los datos que muestra el panel de detalle.

La busqueda ocurre solo dentro del arbol de la empresa abierta, de modo que una clave
de otra empresa en la URL no encuentra nada y se vuelve a mostrar la empresa.
"""
from dataclasses import dataclass

from django.urls import reverse

from .models import Area, Company, Position, Site


@dataclass(frozen=True)
class Selection:
    kind: str
    icon: str
    name: str
    path: list[str]
    details: list[tuple[str, str]]
    edit_url: str
    add_url: str = ""
    add_label: str = ""
    key: str = "empresa"


def _company(company: Company) -> Selection:
    return Selection(
        kind="EMPRESA",
        icon="building-complex",
        name=company.name,
        path=[company.name],
        details=[
            ("NIT", company.nit_display),
            ("Municipio", company.municipality.name),
            ("Departamento", company.municipality.department.name),
            ("Estado", "Activa" if company.is_active else "Inactiva"),
        ],
        edit_url=reverse("companies:update", args=[company.pk]),
        add_url=reverse("companies:site_create", args=[company.pk]),
        add_label="Agregar sede",
    )


def _site(company: Company, site: Site) -> Selection:
    return Selection(
        kind="SEDE",
        icon="map-pin",
        name=site.name,
        path=[company.name, site.name],
        details=[
            ("Municipio", site.municipality.name),
            ("Departamento", site.municipality.department.name),
            ("Dirección", site.address or "Sin registrar"),
            ("Áreas", str(len(site.areas.all()))),
        ],
        edit_url=reverse("companies:site_update", args=[site.pk]),
        add_url=reverse("companies:area_create", args=[site.pk]),
        add_label="Agregar área",
        key=site.node_key,
    )


def _area(company: Company, site: Site, area: Area) -> Selection:
    return Selection(
        kind="ÁREA",
        icon="layout-list",
        name=area.name,
        path=[company.name, site.name, area.name],
        details=[
            ("Sede", site.name),
            ("Descripción", area.description or "Sin registrar"),
            ("Puestos", str(len(area.positions.all()))),
        ],
        edit_url=reverse("companies:area_update", args=[area.pk]),
        add_url=reverse("companies:position_create", args=[area.pk]),
        add_label="Agregar puesto",
        key=area.node_key,
    )


def _position(company: Company, site: Site, area: Area, position: Position) -> Selection:
    return Selection(
        kind="PUESTO DE TRABAJO",
        icon="users",
        name=position.name,
        path=[company.name, site.name, area.name, position.name],
        details=[
            ("Sede", site.name),
            ("Área", area.name),
            ("Descripción", position.description or "Sin registrar"),
        ],
        edit_url=reverse("companies:position_update", args=[position.pk]),
        key=position.node_key,
    )


def select_node(company: Company, key: str | None) -> Selection:
    """Requiere la empresa cargada con selectors.with_structure para no repetir consultas."""
    for site in company.sites.all():
        if site.node_key == key:
            return _site(company, site)
        for area in site.areas.all():
            if area.node_key == key:
                return _area(company, site, area)
            for position in area.positions.all():
                if position.node_key == key:
                    return _position(company, site, area, position)
    return _company(company)


def structure_counts(company: Company) -> dict[str, int]:
    sites = list(company.sites.all())
    areas = [area for site in sites for area in site.areas.all()]
    positions = [position for area in areas for position in area.positions.all()]
    return {"sites": len(sites), "areas": len(areas), "positions": len(positions)}
