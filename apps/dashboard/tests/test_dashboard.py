from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.core.tests.factories import (
    at,
    completed_visit,
    make_company,
    make_contract,
    make_position,
    make_site,
    make_user,
    make_visit,
)
from apps.dashboard.panels import PANELS
from apps.dashboard.views import greeting


class GreetingTests(SimpleTestCase):
    def test_changes_with_the_hour(self):
        self.assertEqual(greeting(8), "Buenos días")
        self.assertEqual(greeting(15), "Buenas tardes")
        self.assertEqual(greeting(21), "Buenas noches")


class RoleDashboardTests(TestCase):
    url = "/"

    def login(self, role, **fields):
        if role == Role.COMPANY:
            fields.setdefault("company", make_company(name="Mi empresa"))
        self.client.force_login(make_user(role=role, **fields))
        return self.client.get(self.url)

    def test_every_role_has_its_panel(self):
        self.assertEqual(set(PANELS), set(Role))
        expected = {
            Role.ADMIN: "dashboard/admin.html",
            Role.ENGINEER: "dashboard/engineer.html",
            Role.COMPANY: "dashboard/company.html",
        }
        for role, template in expected.items():
            response = self.login(role)
            self.assertEqual(response.status_code, 200, role)
            self.assertTemplateUsed(response, template)

    def test_support_is_guided_to_create_the_engineer_and_sees_no_business_data(self):
        make_position()
        response = self.login(Role.ADMIN)
        self.assertContains(response, "Crea la cuenta del ingeniero industrial")
        self.assertNotIn("recent_evaluations", response.context)
        self.assertNotIn("totals", response.context)
        make_user(role=Role.ENGINEER)
        self.assertNotContains(self.login(Role.ADMIN), "Crea la cuenta del ingeniero industrial")

    def test_engineer_sees_the_first_steps_until_the_flow_is_complete(self):
        response = self.login(Role.ENGINEER)
        self.assertTrue(response.context["onboarding"])
        self.assertContains(response, "Primeros pasos")

    def test_engineer_is_told_what_needs_attention(self):
        position = make_position()
        company = position.company
        make_contract(company, start=timezone.localdate() - timedelta(days=340), end=timezone.localdate() + timedelta(days=10))
        make_visit(position.area.site, at(timezone.localdate() - timedelta(days=1)))
        completed_visit(position)
        response = self.login(Role.ENGINEER)
        self.assertEqual(response.context["to_close_count"], 1)
        self.assertEqual(len(response.context["without_evaluation"]), 1)
        self.assertEqual(len(response.context["expiring_contracts"]), 1)
        self.assertContains(response, "vence el")

    def test_company_only_sees_its_data_and_its_contract(self):
        own = make_company(name="Mi empresa")
        other = make_company(name="Empresa ajena")
        make_contract(other)
        make_site(other)
        response = self.login(Role.COMPANY, company=own)
        self.assertContains(response, "Mi empresa")
        self.assertNotContains(response, "Empresa ajena")
        self.assertIsNone(response.context["contract"])
        self.assertContains(response, "No hay un contrato vigente")
        self.assertEqual(response.context["counts"], {"sites": 0, "areas": 0, "positions": 0, "workers": 0})

        contract = make_contract(own)
        response = self.login(Role.COMPANY, company=own)
        self.assertEqual(response.context["contract"], contract)
        self.assertContains(response, contract.display_code)

    def test_dashboard_requires_login(self):
        self.assertRedirects(self.client.get(reverse("dashboard:home")), "/ingresar/?next=/")
