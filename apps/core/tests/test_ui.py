import re
from pathlib import Path
from io import StringIO

from django.conf import settings
from django.core.management import CommandError, call_command
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import Role, User
from apps.companies.models import Company
from apps.core.templatetags.ui import _icons, icon


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
