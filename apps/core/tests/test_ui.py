import os
import re
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import CommandError, call_command
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import Role, User
from apps.companies.models import Company
from apps.core.templatetags.ui import _icons, icon
from apps.core.views import full_reload_url


class FullReloadUrlTests(SimpleTestCase):
    def test_moves_the_fragment_so_the_browser_reloads(self):
        self.assertEqual(full_reload_url("/evaluaciones/1/#postura-2"), "/evaluaciones/1/?foco=postura-2")

    def test_keeps_the_existing_query(self):
        self.assertEqual(full_reload_url("/a/?x=1#b"), "/a/?x=1&foco=b")

    def test_leaves_other_urls_alone(self):
        self.assertEqual(full_reload_url("/a/?x=1"), "/a/?x=1")


class IconTests(SimpleTestCase):
    def test_renders_svg(self):
        self.assertIn("<svg", icon("check"))

    def test_every_icon_used_in_templates_exists(self):
        for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            for name in re.findall(r"{% icon '([\w-]+)' %}", path.read_text(encoding="utf-8")):
                self.assertIn(name, _icons(), f"{name} en {path}")

    def test_every_template_compiles(self):
        root = Path(settings.BASE_DIR, "templates")
        for path in root.rglob("*.html"):
            get_template(path.relative_to(root).as_posix())


class SeedDemoTests(TestCase):
    @override_settings(DEBUG=True)
    def test_creates_one_user_per_role_and_can_run_twice(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(User.objects.count(), len(Role))
        self.assertEqual(set(User.objects.values_list("role", flat=True)), set(Role.values))
        self.assertEqual(Company.objects.count(), 2)

    @override_settings(DEBUG=False)
    def test_refuses_to_run_outside_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_production_never_accepts_the_published_password(self):
        with self.assertRaisesMessage(CommandError, "clave de demostración"):
            call_command("seed_demo", allow_production=True, stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_production_seed_uses_the_given_password(self):
        call_command("seed_demo", allow_production=True, password="Otra-clave-privada-2026", stdout=StringIO())
        user = User.objects.get(email="admin@ergopostura.test")
        self.assertTrue(user.check_password("Otra-clave-privada-2026"))


class EnsureAdminTests(TestCase):
    ENV = {"DJANGO_ADMIN_EMAIL": "Jefe@Empresa.com", "DJANGO_ADMIN_PASSWORD": "Una-clave-larga-2026"}

    def test_creates_admin_once_and_does_not_reset_it(self):
        with mock.patch.dict(os.environ, self.ENV):
            call_command("ensure_admin", stdout=StringIO())
        user = User.objects.get(email="jefe@empresa.com")
        self.assertEqual(user.role, Role.ADMIN)

        with mock.patch.dict(os.environ, {**self.ENV, "DJANGO_ADMIN_PASSWORD": "Otra-clave-larga-2026"}):
            call_command("ensure_admin", stdout=StringIO())
        user.refresh_from_db()
        self.assertTrue(user.check_password("Una-clave-larga-2026"))

    def test_does_nothing_without_variables(self):
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("DJANGO_ADMIN_EMAIL", None)
            os.environ.pop("DJANGO_ADMIN_PASSWORD", None)
            call_command("ensure_admin", stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_rejects_a_weak_password(self):
        with mock.patch.dict(os.environ, {**self.ENV, "DJANGO_ADMIN_PASSWORD": "123"}):
            with self.assertRaises(CommandError):
                call_command("ensure_admin", stdout=StringIO())
        self.assertFalse(User.objects.exists())
