from itertools import count

from django.contrib.auth import get_user_model

from apps.accounts.models import Role
from apps.companies.models import Area, Company, Position, Site

_sequence = count(1)
PASSWORD = "Prueba-segura-2026"


def make_company(name="Café Montaña S.A.S.", nit=None, **fields):
    nit = nit or str(800_000_000 + next(_sequence))
    defaults = {"city": "Armenia", "department": "Quindío"}
    return Company.objects.create(name=name, nit=nit, **{**defaults, **fields})


def make_site(company=None, name="Planta Armenia"):
    return Site.objects.create(
        company=company or make_company(), name=name, city="Armenia", department="Quindío"
    )


def make_area(site=None, name="Empaque"):
    return Area.objects.create(site=site or make_site(), name=name)


def make_position(area=None, name="Operario de empaque"):
    return Position.objects.create(area=area or make_area(), name=name)


def make_user(role=Role.EVALUATOR, company=None, **fields):
    email = fields.pop("email", f"usuario{next(_sequence)}@ergopostura.test")
    if role == Role.COMPANY and company is None:
        company = make_company()
    return get_user_model().objects.create_user(
        email=email, password=PASSWORD, role=role, company=company, **fields
    )
