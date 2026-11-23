from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.api.presenters import navigation
from apps.companies.forms import CompanyForm
from apps.companies.models import Company, Site
from apps.companies.selectors import search_companies
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
    return {"person_type": "juridica", "name": "Café Montaña S.A.S.", "nit": "900.123.456-8", **location()}


class DatabaseIntegrityTests(TestCase):
    def test_duplicate_nit_is_rejected_by_database(self):
        make_company(nit="900123456")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_company(nit="900123456")

    def test_malformed_nit_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_company(nit="90012345A")

    def test_natural_person_needs_cedula_and_no_nit(self):
        place = municipality()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Company.objects.create(name="Jorge Cárdenas", person_type="natural", nit="900123456", municipality=place)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Company.objects.create(name="Jorge Cárdenas", person_type="natural", municipality=place)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Company.objects.create(name="Café", person_type="juridica", cedula="1094887654", municipality=place)

    def test_duplicate_cedula_is_rejected_by_database(self):
        place = municipality()
        Company.objects.create(name="Jorge Cárdenas", person_type="natural", cedula="1094887654", municipality=place)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Company.objects.create(name="Otro", person_type="natural", cedula="1094887654", municipality=place)

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









def natural_company(**changes):
    return {"person_type": "natural", "name": "Jorge Iván Cárdenas", "cedula": "1.094.887.654", **location(), **changes}


class NaturalPersonFormTests(TestCase):
    def test_person_type_is_required(self):
        form = CompanyForm(data={**valid_company(), "person_type": ""})
        self.assertIn("Elige si la empresa es persona natural o jurídica.", form.errors["person_type"])

    def test_natural_person_is_saved_with_cedula_only(self):
        form = CompanyForm(data=natural_company(nit="900.123.456-8"))
        self.assertTrue(form.is_valid(), form.errors)
        company = form.save()
        self.assertEqual((company.person_type, company.cedula, company.nit), ("natural", "1094887654", None))
        self.assertEqual((company.document_label, company.document_display), ("Cédula", "1.094.887.654"))

    def test_legal_person_ignores_a_cedula(self):
        form = CompanyForm(data={**valid_company(), "cedula": "1094887654"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual((form.save().nit, Company.objects.get().cedula), ("900123456", None))

    def test_missing_cedula(self):
        form = CompanyForm(data=natural_company(cedula=" "))
        self.assertIn("La cédula es obligatoria.", form.errors["cedula"])

    def test_invalid_cedula(self):
        for raw in ("12", "0123456", "10948876AB", "12345678901"):
            form = CompanyForm(data=natural_company(cedula=raw))
            self.assertFalse(form.is_valid(), raw)
            self.assertIn("cedula", form.errors)

    def test_duplicate_cedula_message(self):
        CompanyForm(data=natural_company()).save()
        form = CompanyForm(data=natural_company(name="Otra persona", cedula="1094887654"))
        self.assertIn("Ya existe una empresa con esta cédula.", form.errors["cedula"])

    def test_same_number_cannot_be_nit_and_cedula(self):
        # El NIT de una persona natural es su cedula: seria el mismo cliente dos veces.
        make_company(name="Café Montaña S.A.S.", nit="1094887654")
        form = CompanyForm(data=natural_company())
        self.assertIn("Este número ya está registrado como el NIT de Café Montaña S.A.S.", form.errors["cedula"])

    def test_changing_the_person_type_keeps_only_the_new_document(self):
        company = make_company(nit="900123456")
        form = CompanyForm(data={**natural_company(), "is_active": "on"}, instance=company)
        self.assertTrue(form.is_valid(), form.errors)
        company = form.save()
        self.assertEqual((company.person_type, company.nit, company.cedula), ("natural", None, "1094887654"))

    def test_search_finds_a_natural_person_by_cedula(self):
        CompanyForm(data=natural_company()).save()
        engineer = make_user(role=Role.ENGINEER)
        self.assertEqual([c.name for c in search_companies(engineer, "1.094.887")], ["Jorge Iván Cárdenas"])
