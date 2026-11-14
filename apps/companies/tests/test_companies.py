from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.api.presenters import navigation
from apps.companies.forms import CompanyForm
from apps.companies.models import Site
from apps.core.tests.factories import (
    make_area,
    make_company,
    make_position,
    make_site,
    make_user,
    municipality,
)


def location(name="Armenia", department="Quindío"):
    place = municipality(name, department)
    return {"department": place.department_id, "municipality": place.pk}


def valid_company():
    return {"name": "Café Montaña S.A.S.", "nit": "900.123.456-8", **location()}


class DatabaseIntegrityTests(TestCase):
    def test_duplicate_nit_is_rejected_by_database(self):
        make_company(nit="900123456")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_company(nit="900123456")

    def test_malformed_nit_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_company(nit="90012345A")

    def test_child_names_are_unique_per_parent_ignoring_case(self):
        site = make_site()
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_site(site.company, name=site.name.upper())
        area = make_area(site)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_area(site, name=area.name.upper())
        position = make_position(area)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_position(area, name=position.name.upper())

    def test_same_name_is_allowed_under_different_parents(self):
        make_site(make_company(), name="Principal")
        make_site(make_company(), name="Principal")
        self.assertEqual(Site.objects.filter(name="Principal").count(), 2)

    def test_parents_with_children_cannot_be_deleted(self):
        position = make_position()
        for parent in (position.area, position.area.site, position.company):
            with self.assertRaises(ProtectedError):
                parent.delete()

    def test_position_reaches_its_company_through_the_hierarchy(self):
        company = make_company()
        position = make_position(make_area(make_site(company)))
        self.assertEqual(position.company, company)


class CompanyFormTests(TestCase):
    def test_duplicate_nit_message(self):
        make_company(nit="900123456")
        form = CompanyForm(data=valid_company())
        self.assertFalse(form.is_valid())
        self.assertIn("Ya existe una empresa con este NIT.", form.errors["nit"])

    def test_same_nit_written_differently_is_still_a_duplicate(self):
        make_company(nit="900123456")
        for raw in ("900123456", "900123456-8", "900 123 456"):
            form = CompanyForm(data={**valid_company(), "nit": raw})
            self.assertFalse(form.is_valid(), raw)
            self.assertIn("Ya existe una empresa con este NIT.", form.errors["nit"])

    def test_nit_is_saved_normalized(self):
        form = CompanyForm(data=valid_company())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().nit, "900123456")

    def test_missing_nit(self):
        form = CompanyForm(data={**valid_company(), "nit": "  "})
        self.assertIn("El NIT es obligatorio.", form.errors["nit"])

    def test_editing_a_company_keeps_its_own_nit(self):
        company = make_company(nit="900123456")
        form = CompanyForm(data={**valid_company(), "is_active": "on"}, instance=company)
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_cannot_take_the_nit_of_another_company(self):
        make_company(nit="900123456")
        other = make_company(nit="901234567")
        form = CompanyForm(data=valid_company(), instance=other)
        self.assertIn("Ya existe una empresa con este NIT.", form.errors["nit"])

    def test_new_company_has_no_active_field_and_starts_active(self):
        form = CompanyForm(data=valid_company())
        self.assertNotIn("is_active", form.fields)
        self.assertTrue(form.save().is_active)

    def test_spaces_in_name_are_normalized(self):
        form = CompanyForm(data={**valid_company(), "name": "  Café   Montaña  "})
        self.assertEqual(form.save().name, "Café Montaña")


class AccessControlTests(TestCase):
    """Matriz de quien puede hacer que, recorriendo todos los roles."""

    @classmethod
    def setUpTestData(cls):
        cls.position = make_position()
        cls.area = cls.position.area
        cls.site = cls.area.site
        cls.company = cls.site.company
        cls.other_company = make_company(name="Otra empresa")

    def manage_urls(self):
        return [
            reverse("companies:create"),
            reverse("companies:update", args=[self.company.pk]),
            reverse("companies:site_create", args=[self.company.pk]),
            reverse("companies:site_update", args=[self.site.pk]),
            reverse("companies:area_create", args=[self.site.pk]),
            reverse("companies:area_update", args=[self.area.pk]),
            reverse("companies:position_create", args=[self.area.pk]),
            reverse("companies:position_update", args=[self.position.pk]),
        ]

    def read_urls(self):
        return [reverse("companies:list"), reverse("companies:detail", args=[self.company.pk])]







    def labels(self, user):
        return [item["label"] for item in navigation(user)]

    def test_navigation_only_shows_what_the_role_can_open(self):
        self.assertEqual(self.labels(make_user(role=Role.ADMIN)), ["Panel principal", "Usuarios"])
        self.assertEqual(
            self.labels(make_user(role=Role.ENGINEER)),
            ["Panel principal", "Empresas", "Contratos", "Visitas", "Evaluaciones", "Indicadores",
             "Tareas pendientes", "Accesos de empresas"],
        )
        self.assertEqual(
            self.labels(make_user(role=Role.COMPANY, company=self.company)),
            ["Panel principal", "Visitas", "Evaluaciones", "Indicadores", "Tareas pendientes"],
        )







class WorkerTests(TestCase):
    def setUp(self):
        self.engineer = make_user(role=Role.ENGINEER)
        self.position = make_position()
        self.company = self.position.company
        self.client.force_login(self.engineer)







