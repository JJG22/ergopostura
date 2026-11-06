from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.companies.forms import CompanyForm
from apps.core.tests.factories import make_company, make_user, municipality
from apps.geography import catalog
from apps.geography.models import Department, Municipality


class CatalogTests(TestCase):
    def test_migration_loads_every_department_and_municipality(self):
        snapshot = catalog.read_snapshot()
        self.assertEqual(Department.objects.count(), len(snapshot["departments"]))
        self.assertEqual(Municipality.objects.count(), len(snapshot["municipalities"]))
        self.assertEqual(Department.objects.count(), 33)

    def test_loading_twice_updates_without_duplicating(self):
        data = catalog.read_snapshot()
        data["municipalities"][0]["name"] = "Nombre corregido"
        created = catalog.load(data, Department, Municipality)
        self.assertEqual(created, {"departments": 0, "municipalities": 0})
        self.assertTrue(Municipality.objects.filter(name="Nombre corregido").exists())

    def test_normalize_ignores_accents_case_and_spaces(self):
        self.assertEqual(catalog.normalize("  CALARCÁ "), catalog.normalize("calarca"))

    def test_full_name_does_not_repeat_bogota(self):
        self.assertEqual(municipality("Armenia", "Quindío").full_name, "Armenia, Quindío")
        self.assertEqual(Municipality.objects.get(department__name="Bogotá").full_name, "Bogotá D.C.")


class LocationFormTests(TestCase):
    def test_municipality_must_belong_to_chosen_department(self):
        pereira = municipality("Pereira", "Risaralda")
        quindio = municipality().department
        form = CompanyForm(
            data={"name": "X S.A.S.", "nit": "900123456", "department": quindio.pk, "municipality": pereira.pk}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("municipality", form.errors)

    def test_municipalities_wait_for_a_department(self):
        form = CompanyForm()
        self.assertFalse(form.fields["municipality"].queryset.exists())

    def test_editing_preselects_the_department(self):
        company = make_company()
        form = CompanyForm(instance=company)
        self.assertEqual(form.initial["department"], company.municipality.department_id)
        self.assertTrue(form.fields["municipality"].queryset.filter(pk=company.municipality_id).exists())


class MunicipalityOptionsViewTests(TestCase):
    url = reverse("geography:municipalities")

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_lists_only_municipalities_of_the_department(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        quindio = municipality().department
        response = self.client.get(self.url, {"department": quindio.pk})
        self.assertContains(response, "Calarcá")
        self.assertNotContains(response, "Pereira")

    def test_invalid_department_returns_waiting_option(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        response = self.client.get(self.url, {"department": "abc"})
        self.assertContains(response, "Selecciona primero un departamento")
