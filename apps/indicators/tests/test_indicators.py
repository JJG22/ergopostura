from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.core.tests.factories import make_area, make_company, make_position, make_site, make_user
from apps.evaluations import services
from apps.evaluations.models import Recommendation
from apps.evaluations.tests.test_evaluations import make_assessment, make_evaluation, make_posture
from apps.indicators.metrics import EvaluationRow, distribution, latest_per_position
from apps.rula.scoring import Load

LOW = dict(
    upper_arm_angle="0", shoulder_raised="", lower_arm_angle="80", wrist_angle="0",
    wrist_bent_from_midline="", arm_static_or_repeated="",
    arm_load=Load.NONE_OR_LIGHT_INTERMITTENT.name, neck_angle="0", neck_twisted="", trunk_angle="0",
)
# Puntaje 6: amarillo. Es el caso calculado a mano en las pruebas de RULA.
MEDIUM = {}
HIGH = dict(
    upper_arm_angle="120", lower_arm_angle="10", wrist_angle="40", arm_load=Load.SHOCK_OR_RAPID_FORCE.name,
    neck_angle="-10", trunk_angle="80", body_load=Load.HEAVY_STATIC_OR_REPEATED.name,
)


def row(position, score, area=1, company=1):
    return EvaluationRow(position, area, company, "Empresa", score)


def finished(user, position, level, days_ago=0):
    evaluation = make_evaluation(
        user, position, evaluated_on=timezone.localdate() - timedelta(days=days_ago)
    )
    posture = make_posture(evaluation)
    make_assessment(posture, **level)
    Recommendation.objects.create(posture=posture, text="Ajustar", author=user)
    services.complete_evaluation(evaluation)
    return evaluation


class MetricsTests(SimpleTestCase):
    def test_counts_by_traffic_light(self):
        risk = distribution([row(1, 1), row(2, 2), row(3, 3), row(4, 6), row(5, 7)])
        self.assertEqual((risk.green, risk.yellow, risk.red), (2, 2, 1))
        self.assertEqual(risk.total, 5)
        self.assertEqual(risk.follow_up, 3)
        self.assertEqual(risk.follow_up_percent, 60)

    def test_empty_does_not_divide_by_zero(self):
        self.assertEqual(distribution([]).follow_up_percent, 0)

    def test_only_the_latest_evaluation_of_a_position_counts(self):
        rows = [row(1, 2), row(1, 7), row(2, 7)]
        self.assertEqual(latest_per_position(rows), [row(1, 2), row(2, 7)])


class IndicatorViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = make_user(role=Role.ENGINEER)
        cls.company = make_company(name="Mi empresa")
        cls.site = make_site(cls.company)
        cls.area_a = make_area(cls.site, name="Empaque")
        cls.area_b = make_area(cls.site, name="Bodega")
        cls.empty_area = make_area(cls.site, name="Sin datos")
        cls.foreign = make_company(name="Ajena")
        foreign_position = make_position(make_area(make_site(cls.foreign), name="Ajena"))

        cls.position_a = make_position(cls.area_a, name="Uno")
        finished(cls.author, cls.position_a, HIGH, days_ago=10)
        finished(cls.author, cls.position_a, LOW, days_ago=1)  # La mas reciente manda.
        finished(cls.author, make_position(cls.area_a, name="Dos"), MEDIUM)
        finished(cls.author, make_position(cls.area_b, name="Tres"), HIGH)
        finished(cls.author, foreign_position, HIGH)
        # En curso: no debe contar.
        draft = make_evaluation(cls.author, make_position(cls.area_b, name="Cuatro"))
        make_assessment(make_posture(draft), **HIGH)

    url = "/indicadores/"

    def login(self, role, **fields):
        self.client.force_login(make_user(role=role, **fields))

    def test_roles_with_access(self):
        self.login(Role.ENGINEER)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.login(Role.COMPANY, company=self.company)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_support_has_no_access(self):
        self.login(Role.ADMIN)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertIn("/ingresar/", self.client.get(self.url)["Location"])

    def test_engineer_can_compare_companies(self):
        self.login(Role.ENGINEER)
        self.assertTrue(self.client.get(self.url).context["shows_all_companies"])

    def test_totals_count_each_position_once_and_skip_drafts(self):
        self.login(Role.ENGINEER)
        context = self.client.get(self.url).context
        totals = context["totals"]
        # Uno (verde por su evaluacion reciente), Dos (amarillo), Tres y Ajena (rojo).
        self.assertEqual((totals.green, totals.yellow, totals.red), (1, 1, 2))
        self.assertEqual(context["company_count"], 2)
        self.assertEqual(context["area_count"], 3)

    def test_area_comparison_uses_the_same_definition_and_shows_empty_areas(self):
        self.login(Role.ENGINEER)
        response = self.client.get(self.url, {"empresa": self.company.pk})
        rows = {item["label"]: item["risk"] for item in response.context["area_rows"]}
        self.assertEqual(rows[f"{self.site.name} · Empaque"].green, 1)
        self.assertEqual(rows[f"{self.site.name} · Empaque"].yellow, 1)
        self.assertEqual(rows[f"{self.site.name} · Bodega"].red, 1)
        self.assertEqual(rows[f"{self.site.name} · Sin datos"].total, 0)
        self.assertContains(response, "Sin evaluaciones")

    def test_company_user_only_sees_its_own_data_even_forcing_the_parameter(self):
        self.login(Role.COMPANY, company=self.company)
        response = self.client.get(self.url, {"empresa": self.foreign.pk})
        self.assertEqual(response.context["company_count"], 1)
        self.assertEqual(response.context["selected_company_id"], self.company.pk)
        self.assertNotContains(response, "Ajena")
        self.assertFalse(response.context["shows_all_companies"])

    def test_company_user_without_evaluations_sees_empty_state(self):
        company = make_company(name="Nueva")
        make_area(make_site(company))
        self.login(Role.COMPANY, company=company)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"].total, 0)

    def test_unknown_company_parameter_is_ignored(self):
        self.login(Role.ENGINEER)
        for value in ("999999", "abc", "'; DROP"):
            response = self.client.get(self.url, {"empresa": value})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context["selected_company_id"])

    def test_definition_is_visible(self):
        self.login(Role.ENGINEER)
        self.assertContains(self.client.get(self.url), "más reciente de cada puesto")

    def test_reverse_url(self):
        self.assertEqual(reverse("indicators:home"), self.url)
