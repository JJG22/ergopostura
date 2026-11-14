from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import Role
from apps.core.tests.factories import (
    PASSWORD,
    at,
    completed_visit,
    make_company,
    make_contract,
    make_position,
    make_user,
    make_visit,
)


class ApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        self.client.get("/api/v1/auth/csrf/")
        return {"HTTP_X_CSRFTOKEN": self.client.cookies["csrftoken"].value}

    def login(self, email, password=PASSWORD, remember=True):
        return self.client.post("/api/v1/auth/login/", {"email": email, "password": password, "remember": remember},
                                format="json", **self.csrf())


class AuthTests(ApiTestCase):
    def test_errors_share_one_shape(self):
        response = self.client.get("/api/v1/auth/session/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "not_authenticated")
        self.assertNotIn("WWW-Authenticate", response)

    def test_login_returns_session_with_capabilities_and_menu(self):
        user = make_user(role=Role.ENGINEER, email="ing@ergopostura.test", first_name="Andrés")
        response = self.login("ING@ergopostura.test")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["user"]["id"], user.pk)
        self.assertIn("evaluation.manage", data["capabilities"])
        menu = {item["label"]: item for item in data["navigation"]}
        self.assertEqual(menu["Panel principal"]["to"], "/")
        self.assertEqual(menu["Empresas"]["to"], "/empresas")
        self.assertEqual(menu["Contratos"]["to"], "/contratos")
        self.assertEqual(menu["Visitas"]["href"], "/visitas/")
        self.assertNotIn("Usuarios", menu)
        self.assertEqual(self.client.get("/api/v1/auth/session/").status_code, 200)

    def test_wrong_password_is_a_generic_error(self):
        make_user(email="ing@ergopostura.test")
        response = self.login("ing@ergopostura.test", "otra")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_credentials")
        self.assertIn("no son correctos", response.json()["error"]["message"])

    def test_login_requires_csrf(self):
        make_user(email="ing@ergopostura.test")
        response = self.client.post("/api/v1/auth/login/", {"email": "ing@ergopostura.test", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_inactive_account_cannot_log_in(self):
        make_user(email="ing@ergopostura.test", is_active=False)
        self.assertEqual(self.login("ing@ergopostura.test").status_code, 400)

    @mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"login": "2/min"})
    def test_repeated_attempts_are_throttled(self):
        for _ in range(2):
            self.login("nadie@ergopostura.test", "x")
        response = self.login("nadie@ergopostura.test", "x")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "throttled")

    def test_logout_ends_the_session(self):
        make_user(email="ing@ergopostura.test")
        self.login("ing@ergopostura.test")
        self.client.post("/api/v1/auth/logout/", **self.csrf())
        self.assertEqual(self.client.get("/api/v1/auth/session/").status_code, 401)

    def test_writes_without_csrf_are_rejected_for_logged_in_users(self):
        make_user(email="ing@ergopostura.test")
        self.login("ing@ergopostura.test")
        response = self.client.post("/api/v1/auth/password/", {}, format="json")
        self.assertEqual(response.status_code, 403)


class TemporaryPasswordTests(ApiTestCase):
    def test_temporary_password_blocks_the_api_until_it_changes(self):
        make_user(email="nuevo@ergopostura.test", must_change_password=True)
        data = self.login("nuevo@ergopostura.test").json()
        self.assertTrue(data["user"]["must_change_password"])
        blocked = self.client.get("/api/v1/dashboard/")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["error"]["code"], "password_change_required")

        bad = self.client.post("/api/v1/auth/password/", {"old_password": PASSWORD, "new_password1": "123", "new_password2": "123"},
                               format="json", **self.csrf())
        self.assertEqual(bad.status_code, 400)
        self.assertIn("new_password2", bad.json()["error"]["fields"])

        ok = self.client.post("/api/v1/auth/password/", {"old_password": PASSWORD, "new_password1": "Mi-Clave-Nueva-77",
                                                         "new_password2": "Mi-Clave-Nueva-77"}, format="json", **self.csrf())
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(ok.json()["user"]["must_change_password"])
        self.assertEqual(self.client.get("/api/v1/dashboard/").status_code, 200)


class DashboardTests(ApiTestCase):
    def test_support_gets_accounts_and_no_business_data(self):
        make_user(role=Role.ADMIN, email="soporte@ergopostura.test")
        self.login("soporte@ergopostura.test")
        data = self.client.get("/api/v1/dashboard/").json()
        self.assertEqual(data["role"], "admin")
        self.assertFalse(data["has_engineer"])
        self.assertNotIn("recent_evaluations", data)

    def test_engineer_sees_what_needs_attention(self):
        position = make_position()
        today = timezone.localdate()
        make_contract(position.company, start=today - timedelta(days=340), end=today + timedelta(days=10))
        make_visit(position.area.site, at(today - timedelta(days=1)))
        completed_visit(position)
        make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.login("ing@ergopostura.test")
        data = self.client.get("/api/v1/dashboard/").json()
        self.assertEqual(data["to_close_count"], 1)
        self.assertEqual(data["to_close"][0]["level"]["key"], "por_cerrar")
        self.assertEqual(len(data["expiring_contracts"]), 1)
        self.assertEqual(data["expiring_contracts"][0]["status"], "por_vencer")
        self.assertEqual(len(data["without_evaluation"]), 1)

    def test_company_only_sees_its_own_data(self):
        own = make_company(name="Mi empresa")
        other = make_company(name="Ajena")
        make_contract(other)
        make_user(role=Role.COMPANY, company=own, email="empresa@ergopostura.test")
        self.login("empresa@ergopostura.test")
        data = self.client.get("/api/v1/dashboard/").json()
        self.assertEqual(data["company"]["name"], "Mi empresa")
        self.assertIsNone(data["contract"])
        self.assertNotIn("Ajena", str(data))


class SpaTests(TestCase):
    def test_every_client_route_gets_the_same_page(self):
        first = self.client.get("/app/")
        deep = self.client.get("/app/empresas/1/")
        # Sin compilar el cliente, explica cómo hacerlo en vez de fallar.
        self.assertEqual(first.status_code, deep.status_code)
        self.assertIn(first.status_code, (200, 503))
