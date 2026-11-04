from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.core.tests.factories import make_company, make_position, make_user
from apps.dashboard.panels import PANELS
from apps.dashboard.views import greeting


class GreetingTests(SimpleTestCase):
    def test_changes_with_the_hour(self):
        self.assertEqual(greeting(8), "Buenos días")
        self.assertEqual(greeting(15), "Buenas tardes")
        self.assertEqual(greeting(21), "Buenas noches")


class RoleDashboardTests(TestCase):
    url = "/"

    def test_every_role_has_a_panel_that_renders(self):
        self.assertEqual(set(PANELS), set(Role))
        for role in Role:
            self.client.force_login(make_user(role=role))
            self.assertEqual(self.client.get(self.url).status_code, 200, role)

    def test_each_role_gets_its_own_view(self):
        expected = {
            Role.ADMIN: "dashboard/admin.html",
            Role.ENGINEER: "dashboard/engineer.html",
            Role.COMPANY: "dashboard/company.html",
            Role.EVALUATOR: "dashboard/evaluator.html",
            Role.RESULTS: "dashboard/pending.html",
            Role.TASKS: "dashboard/pending.html",
        }
        for role, template in expected.items():
            self.client.force_login(make_user(role=role))
            self.assertTemplateUsed(self.client.get(self.url), template)

    def test_only_admin_sees_user_statistics(self):
        make_position()
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertContains(self.client.get(self.url), "Usuarios por rol")

        for role in (Role.ENGINEER, Role.COMPANY, Role.EVALUATOR, Role.RESULTS, Role.TASKS):
            self.client.force_login(make_user(role=role))
            response = self.client.get(self.url)
            self.assertNotContains(response, "Usuarios por rol")
            self.assertNotIn("users_by_role", response.context)

    def test_company_user_only_sees_data_of_its_company(self):
        own = make_company(name="Mi empresa")
        make_company(name="Empresa ajena")
        make_position()
        self.client.force_login(make_user(role=Role.COMPANY, company=own))
        response = self.client.get(self.url)
        self.assertContains(response, "Mi empresa")
        self.assertNotContains(response, "Empresa ajena")
        self.assertEqual(response.context["counts"], {"sites": 0, "areas": 0, "positions": 0})

    def test_admin_totals_are_real(self):
        make_position()
        make_company(name="Sin estructura")
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertEqual(
            self.client.get(self.url).context["totals"],
            {"companies": 2, "sites": 1, "areas": 1, "positions": 1},
        )

    def test_dashboard_requires_login(self):
        self.assertRedirects(self.client.get(reverse("dashboard:home")), "/ingresar/?next=/")
