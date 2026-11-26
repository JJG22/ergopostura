import json
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase, override_settings

from apps.accounts.models import Role
from apps.core.tests.factories import (
    completed_visit,
    make_position,
    make_user,
    make_visit,
    make_worker,
)
from apps.evaluations import advisor, services
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



def advice_json(**changes):
    data = {
        "observations": "La mesa queda baja y obliga a flexionar el tronco y el cuello.",
        "recommendations": [
            {"text": "Rotar la tarea cada dos horas.", "focus": "general", "kind": "administrativa", "priority": "media"},
            {"text": "Subir la superficie de trabajo hasta la altura de los codos.", "focus": "tronco",
             "kind": "ingenieria", "priority": "alta"},
        ],
        "caution": None,
    }
    data.update(changes)
    return json.dumps(data)


def fake_advisor(text=None, stop_reason="end_turn", error=None):
    response = SimpleNamespace(stop_reason=stop_reason, model="claude-opus-5-5",
                               content=[SimpleNamespace(type="text", text=text if text is not None else advice_json())])
    create = mock.Mock(return_value=response, side_effect=error)
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    return mock.patch.object(advisor.anthropic, "Anthropic", return_value=client), create


@override_settings(ANTHROPIC_API_KEY="clave-de-prueba")
class AiAdviceApiTests(ApiTestCase):
    """Recomendaciones de la IA: una segunda opinión que el ingeniero decide si usa."""

    def setUp(self):
        super().setUp()
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.evaluation = make_evaluation(self.engineer)
        self.posture = make_posture(self.evaluation)
        self.assessment = make_assessment(self.posture)
        self.url = f"/api/v1/evaluations/postures/{self.posture.pk}/ai-recommendations/"

    def as_engineer(self):
        self.login(self.engineer.email)
        return self.csrf()

    def test_sends_the_photo_and_the_result_and_keeps_the_advice(self):
        headers = self.as_engineer()
        patcher, create = fake_advisor()
        with patcher:
            response = self.client.post(self.url, format="json", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        content = create.call_args.kwargs["messages"][0]["content"]
        self.assertEqual((content[0]["type"], content[0]["source"]["media_type"]), ("image", "image/jpeg"))
        self.assertIn("Puntaje final RULA: 6 de 7", content[1]["text"])
        advice = response.json()["result"]["ai_advice"]
        # Ordenadas por prioridad, con etiquetas en español.
        self.assertEqual([item["priority"] for item in advice["items"]], ["alta", "media"])
        self.assertEqual(advice["items"][0]["kind_label"], "Cambio en el puesto")
        self.assertFalse(advice["stale"])
        # No crea recomendaciones: el ingeniero decide cuáles usa.
        self.assertFalse(Recommendation.objects.exists())
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.ai_recommendations["grand_score"], 6)

    def test_advice_is_marked_stale_when_the_analysis_changes(self):
        headers = self.as_engineer()
        patcher, _ = fake_advisor()
        with patcher:
            self.client.post(self.url, format="json", **headers)
        response = self.client.put(f"/api/v1/evaluations/postures/{self.posture.pk}/assessment/",
                                   {**ASSESSMENT, "photo": self.assessment.photo_id, "trunk_angle": 70, "neck_angle": 30,
                                    "arm_load": "HEAVY_STATIC_OR_REPEATED", "body_load": "HEAVY_STATIC_OR_REPEATED"}, format="json", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["result"]["grand_score"], 7)
        self.assertTrue(response.json()["result"]["ai_advice"]["stale"])

    def test_a_recommendation_taken_from_the_ai_is_marked(self):
        headers = self.as_engineer()
        response = self.client.post(f"/api/v1/evaluations/postures/{self.posture.pk}/recommendations/",
                                    {"text": "Subir la superficie de trabajo.", "from_ai": True}, format="json", **headers)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Recommendation.objects.get().from_ai)
        detail = self.client.get(f"/api/v1/evaluations/{self.evaluation.pk}/").json()
        self.assertTrue(detail["postures"][0]["recommendations"][0]["from_ai"])

    def test_without_ai_the_catalog_answers_and_says_why(self):
        headers = self.as_engineer()
        patcher, _ = fake_advisor(stop_reason="refusal")
        with patcher:
            response = self.client.post(self.url, format="json", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        advice = response.json()["result"]["ai_advice"]
        self.assertEqual(advice["source"], "catalogo")
        self.assertIn("no pudo procesar", advice["notice"])
        self.assertTrue(advice["items"])
        with override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY=""):
            advice = self.client.post(self.url, format="json", **headers).json()["result"]["ai_advice"]
        self.assertEqual((advice["source"], advice["model"]), ("catalogo", advisor.CATALOG_MODEL))

    def test_only_the_author_can_ask(self):
        other = make_user(role=Role.ENGINEER, email="otro@ergopostura.test")
        self.login(other.email)
        self.assertEqual(self.client.post(self.url, format="json", **self.csrf()).status_code, 404)


def fake_gemini(text=None, status="completed", error=None):
    interaction = SimpleNamespace(status=status, output_text=text if text is not None else advice_json())
    create = mock.Mock(return_value=interaction, side_effect=error)
    client = SimpleNamespace(interactions=SimpleNamespace(create=create))
    return mock.patch("google.genai.Client", return_value=client), create


@override_settings(GEMINI_API_KEY="clave-gemini", ANTHROPIC_API_KEY="", GEMINI_MODEL="gemini-4-hydrogen")
class GeminiAdviceTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.posture = make_posture(make_evaluation(self.engineer))
        self.assessment = make_assessment(self.posture)
        self.url = f"/api/v1/evaluations/postures/{self.posture.pk}/ai-recommendations/"
        self.login(self.engineer.email)
        self.headers = self.csrf()

    def test_sends_the_photo_to_gemini_without_storing_it(self):
        patcher, create = fake_gemini()
        with patcher:
            response = self.client.post(self.url, format="json", **self.headers)
        self.assertEqual(response.status_code, 200, response.content)
        kwargs = create.call_args.kwargs
        self.assertEqual((kwargs["model"], kwargs["store"]), ("gemini-4-hydrogen", False))
        self.assertEqual((kwargs["input"][0]["type"], kwargs["input"][0]["mime_type"]), ("image", "image/jpeg"))
        # Gemini no admite anyOf con null: el esquema llega con el tipo simple.
        self.assertEqual(kwargs["response_format"]["schema"]["properties"]["caution"], {"type": "string"})
        advice = response.json()["result"]["ai_advice"]
        self.assertEqual((advice["source"], advice["model"]), ("ia", "gemini-4-hydrogen"))

    def test_quota_exhausted_falls_back_to_the_catalog(self):
        from google.genai import errors

        patcher, _ = fake_gemini(error=errors.ClientError(429, {"error": {"message": "quota"}}))
        with patcher:
            advice = self.client.post(self.url, format="json", **self.headers).json()["result"]["ai_advice"]
        self.assertEqual(advice["source"], "catalogo")
        self.assertIn("límite gratuito", advice["notice"])
class AdviceCleaningTests(TestCase):
    def test_invalid_values_are_normalized_and_capped(self):
        items = [{"text": f"  Recomendación   {i} ", "focus": "oreja", "kind": "magia", "priority": "urgente"} for i in range(9)]
        cleaned = advisor.clean_advice({"observations": "x", "recommendations": items, "caution": 3})
        self.assertEqual(len(cleaned["items"]), advisor.MAX_ITEMS)
        self.assertEqual(cleaned["items"][0], {"text": "Recomendación 0", "focus": "general", "kind": "ingenieria", "priority": "media"})
        self.assertIsNone(cleaned["caution"])


class CatalogTests(TestCase):
    def test_the_highest_scores_get_the_first_recommendations(self):
        engineer = make_user(role=Role.ENGINEER)
        assessment = make_assessment(make_posture(make_evaluation(engineer)), trunk_angle="70", neck_angle="30")
        items = advisor.catalog_advice(assessment).data["items"]
        self.assertEqual(items[0]["priority"], "alta")
        self.assertIn("tronco", {item["focus"] for item in items})
        self.assertLessEqual(len(items), advisor.MAX_ITEMS)
