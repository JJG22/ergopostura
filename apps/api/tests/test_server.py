from django.test import TestCase

from apps.accounts.models import Role
from apps.core.legacy import target_for
from apps.core.tests.factories import PASSWORD, make_user


class LegacyAddressTests(TestCase):
    """El servidor ya no genera pantallas: las direcciones viejas llevan a su pantalla en React."""

    def test_old_addresses_point_to_the_same_screen(self):
        cases = {
            "": "/app/",
            "ingresar/": "/app/ingresar",
            "empresas/": "/app/empresas",
            "empresas/7/": "/app/empresas/7",
            "empresas/7/editar/": "/app/empresas/7",
            "contratos/nuevo/": "/app/contratos/nuevo",
            "contratos/3/editar/": "/app/contratos/3/editar",
            "visitas/agenda/": "/app/visitas/agenda",
            "visitas/12/": "/app/visitas/12",
            "evaluaciones/5/informe/": "/app/evaluaciones/5/informe",
            "evaluaciones/posturas/9/analisis/": "/app/evaluaciones/posturas/9/analisis",
            "usuarios/nuevo/": "/app/usuarios?crear=1",
            "tareas/": "/app/tareas",
        }
        for path, target in cases.items():
            with self.subTest(path=path):
                self.assertEqual(target_for(path, {}), target)

    def test_filters_are_kept_and_unknown_parameters_dropped(self):
        response = self.client.get("/visitas/agenda/?ver=por_cerrar&x=1")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/app/visitas/agenda?ver=por_cerrar")
        self.assertEqual(self.client.get("/indicadores").status_code, 302)

    def test_unknown_addresses_answer_json_not_html(self):
        response = self.client.get("/no-existe/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["error"]["code"], "not_found")
        self.assertEqual(self.client.get("/api/v1/no-existe/").status_code, 404)


class AdminPanelTests(TestCase):
    def test_admin_login_uses_the_application_login(self):
        response = self.client.get("/admin/login/?next=/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/app/ingresar?next=/admin/")
        # El panel envía a su propio login, que a su vez lleva al de la aplicación.
        self.assertTrue(self.client.get("/admin/")["Location"].startswith("/admin/login/"))

    def test_support_with_temporary_password_changes_it_first(self):
        user = make_user(role=Role.ADMIN, must_change_password=True)
        self.client.login(username=user.email, password=PASSWORD)
        response = self.client.get("/admin/")
        self.assertEqual(response["Location"], "/app/cambiar-contrasena")
        self.assertEqual(self.client.get("/api/v1/auth/session/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/dashboard/").json()["error"]["code"], "password_change_required")

    def test_support_opens_the_admin_panel(self):
        user = make_user(role=Role.ADMIN)
        self.client.login(username=user.email, password=PASSWORD)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/app/")
