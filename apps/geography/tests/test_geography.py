from django.test import TestCase

from apps.companies.forms import CompanyForm
from apps.core.tests.factories import make_company, municipality
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


