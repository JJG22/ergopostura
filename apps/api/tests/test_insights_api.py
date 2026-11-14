from apps.accounts.models import Role
from apps.core.tests.factories import completed_visit, make_position, make_user
from apps.evaluations import services
from apps.evaluations.models import Recommendation
from apps.evaluations.tests.test_evaluations import make_assessment, make_evaluation, make_posture

from .test_api import ApiTestCase


class InsightsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.position = make_position()
        self.company = self.position.area.site.company
        evaluation = make_evaluation(self.engineer, self.position, visit=completed_visit(self.position))
        posture = make_posture(evaluation)
        make_assessment(posture)  # resultado 6: amarillo
        self.recommendation = Recommendation.objects.create(posture=posture, text="Elevar la banda", author=self.engineer)
        services.complete_evaluation(evaluation)
        self.draft = make_evaluation(self.engineer, self.position, visit=evaluation.visit)

    def test_indicators_count_each_position_once_and_compare_areas(self):
        self.login(self.engineer.email)
        data = self.client.get("/api/v1/indicators/").json()
        self.assertEqual(data["totals"]["yellow"], 1)
        self.assertEqual(data["totals"]["follow_up_percent"], 100)
        self.assertIsNone(data["areas"])
        data = self.client.get(f"/api/v1/indicators/?company={self.company.pk}").json()
        self.assertEqual(data["selected_company"]["name"], self.company.name)
        self.assertEqual(data["areas"][0]["risk"]["total"], 1)
        self.assertIsNone(self.client.get("/api/v1/indicators/?company=999").json()["selected_company"])

    def test_company_sees_only_its_areas(self):
        member = make_user(role=Role.COMPANY, company=self.company)
        self.login(member.email)
        data = self.client.get("/api/v1/indicators/?company=1234").json()
        self.assertFalse(data["shows_all_companies"])
        self.assertEqual(data["companies"], [])
        self.assertEqual(data["selected_company"]["id"], self.company.pk)

    def test_engineer_tasks_show_drafts_and_company_attends_recommendations(self):
        self.login(self.engineer.email)
        data = self.client.get("/api/v1/tasks/").json()
        self.assertEqual([e["id"] for e in data["in_progress"]], [self.draft.pk])
        self.assertIn("Agrega al menos una postura.", data["in_progress"][0]["problems"])
        self.assertFalse(data["can_attend"])

        member = make_user(role=Role.COMPANY, company=self.company)
        self.client.post("/api/v1/auth/logout/", **self.csrf())
        self.login(member.email)
        headers = self.csrf()
        data = self.client.get("/api/v1/tasks/").json()
        self.assertEqual([r["id"] for r in data["results"]], [self.recommendation.pk])
        self.assertTrue(data["can_attend"])
        response = self.client.post(f"/api/v1/tasks/{self.recommendation.pk}/attend/", {"attended": True}, format="json", **headers)
        self.assertIsNotNone(response.json()["attended_at"])
        self.assertEqual(self.client.get("/api/v1/tasks/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/tasks/?view=atendidas").json()["count"], 1)
        self.client.post(f"/api/v1/tasks/{self.recommendation.pk}/attend/", {"attended": False}, format="json", **headers)
        self.assertEqual(self.client.get("/api/v1/tasks/").json()["count"], 1)

    def test_engineer_cannot_attend_and_other_company_cannot_see(self):
        self.login(self.engineer.email)
        response = self.client.post(f"/api/v1/tasks/{self.recommendation.pk}/attend/", {"attended": True}, format="json", **self.csrf())
        self.assertEqual(response.status_code, 403)
        outsider = make_user(role=Role.COMPANY)
        self.client.post("/api/v1/auth/logout/", **self.csrf())
        self.login(outsider.email)
        self.assertEqual(self.client.get("/api/v1/tasks/").json()["count"], 0)
        response = self.client.post(f"/api/v1/tasks/{self.recommendation.pk}/attend/", {"attended": True}, format="json", **self.csrf())
        self.assertEqual(response.status_code, 404)
