from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import Role
from apps.core.tests.factories import make_area, make_company, make_position, make_site, make_user
from apps.evaluations import services
from apps.evaluations.models import Recommendation
from apps.evaluations.tests.test_evaluations import make_assessment, make_evaluation, make_posture

URL = "/tareas/"


class TaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = make_user(role=Role.ENGINEER)
        cls.company = make_company(name="Mi empresa")
        position = make_position(make_area(make_site(cls.company)), name="Puesto propio")
        foreign_position = make_position(make_area(make_site(make_company(name="Ajena")), name="Ajena"), name="Puesto ajeno")

        cls.evaluation = make_evaluation(cls.author, position)
        posture = make_posture(cls.evaluation)
        make_assessment(posture)
        cls.recommendation = Recommendation.objects.create(posture=posture, text="Bajar la banda", author=cls.author)
        services.complete_evaluation(cls.evaluation)

        foreign = make_evaluation(cls.author, foreign_position)
        foreign_posture = make_posture(foreign)
        make_assessment(foreign_posture)
        cls.foreign_recommendation = Recommendation.objects.create(
            posture=foreign_posture, text="Cambiar la silla", author=cls.author
        )
        services.complete_evaluation(foreign)

        cls.draft = make_evaluation(cls.author, position)
        draft_posture = make_posture(cls.draft, "Sin analizar")
        cls.draft_recommendation = Recommendation.objects.create(
            posture=draft_posture, text="Borrador oculto", author=cls.author
        )

    def login(self, role, **fields):
        user = make_user(role=role, **fields)
        self.client.force_login(user)
        return user

    def attend_url(self, recommendation):
        return reverse("tasks:attend", args=[recommendation.pk])

    def company_member(self):
        return self.login(Role.COMPANY, company=self.company)

    def test_access(self):
        self.assertIn("/ingresar/", self.client.get(URL)["Location"])
        self.login(Role.ADMIN)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.login(Role.ENGINEER)
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.company_member()
        self.assertEqual(self.client.get(URL).status_code, 200)

    def test_engineer_follows_all_completed_recommendations_but_not_drafts(self):
        self.login(Role.ENGINEER)
        response = self.client.get(URL)
        self.assertEqual(
            set(response.context["recommendations"]), {self.recommendation, self.foreign_recommendation}
        )
        self.assertNotContains(response, "Borrador oculto")

    def test_company_sees_and_attends_only_its_own(self):
        user = self.login(Role.COMPANY, company=self.company)
        self.assertEqual(list(self.client.get(URL).context["recommendations"]), [self.recommendation])
        self.assertEqual(self.client.post(self.attend_url(self.foreign_recommendation)).status_code, 404)
        self.client.post(self.attend_url(self.recommendation))
        self.recommendation.refresh_from_db()
        self.assertEqual(self.recommendation.attended_by, user)
        self.assertIsNotNone(self.recommendation.attended_at)

    def test_engineer_sees_own_drafts_with_what_is_missing(self):
        self.client.force_login(self.author)
        response = self.client.get(URL)
        items = response.context["in_progress"]
        self.assertEqual([item["evaluation"] for item in items], [self.draft])
        self.assertIn("Sin analizar", items[0]["problems"][0])
        self.assertTrue(response.context["shows_recommendations"])

    def test_another_engineer_does_not_see_those_drafts(self):
        self.login(Role.ENGINEER)
        self.assertEqual(self.client.get(URL).context["in_progress"], [])

    def test_only_the_company_attends(self):
        for role in (Role.ENGINEER, Role.ADMIN):
            self.login(role)
            self.assertEqual(self.client.post(self.attend_url(self.recommendation)).status_code, 403, role)
        self.recommendation.refresh_from_db()
        self.assertIsNone(self.recommendation.attended_at)

    def test_attend_requires_post(self):
        self.company_member()
        self.assertEqual(self.client.get(self.attend_url(self.recommendation)).status_code, 405)

    def test_draft_recommendation_cannot_be_attended(self):
        self.company_member()
        self.assertEqual(self.client.post(self.attend_url(self.draft_recommendation)).status_code, 404)

    def test_attend_moves_to_the_other_tab_and_can_be_undone(self):
        self.company_member()
        self.client.post(self.attend_url(self.recommendation))
        self.assertNotIn(self.recommendation, self.client.get(URL).context["recommendations"])
        self.assertIn(self.recommendation, self.client.get(URL, {"ver": "atendidas"}).context["recommendations"])

        self.client.post(reverse("tasks:reopen", args=[self.recommendation.pk]))
        self.recommendation.refresh_from_db()
        self.assertIsNone(self.recommendation.attended_at)
        self.assertIsNone(self.recommendation.attended_by)

    def test_attending_does_not_change_the_result(self):
        result = self.recommendation.posture.assessment
        before = (result.grand_score, result.partial_scores)
        self.company_member()
        self.client.post(self.attend_url(self.recommendation))
        result.refresh_from_db()
        self.assertEqual((result.grand_score, result.partial_scores), before)

    def test_company_can_open_the_evaluation_behind_each_task(self):
        self.company_member()
        response = self.client.get(URL)
        self.assertContains(response, reverse("evaluations:detail", args=[self.evaluation.pk]))

    def test_search(self):
        self.login(Role.ENGINEER)
        for query, expected in (("banda", self.recommendation), ("Puesto ajeno", self.foreign_recommendation)):
            self.assertEqual(list(self.client.get(URL, {"q": query}).context["recommendations"]), [expected])

    def test_query_count_does_not_grow(self):
        self.login(Role.ENGINEER)
        with CaptureQueriesContext(connection) as before:
            self.client.get(URL)
        posture = self.recommendation.posture
        for index in range(5):
            Recommendation.objects.create(posture=posture, text=f"Extra {index}", author=self.author)
        with self.assertNumQueries(len(before)):
            self.client.get(URL)


class ReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = make_user(role=Role.ENGINEER)
        cls.company = make_company(name="Mi empresa", nit="900123456")
        position = make_position(make_area(make_site(cls.company)))
        cls.evaluation = make_evaluation(cls.author, position)
        cls.posture = make_posture(cls.evaluation)
        cls.result = make_assessment(cls.posture)
        Recommendation.objects.create(posture=cls.posture, text="Bajar la banda", author=cls.author)
        services.complete_evaluation(cls.evaluation)

        cls.draft = make_evaluation(cls.author, position)
        foreign_position = make_position(make_area(make_site(make_company(name="Ajena")), name="Ajena"))
        cls.foreign = make_evaluation(cls.author, foreign_position)
        posture = make_posture(cls.foreign)
        make_assessment(posture)
        Recommendation.objects.create(posture=posture, text="Otra", author=cls.author)
        services.complete_evaluation(cls.foreign)

    def report(self, evaluation):
        return reverse("evaluations:report", args=[evaluation.pk])

    def test_contains_results_evidence_and_recommendations(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        response = self.client.get(self.report(self.evaluation))
        self.assertContains(response, "900.123.456-8")
        self.assertContains(response, "Requiere revisión · Nivel 3")
        self.assertContains(response, "Bajar la banda")
        self.assertContains(response, reverse("evaluations:photo", args=[self.result.photo_id]))
        self.assertContains(response, "McAtamney")

    def test_draft_has_no_report(self):
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(self.report(self.draft)).status_code, 404)

    def test_follows_the_scope_of_the_evaluation(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        self.assertEqual(self.client.get(self.report(self.evaluation)).status_code, 200)
        self.assertEqual(self.client.get(self.report(self.foreign)).status_code, 404)

    def test_requires_access(self):
        self.assertIn("/ingresar/", self.client.get(self.report(self.evaluation))["Location"])
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertEqual(self.client.get(self.report(self.evaluation)).status_code, 403)

    def test_detail_links_to_the_report_only_when_completed(self):
        self.client.force_login(self.author)
        detail = reverse("evaluations:detail", args=[self.evaluation.pk])
        self.assertContains(self.client.get(detail), self.report(self.evaluation))
        draft = reverse("evaluations:detail", args=[self.draft.pk])
        self.assertNotContains(self.client.get(draft), "Ver informe")
