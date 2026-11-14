import os
import re
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.companies.models import Company, Worker
from apps.contracts.models import Contract
from apps.core.demo import data as demo_data
from apps.core.templatetags.ui import _icons, icon
from apps.evaluations.models import Evaluation, Recommendation, RulaAssessment
from apps.evaluations.services import completion_problems
from apps.visits.models import Visit


class IconTests(SimpleTestCase):
    def test_renders_svg(self):
        self.assertIn("<svg", icon("check"))

    def test_every_icon_used_in_templates_exists(self):
        for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            for name in re.findall(r"{% icon '([\w-]+)' %}", path.read_text(encoding="utf-8")):
                self.assertIn(name, _icons(), f"{name} en {path}")



class SeedDemoTests(TestCase):
    @override_settings(DEBUG=True)
    def test_creates_one_user_per_role_and_can_run_twice(self):
        call_command("seed_demo", stdout=StringIO())
        totals = (Visit.objects.count(), Evaluation.objects.count(), Recommendation.objects.count())
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual((Visit.objects.count(), Evaluation.objects.count(), Recommendation.objects.count()), totals)
        self.assertEqual(User.objects.count(), len(demo_data.USERS))
        self.assertEqual(set(User.objects.values_list("role", flat=True)), set(Role.values))
        self.assertEqual(Company.objects.count(), len(demo_data.COMPANIES))

    @override_settings(DEBUG=True)
    def test_demo_data_follows_the_business_rules(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(set(RulaAssessment.objects.values_list("action_level", flat=True)), {1, 2, 3, 4})
        for evaluation in Evaluation.objects.filter(status=Evaluation.Status.COMPLETED):
            self.assertEqual(completion_problems(evaluation), [], evaluation)
        self.assertTrue(Evaluation.objects.filter(status=Evaluation.Status.DRAFT).exists())
        self.assertTrue(Recommendation.objects.filter(attended_at__isnull=False).exists())
        self.assertTrue(Recommendation.objects.filter(attended_at__isnull=True).exists())

        # Toda evaluacion sale de una visita realizada en la sede del puesto.
        for evaluation in Evaluation.objects.select_related("visit", "position__area"):
            self.assertEqual(evaluation.visit.status, Visit.Status.COMPLETED)
            self.assertEqual(evaluation.visit.site_id, evaluation.position.area.site_id)

        # Las visitas no se cruzan y caen dentro del contrato de su empresa.
        visits = list(Visit.objects.exclude(status=Visit.Status.CANCELLED).select_related("site__company"))
        for visit in visits:
            day = timezone.localdate(visit.scheduled_at)
            self.assertTrue(Contract.objects.filter(company=visit.company, start_date__lte=day, end_date__gte=day).exists(), visit)
            for other in visits:
                if other.pk != visit.pk:
                    self.assertFalse(visit.scheduled_at < other.ends_at and other.scheduled_at < visit.ends_at, (visit, other))

        now = timezone.now()
        statuses = set(Visit.objects.values_list("status", flat=True))
        self.assertEqual(statuses, set(Visit.Status.values))
        self.assertTrue(Visit.objects.filter(status=Visit.Status.SCHEDULED, scheduled_at__lt=now).exists())
        self.assertTrue(Visit.objects.filter(status=Visit.Status.SCHEDULED, scheduled_at__gt=now).exists())
        inactive = Company.objects.get(is_active=False)
        self.assertFalse(Visit.objects.filter(site__company=inactive, scheduled_at__gt=now).exists())
        self.assertEqual(Contract.objects.count(), len(demo_data.COMPANIES))
        self.assertTrue(Worker.objects.exists())
        documents = Contract.objects.values_list("file_data", flat=True)
        self.assertTrue(all(bytes(data).startswith(b"%PDF-") for data in documents))
        company_user = User.objects.get(email="empresa2@ergopostura.test")
        self.assertEqual(company_user.company.nit, "890900123")

    @override_settings(DEBUG=False)
    def test_refuses_to_run_outside_debug(self):
        # En produccion el sistema arranca vacio: ni con otra clave se cargan datos ficticios.
        for options in ({}, {"password": "Otra-clave-privada-2026"}):
            with self.assertRaises(CommandError):
                call_command("seed_demo", stdout=StringIO(), **options)
        self.assertFalse(User.objects.exists())


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
