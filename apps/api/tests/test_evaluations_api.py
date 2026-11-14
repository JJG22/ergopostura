from apps.accounts.models import Role
from apps.core.tests.factories import (
    completed_visit,
    make_position,
    make_user,
    make_visit,
    make_worker,
)
from apps.evaluations import services
from apps.evaluations.models import Evaluation, Recommendation
from apps.evaluations.tests.test_evaluations import (
    make_assessment,
    make_evaluation,
    make_posture,
    upload,
)

from .test_api import ApiTestCase

# El mismo caso calculado a mano de apps/evaluations: resultado 6, nivel de acción 3.
ASSESSMENT = {
    "upper_arm_angle": 30, "shoulder_raised": True, "upper_arm_abducted": False, "arm_supported": False,
    "lower_arm_angle": 110, "lower_arm_across_midline_or_out": False, "wrist_angle": 10,
    "wrist_bent_from_midline": True, "wrist_twist_near_end": False, "arm_static_or_repeated": True,
    "arm_load": "MEDIUM_INTERMITTENT", "neck_angle": 15, "neck_twisted": True, "neck_side_bent": False,
    "trunk_angle": 30, "trunk_supported_seated": False, "trunk_twisted": False, "trunk_side_bent": False,
    "legs_supported_and_balanced": True, "body_static_or_repeated": False, "body_load": "NONE_OR_LIGHT_INTERMITTENT",
}


class EvaluationsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.position = make_position()
        self.visit = completed_visit(self.position)
        self.company = self.position.area.site.company

    def as_engineer(self):
        self.login(self.engineer.email)
        return self.csrf()

    def test_options_cascade_from_the_completed_visit(self):
        make_visit(site=self.position.area.site)  # programada: no aparece
        worker = make_worker(self.position)
        self.as_engineer()
        data = self.client.get("/api/v1/evaluations/options/").json()
        self.assertEqual([v["value"] for v in data["visits"]], [str(self.visit.pk)])
        self.assertEqual(data["areas"], [])
        data = self.client.get(f"/api/v1/evaluations/options/?visit={self.visit.pk}&area={self.position.area_id}&position={self.position.pk}").json()
        self.assertEqual([a["value"] for a in data["areas"]], [str(self.position.area_id)])
        self.assertEqual([w["value"] for w in data["workers"]], [str(worker.pk)])

    def test_full_cycle_create_posture_photo_assessment_recommendation_complete(self):
        headers = self.as_engineer()
        payload = {"visit": self.visit.pk, "area": self.position.area_id, "position": self.position.pk,
                   "evaluated_on": self.visit.scheduled_at.date().isoformat(), "activity_description": "Empaca cajas",
                   "carries_load": False, "repetitive_movements": False}
        response = self.client.post("/api/v1/evaluations/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 201, response.content)
        pk = response.json()["id"]

        response = self.client.post(f"/api/v1/evaluations/{pk}/complete/", **headers)
        self.assertEqual(response.status_code, 409)
        self.assertIn("Agrega al menos una postura.", response.json()["error"]["fields"]["__all__"])

        posture = self.client.post(f"/api/v1/evaluations/{pk}/postures/",
                                   {"name": "Empaque", "side": "derecho", "duration_value": 5, "duration_unit": "minutos"},
                                   format="json", **headers).json()["id"]
        self.assertEqual(self.client.get(f"/api/v1/evaluations/postures/{posture}/assessment/").status_code, 409)
        photo = self.client.post(f"/api/v1/evaluations/postures/{posture}/photos/", {"photo": upload()}, format="multipart", **headers)
        self.assertEqual(photo.status_code, 201, photo.content)
        photo_id = photo.json()["id"]

        form = self.client.get(f"/api/v1/evaluations/postures/{posture}/assessment/").json()
        self.assertEqual(form["photo"], photo_id)
        self.assertEqual(len(form["groups"]), 5)
        result = self.client.put(f"/api/v1/evaluations/postures/{posture}/assessment/", {**ASSESSMENT, "photo": photo_id,
                                 "ai_suggestion": {"angles": {"upper_arm_angle": 28}, "photo": photo_id, "model": "mediapipe"}},
                                 format="json", **headers)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(result.json()["result"]["grand_score"], 6)
        self.assertEqual(result.json()["result"]["ai_trace"]["rows"][0]["suggested"], 28.0)

        self.assertEqual(self.client.delete(f"/api/v1/evaluations/photos/{photo_id}/", **headers).status_code, 409)
        self.assertEqual(self.client.post(f"/api/v1/evaluations/{pk}/complete/", **headers).status_code, 409)
        self.client.post(f"/api/v1/evaluations/postures/{posture}/recommendations/", {"text": "Elevar la banda"}, format="json", **headers)
        response = self.client.post(f"/api/v1/evaluations/{pk}/complete/", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "terminada")
        self.assertFalse(response.json()["can_edit"])
        self.assertEqual(response.json()["risk"]["level"], 3)

    def test_company_only_sees_completed_and_photos_are_private(self):
        draft = make_evaluation(self.engineer, self.position, visit=self.visit)
        done = make_evaluation(self.engineer, self.position, visit=self.visit)
        posture = make_posture(done)
        make_assessment(posture)
        Recommendation.objects.create(posture=posture, text="Elevar la banda", author=self.engineer)
        services.complete_evaluation(done)
        photo = posture.photos.first()

        member = make_user(role=Role.COMPANY, company=self.company)
        self.login(member.email)
        ids = [e["id"] for e in self.client.get("/api/v1/evaluations/").json()["results"]]
        self.assertEqual(ids, [done.pk])
        self.assertEqual(self.client.get(f"/api/v1/evaluations/{draft.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/evaluations/photos/{photo.pk}/")["Content-Type"], "image/jpeg")
        self.assertFalse(self.client.get(f"/api/v1/evaluations/{done.pk}/").json()["can_reopen"])

        outsider = make_user(role=Role.COMPANY)
        self.client.post("/api/v1/auth/logout/", **self.csrf())
        self.login(outsider.email)
        self.assertEqual(self.client.get(f"/api/v1/evaluations/photos/{photo.pk}/").status_code, 404)

    def test_other_engineer_cannot_edit_and_reopen_returns_to_draft(self):
        evaluation = make_evaluation(self.engineer, self.position, visit=self.visit)
        other = make_user(role=Role.ENGINEER)
        self.login(other.email)
        headers = self.csrf()
        self.assertFalse(self.client.get(f"/api/v1/evaluations/{evaluation.pk}/").json()["can_edit"])
        response = self.client.post(f"/api/v1/evaluations/{evaluation.pk}/postures/", {"name": "X", "side": "derecho",
                                    "duration_value": 1, "duration_unit": "minutos"}, format="json", **headers)
        self.assertEqual(response.status_code, 404)
        Evaluation.objects.filter(pk=evaluation.pk).update(status="terminada", completed_at=self.visit.scheduled_at)
        response = self.client.post(f"/api/v1/evaluations/{evaluation.pk}/reopen/", **headers)
        self.assertEqual(response.json()["status"], "borrador")

    def test_duplicate_posture_and_recommendation_needs_result(self):
        evaluation = make_evaluation(self.engineer, self.position, visit=self.visit)
        posture = make_posture(evaluation, name="Empaque")
        headers = self.as_engineer()
        response = self.client.post(f"/api/v1/evaluations/{evaluation.pk}/postures/", {"name": "empaque", "side": "derecho",
                                    "duration_value": 1, "duration_unit": "minutos"}, format="json", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["error"]["fields"])
        response = self.client.post(f"/api/v1/evaluations/postures/{posture.pk}/recommendations/", {"text": "x"}, format="json", **headers)
        self.assertEqual(response.status_code, 409)

