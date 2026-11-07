import json
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.db.models import RestrictedError
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import Role
from apps.core.tests.factories import (
    at,
    completed_visit,
    make_area,
    make_company,
    make_position,
    make_site,
    make_user,
    make_visit,
    make_worker,
)
from apps.evaluations import services
from apps.evaluations.forms import EvaluationForm, PostureForm, RulaAssessmentForm
from apps.evaluations.models import Evaluation, Posture, PosturePhoto, Recommendation, RulaAssessment
from apps.evaluations.photos import InvalidPhoto, process_photo
from apps.evaluations.selectors import visible_evaluations
from apps.rula.scoring import Load
from apps.visits.models import Visit


def image_bytes(fmt="JPEG", size=(40, 30), **save_options):
    output = BytesIO()
    Image.new("RGB", size, "teal").save(output, format=fmt, **save_options)
    return output.getvalue()


def upload(name="foto.jpg", content=None, content_type="image/jpeg"):
    return SimpleUploadedFile(name, content if content is not None else image_bytes(), content_type)


def make_evaluation(user, position=None, **fields):
    position = position or make_position()
    defaults = {"evaluated_on": timezone.localdate(), "activity_description": "Empaca cajas"}
    if "visit" not in fields:
        fields["visit"] = completed_visit(position)
    return Evaluation.objects.create(position=position, evaluator=user, **{**defaults, **fields})


def make_posture(evaluation, name="Empaque en banda"):
    return Posture.objects.create(evaluation=evaluation, name=name, duration_value=5)


ASSESSMENT_INPUT = {
    # Caso calculado a mano en apps/rula/tests: resultado 6, nivel de accion 3.
    "upper_arm_angle": "30",
    "shoulder_raised": "on",
    "lower_arm_angle": "110",
    "wrist_angle": "10",
    "wrist_bent_from_midline": "on",
    "arm_static_or_repeated": "on",
    "arm_load": Load.MEDIUM_INTERMITTENT.name,
    "neck_angle": "15",
    "neck_twisted": "on",
    "trunk_angle": "30",
    "legs_supported_and_balanced": "on",
    "body_load": Load.NONE_OR_LIGHT_INTERMITTENT.name,
}


def make_assessment(posture, **changes):
    photo = posture.photos.first() or services.add_photo(posture, upload())
    form = RulaAssessmentForm(
        data={**ASSESSMENT_INPUT, "photo": photo.pk, **changes},
        posture=posture,
        photos=PosturePhoto.objects.filter(posture=posture),
    )
    assert form.is_valid(), form.errors
    return form.save()


class PhotoProcessingTests(TestCase):
    def test_converts_to_jpeg_and_limits_size(self):
        result = process_photo(upload("foto.png", image_bytes("PNG", (3000, 1500))))
        self.assertEqual(result.content_type, "image/jpeg")
        self.assertEqual((result.width, result.height), (1600, 800))

    def test_removes_metadata(self):
        exif = Image.Exif()
        exif[0x010F] = "CamaraDePrueba"
        result = process_photo(upload(content=image_bytes(exif=exif)))
        self.assertNotIn(b"CamaraDePrueba", result.data)
        self.assertFalse(Image.open(BytesIO(result.data)).getexif())

    def test_applies_phone_rotation(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # El celular guardo la foto girada 90 grados.
        result = process_photo(upload(content=image_bytes(size=(40, 30), exif=exif)))
        self.assertEqual((result.width, result.height), (30, 40))

    def test_rejects_fake_images(self):
        for content in (b"<script>alert(1)</script>", b"", b"\xff\xd8\xff corrupto"):
            with self.assertRaises(InvalidPhoto):
                process_photo(upload(content=content))

    def test_rejects_other_formats(self):
        with self.assertRaisesMessage(InvalidPhoto, "JPG, PNG o WEBP"):
            process_photo(upload("foto.gif", image_bytes("GIF")))

    def test_rejects_files_too_large(self):
        big = upload()
        big.size = 11 * 1024 * 1024
        with self.assertRaisesMessage(InvalidPhoto, "10 MB"):
            process_photo(big)

    def test_rejects_too_many_pixels_before_decoding(self):
        with mock.patch("apps.evaluations.photos.MAX_PIXELS", 100):
            with self.assertRaisesMessage(InvalidPhoto, "resolución"):
                process_photo(upload())


class EvaluationFormTests(TestCase):
    """Sin visita realizada no hay evaluacion, y el puesto sale de la sede visitada."""

    def setUp(self):
        self.user = make_user(role=Role.ENGINEER)
        self.position = make_position()
        self.area = self.position.area
        self.site = self.area.site
        self.company = self.site.company
        self.visit = completed_visit(self.position, days_ago=3)

    def data(self, **changes):
        return {
            "visit": self.visit.pk,
            "area": self.area.pk,
            "position": self.position.pk,
            "evaluated_on": timezone.localdate().isoformat(),
            "activity_description": "Empaca cajas en la banda",
            **changes,
        }

    def form(self, **changes):
        return EvaluationForm(data=self.data(**changes), user=self.user)

    def test_saves_with_engineer_as_author_and_the_visit(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        evaluation = form.save()
        self.assertEqual(evaluation.evaluator, self.user)
        self.assertEqual(evaluation.visit, self.visit)
        self.assertEqual(evaluation.company, self.company)
        self.assertTrue(evaluation.is_draft)

    def test_visit_is_required(self):
        self.assertIn("visit", self.form(visit="").errors)

    def test_only_completed_visits_are_offered(self):
        for status in (Visit.Status.SCHEDULED, Visit.Status.CANCELLED):
            day = timezone.localdate() - timedelta(days=1)
            visit = make_visit(site=self.site, scheduled_at=at(day, 15), status=status)
            self.assertIn("visit", self.form(visit=visit.pk).errors, status)

    def test_position_must_belong_to_the_visited_site(self):
        other_site = make_site(self.company, name="Otra sede")
        foreign = make_position(make_area(other_site, name="Bodega"), name="Auxiliar")
        self.assertIn("position", self.form(position=foreign.pk).errors)
        self.assertIn("area", self.form(area=foreign.area.pk, position=foreign.pk).errors)

    def test_worker_must_belong_to_the_position(self):
        mine = make_worker(self.position)
        other = make_worker(make_position(self.area, name="Sellado"))
        self.assertTrue(self.form(worker=mine.pk).is_valid())
        self.assertIn("worker", self.form(worker=other.pk).errors)

    def test_date_cannot_be_before_the_visit_or_future(self):
        before = (timezone.localdate() - timedelta(days=5)).isoformat()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertIn("evaluated_on", self.form(evaluated_on=before).errors)
        self.assertIn("evaluated_on", self.form(evaluated_on=tomorrow).errors)

    def test_activity_is_required(self):
        self.assertIn("activity_description", self.form(activity_description="").errors)

    def test_weight_requires_load(self):
        self.assertIn("load_weight_kg", self.form(load_weight_kg="5").errors)
        self.assertTrue(self.form(carries_load="on", load_weight_kg="5").is_valid())

    def test_unknown_weight_is_allowed(self):
        self.assertTrue(self.form(carries_load="on").is_valid())

    def test_visit_of_an_inactive_company_is_not_offered(self):
        self.company.is_active = False
        self.company.save()
        self.assertIn("visit", self.form().errors)

    def test_database_requires_a_visit(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Evaluation.objects.create(
                position=self.position, evaluator=self.user, evaluated_on=timezone.localdate(), activity_description="x"
            )


class PostureRulesTests(TestCase):
    def setUp(self):
        self.user = make_user(role=Role.ENGINEER)
        self.evaluation = make_evaluation(self.user)

    def data(self, **changes):
        return {"name": "Empaque", "side": "derecho", "duration_value": "5", "duration_unit": "minutos", **changes}

    def test_duration_requires_a_positive_value_and_unit(self):
        form = PostureForm(data=self.data(duration_value="0"), evaluation=self.evaluation)
        self.assertIn("duration_value", form.errors)
        form = PostureForm(data=self.data(duration_unit=""), evaluation=self.evaluation)
        self.assertIn("duration_unit", form.errors)

    def test_same_posture_and_side_is_rejected_ignoring_case_and_spaces(self):
        PostureForm(data=self.data(), evaluation=self.evaluation).save()
        form = PostureForm(data=self.data(name="  EMPAQUE "), evaluation=self.evaluation)
        self.assertIn("name", form.errors)

    def test_same_posture_on_the_other_side_is_allowed(self):
        PostureForm(data=self.data(), evaluation=self.evaluation).save()
        self.assertTrue(PostureForm(data=self.data(side="izquierdo"), evaluation=self.evaluation).is_valid())

    def test_database_rejects_duplicates(self):
        make_posture(self.evaluation, "Empaque")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_posture(self.evaluation, "EMPAQUE")


class AssessmentTests(TestCase):
    def setUp(self):
        self.user = make_user(role=Role.ENGINEER)
        self.posture = make_posture(make_evaluation(self.user))

    def test_saved_scores_match_the_case_worked_by_hand(self):
        assessment = make_assessment(self.posture)
        self.assertEqual(assessment.grand_score, 6)
        self.assertEqual(assessment.action_level, 3)
        self.assertEqual(assessment.partial_scores["score_c"], 6)
        self.assertEqual(assessment.partial_scores["score_d"], 4)
        self.assertEqual(assessment.partial_scores["posture_a"], 4)

    def test_repeating_recalculates_and_keeps_one_record(self):
        existing = make_assessment(self.posture)
        form = RulaAssessmentForm(
            data={
                "photo": existing.photo_id,
                "upper_arm_angle": "0",
                "lower_arm_angle": "80",
                "wrist_angle": "0",
                "neck_angle": "0",
                "trunk_angle": "0",
                "legs_supported_and_balanced": "on",
                "arm_load": Load.NONE_OR_LIGHT_INTERMITTENT.name,
                "body_load": Load.NONE_OR_LIGHT_INTERMITTENT.name,
            },
            instance=existing,
            posture=self.posture,
            photos=PosturePhoto.objects.filter(posture=self.posture),
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(RulaAssessment.objects.filter(posture=self.posture).count(), 1)
        self.assertEqual(RulaAssessment.objects.get(posture=self.posture).grand_score, 1)

    def test_trunk_extension_shows_an_error_and_saves_nothing(self):
        photo = services.add_photo(self.posture, upload())
        form = RulaAssessmentForm(
            data={**ASSESSMENT_INPUT, "photo": photo.pk, "trunk_angle": "-5"},
            posture=self.posture,
            photos=PosturePhoto.objects.filter(posture=self.posture),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("extensión", form.non_field_errors()[0])

    def test_photo_of_another_posture_is_rejected(self):
        services.add_photo(self.posture, upload())
        other = make_posture(self.posture.evaluation, "Otra")
        foreign = services.add_photo(other, upload())
        form = RulaAssessmentForm(
            data={**ASSESSMENT_INPUT, "photo": foreign.pk},
            posture=self.posture,
            photos=PosturePhoto.objects.filter(posture=self.posture),
        )
        self.assertIn("photo", form.errors)

    def test_analyzed_photo_cannot_be_deleted_alone(self):
        assessment = make_assessment(self.posture)
        with self.assertRaises(RestrictedError):
            assessment.photo.delete()

    def test_deleting_the_posture_removes_everything(self):
        make_assessment(self.posture)
        self.posture.delete()
        self.assertEqual(PosturePhoto.objects.count(), 0)
        self.assertEqual(RulaAssessment.objects.count(), 0)

    def test_scores_out_of_range_are_rejected_by_database(self):
        assessment = make_assessment(self.posture)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RulaAssessment.objects.filter(pk=assessment.pk).update(grand_score=8)


class CompletionTests(TestCase):
    def setUp(self):
        self.user = make_user(role=Role.ENGINEER)
        self.evaluation = make_evaluation(self.user)

    def test_needs_a_posture(self):
        with self.assertRaises(services.EvaluationIncomplete):
            services.complete_evaluation(self.evaluation)

    def test_needs_the_analysis_of_every_posture(self):
        make_assessment(make_posture(self.evaluation, "Una"), upper_arm_angle="0", shoulder_raised="", lower_arm_angle="80", wrist_angle="0", wrist_bent_from_midline="", arm_static_or_repeated="", arm_load=Load.NONE_OR_LIGHT_INTERMITTENT.name, neck_angle="0", neck_twisted="", trunk_angle="0")
        make_posture(self.evaluation, "Otra")
        self.assertIn("Otra", services.completion_problems(self.evaluation)[0])

    def test_problem_levels_need_a_recommendation(self):
        posture = make_posture(self.evaluation)
        make_assessment(posture)
        self.assertIn("recomendación", services.completion_problems(self.evaluation)[0])
        Recommendation.objects.create(posture=posture, text="Ajustar altura", author=self.user)
        services.complete_evaluation(self.evaluation)
        self.assertFalse(self.evaluation.is_draft)
        self.assertIsNotNone(self.evaluation.completed_at)

    def test_acceptable_level_does_not_need_a_recommendation(self):
        posture = make_posture(self.evaluation)
        make_assessment(
            posture, upper_arm_angle="0", shoulder_raised="", lower_arm_angle="80", wrist_angle="0",
            wrist_bent_from_midline="", arm_static_or_repeated="",
            arm_load=Load.NONE_OR_LIGHT_INTERMITTENT.name, neck_angle="0", neck_twisted="", trunk_angle="0",
        )
        self.assertEqual(services.completion_problems(self.evaluation), [])

    def test_photo_limit(self):
        posture = make_posture(self.evaluation)
        with mock.patch.object(services, "MAX_PHOTOS_PER_POSTURE", 1):
            services.add_photo(posture, upload())
            with self.assertRaises(InvalidPhoto):
                services.add_photo(posture, upload())


class AccessTests(TestCase):
    """Matriz de quien puede hacer que, recorriendo los roles."""

    @classmethod
    def setUpTestData(cls):
        cls.author = make_user(role=Role.ENGINEER)
        cls.company = make_company(name="Mi empresa")
        cls.position = make_position(make_area(make_site(cls.company)))
        cls.foreign_position = make_position(make_area(make_site(make_company(name="Ajena")), name="Ajena"))

        cls.draft = make_evaluation(cls.author, cls.position)
        cls.posture = make_posture(cls.draft)
        cls.photo = services.add_photo(cls.posture, upload())

        cls.done = make_evaluation(cls.author, cls.position)
        cls.done_posture = make_posture(cls.done)
        cls.done_photo = services.add_photo(cls.done_posture, upload())
        make_assessment(cls.done_posture)
        Recommendation.objects.create(posture=cls.done_posture, text="Ajustar", author=cls.author)
        services.complete_evaluation(cls.done)

        cls.foreign_done = make_evaluation(cls.author, cls.foreign_position)
        foreign_posture = make_posture(cls.foreign_done)
        cls.foreign_photo = services.add_photo(foreign_posture, upload())
        make_assessment(foreign_posture)
        Recommendation.objects.create(posture=foreign_posture, text="Ajustar", author=cls.author)
        services.complete_evaluation(cls.foreign_done)

    def login(self, role, **fields):
        user = make_user(role=role, **fields)
        self.client.force_login(user)
        return user

    def detail(self, evaluation):
        return reverse("evaluations:detail", args=[evaluation.pk])

    def test_anonymous_goes_to_login_also_for_photos(self):
        for url in (
            reverse("evaluations:list"),
            self.detail(self.done),
            reverse("evaluations:photo", args=[self.photo.pk]),
        ):
            self.assertIn("/ingresar/", self.client.get(url)["Location"])

    def test_engineer_sees_all_evaluations(self):
        self.login(Role.ENGINEER)
        self.assertEqual(len(self.client.get(reverse("evaluations:list")).context["evaluations"]), 3)

    def test_company_user_sees_only_its_completed_evaluations(self):
        self.login(Role.COMPANY, company=self.company)
        listed = {e.pk for e in self.client.get(reverse("evaluations:list")).context["evaluations"]}
        self.assertEqual(listed, {self.done.pk})
        self.assertEqual(self.client.get(self.detail(self.foreign_done)).status_code, 404)
        self.assertEqual(self.client.get(self.detail(self.draft)).status_code, 404)

    def test_support_has_no_access_to_evaluations(self):
        self.login(Role.ADMIN)
        self.assertEqual(self.client.get(reverse("evaluations:list")).status_code, 403)
        self.assertEqual(self.client.get(self.detail(self.done)).status_code, 403)
        self.assertEqual(self.client.get(reverse("evaluations:photo", args=[self.done_photo.pk])).status_code, 403)

    def test_only_the_engineer_can_create(self):
        url = reverse("evaluations:create")
        self.login(Role.ENGINEER)
        self.assertEqual(self.client.get(url).status_code, 200)
        for role in (Role.ADMIN, Role.COMPANY):
            fields = {"company": self.company} if role == Role.COMPANY else {}
            self.login(role, **fields)
            self.assertEqual(self.client.get(url).status_code, 403, role)

    def test_photo_follows_the_scope_of_its_evaluation(self):
        self.login(Role.COMPANY, company=self.company)
        allowed = self.client.get(reverse("evaluations:photo", args=[self.done_photo.pk]))
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed["Content-Type"], "image/jpeg")
        self.assertIn("private", allowed["Cache-Control"])
        for photo in (self.foreign_photo, self.photo):
            self.assertEqual(self.client.get(reverse("evaluations:photo", args=[photo.pk])).status_code, 404)

    def test_another_evaluator_cannot_modify_a_draft(self):
        self.login(Role.ENGINEER)
        for url, method in (
            (reverse("evaluations:update", args=[self.draft.pk]), "get"),
            (reverse("evaluations:posture_create", args=[self.draft.pk]), "get"),
            (reverse("evaluations:assessment", args=[self.posture.pk]), "get"),
            (reverse("evaluations:complete", args=[self.draft.pk]), "post"),
            (reverse("evaluations:posture_delete", args=[self.posture.pk]), "post"),
            (reverse("evaluations:photo_delete", args=[self.photo.pk]), "post"),
            (reverse("evaluations:photo_upload", args=[self.posture.pk]), "post"),
        ):
            self.assertEqual(getattr(self.client, method)(url).status_code, 404, url)
        self.assertTrue(Posture.objects.filter(pk=self.posture.pk).exists())

    def test_completed_evaluation_is_read_only_even_for_its_author(self):
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(reverse("evaluations:update", args=[self.done.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("evaluations:assessment", args=[self.done_posture.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("evaluations:photo_delete", args=[self.done_photo.pk])).status_code, 404
        )
        response = self.client.get(self.detail(self.done))
        self.assertFalse(response.context["can_edit"])
        self.assertNotContains(response, "Repetir análisis")

    def test_read_only_detail_hides_actions(self):
        self.login(Role.COMPANY, company=self.company)
        response = self.client.get(self.detail(self.done))
        for text in ("Agregar postura", "Subir", "Nueva recomendación", "Terminar", "Reabrir"):
            self.assertNotContains(response, text)
        self.assertContains(response, "Ajustar")

    def test_only_the_engineer_reopens(self):
        url = reverse("evaluations:reopen", args=[self.done.pk])
        for role, fields in ((Role.ADMIN, {}), (Role.COMPANY, {"company": self.company})):
            self.login(role, **fields)
            self.assertEqual(self.client.post(url).status_code, 403, role)
        self.client.force_login(self.author)
        self.assertContains(self.client.get(self.detail(self.done)), "Reabrir")
        self.client.post(url)
        self.done.refresh_from_db()
        self.assertTrue(self.done.is_draft)
        self.assertIsNone(self.done.completed_at)

    def test_get_does_not_change_state(self):
        self.client.force_login(self.author)
        for name, pk in (("complete", self.draft.pk), ("posture_delete", self.posture.pk), ("photo_delete", self.photo.pk)):
            self.assertEqual(self.client.get(reverse(f"evaluations:{name}", args=[pk])).status_code, 405)


class FlowTests(TestCase):
    def setUp(self):
        self.user = make_user(role=Role.ENGINEER)
        self.client.force_login(self.user)
        self.evaluation = make_evaluation(self.user)
        self.posture = make_posture(self.evaluation)
        self.detail = reverse("evaluations:detail", args=[self.evaluation.pk])

    def test_saving_a_posture_in_the_modal_reloads_the_page(self):
        response = self.client.post(
            reverse("evaluations:posture_create", args=[self.evaluation.pk]),
            {"name": "Nueva", "side": "derecho", "duration_value": "3", "duration_unit": "minutos"},
            HTTP_HX_REQUEST="true",
        )
        posture = Posture.objects.get(name="Nueva")
        # Un #fragmento en esta URL haria que el navegador no recargue.
        self.assertEqual(response["HX-Redirect"], f"{self.detail}?foco=postura-{posture.pk}")

    def test_assessment_needs_a_photo_first(self):
        response = self.client.get(reverse("evaluations:assessment", args=[self.posture.pk]))
        self.assertRedirects(response, f"{self.detail}#postura-{self.posture.pk}")

    def test_upload_analyze_recommend_and_complete(self):
        self.client.post(reverse("evaluations:photo_upload", args=[self.posture.pk]), {"photo": upload()})
        photo = PosturePhoto.objects.get(posture=self.posture)

        url = reverse("evaluations:assessment", args=[self.posture.pk])
        self.assertContains(self.client.get(url), reverse("evaluations:photo", args=[photo.pk]))
        response = self.client.post(url, {**ASSESSMENT_INPUT, "photo": photo.pk})
        self.assertEqual(response.status_code, 302)

        page = self.client.get(self.detail)
        self.assertContains(page, "Se requiere investigar y hacer cambios pronto.")
        self.assertContains(page, "Requiere revisión · Nivel 3")
        self.assertContains(page, "Falta una recomendación")

        self.client.post(reverse("evaluations:recommendation_create", args=[self.posture.pk]), {"text": "Bajar la banda"})
        self.assertEqual(Recommendation.objects.get().author, self.user)

        self.client.post(reverse("evaluations:complete", args=[self.evaluation.pk]))
        self.evaluation.refresh_from_db()
        self.assertFalse(self.evaluation.is_draft)

    def test_recommendation_is_only_possible_after_the_result(self):
        url = reverse("evaluations:recommendation_create", args=[self.posture.pk])
        self.client.post(url, {"text": "Antes de tiempo"})
        self.assertEqual(Recommendation.objects.count(), 0)
        self.assertNotContains(self.client.get(self.detail), "Nueva recomendación")

    def test_incomplete_evaluation_is_not_completed_by_forcing_the_post(self):
        self.client.post(reverse("evaluations:complete", args=[self.evaluation.pk]))
        self.evaluation.refresh_from_db()
        self.assertTrue(self.evaluation.is_draft)

    def test_invalid_upload_shows_error_and_saves_nothing(self):
        response = self.client.post(
            reverse("evaluations:photo_upload", args=[self.posture.pk]),
            {"photo": upload("virus.jpg", b"no es imagen")},
            follow=True,
        )
        self.assertContains(response, "no es una fotografía válida")
        self.assertContains(response, "toast-error")
        self.assertEqual(PosturePhoto.objects.count(), 0)

    def test_deleting_analyzed_photo_shows_a_message(self):
        assessment = make_assessment(self.posture)
        response = self.client.post(
            reverse("evaluations:photo_delete", args=[assessment.photo_id]), follow=True
        )
        self.assertContains(response, "sustenta el análisis")
        self.assertEqual(PosturePhoto.objects.count(), 1)

    def test_starting_from_a_visit_selects_it_and_its_date(self):
        visit = self.evaluation.visit
        response = self.client.get(reverse("evaluations:create"), {"visita": visit.pk})
        form = response.context["form"]
        self.assertEqual(form.initial["visit"], visit.pk)
        self.assertEqual(form.initial["evaluated_on"], timezone.localdate(visit.scheduled_at))
        self.assertIn(self.evaluation.position.area, form.fields["area"].queryset)

    def test_bad_visit_parameter_does_not_crash(self):
        for value in ("abc", "999999", "'; DROP"):
            self.assertEqual(self.client.get(reverse("evaluations:create"), {"visita": value}).status_code, 200)

    def test_cascade_offers_the_areas_of_the_visited_site(self):
        visit = self.evaluation.visit
        response = self.client.get(reverse("evaluations:cascade"), {"visit": visit.pk})
        self.assertContains(response, self.evaluation.position.area.name)

    def test_worst_score_is_shown_not_an_average(self):
        make_assessment(self.posture)
        low = make_posture(self.evaluation, "Baja")
        make_assessment(
            low, upper_arm_angle="0", shoulder_raised="", lower_arm_angle="80", wrist_angle="0",
            wrist_bent_from_midline="", arm_static_or_repeated="",
            arm_load=Load.NONE_OR_LIGHT_INTERMITTENT.name, neck_angle="0", neck_twisted="", trunk_angle="0",
        )
        self.assertEqual(visible_evaluations(self.user).get(pk=self.evaluation.pk).worst_score, 6)

    def test_search_by_code_company_and_position(self):
        url = reverse("evaluations:list")
        code = self.evaluation.code
        for query in (code, code.lower(), self.evaluation.company.name[:5], self.evaluation.position.name[:5]):
            found = [e.pk for e in self.client.get(url, {"q": query}).context["evaluations"]]
            self.assertIn(self.evaluation.pk, found, query)
        self.assertEqual(list(self.client.get(url, {"q": "zzz-no-existe"}).context["evaluations"]), [])

    def test_user_text_is_escaped(self):
        Recommendation.objects.create(posture=self.posture, text="<script>x</script>", author=self.user)
        make_assessment(self.posture)
        response = self.client.get(self.detail)
        self.assertNotContains(response, "<script>x</script>")

    def test_detail_does_not_load_image_bytes(self):
        make_assessment(self.posture)
        with CaptureQueriesContext(connection) as captured:
            self.client.get(self.detail)
        photo_queries = [q["sql"] for q in captured.captured_queries if "posturephoto" in q["sql"]]
        self.assertTrue(photo_queries)
        for sql in photo_queries:
            self.assertNotIn('"data"', sql)

    def test_detail_query_count_does_not_grow_with_postures(self):
        make_assessment(self.posture)
        with CaptureQueriesContext(connection) as one_posture:
            self.client.get(self.detail)
        for index in range(4):
            make_assessment(make_posture(self.evaluation, f"Postura {index}"))
        with self.assertNumQueries(len(one_posture)):
            self.client.get(self.detail)


class AiSuggestionTests(TestCase):
    """La sugerencia de la IA solo deja constancia: nunca cambia lo que registra el evaluador."""

    def setUp(self):
        self.user = make_user(role=Role.ENGINEER)
        self.posture = make_posture(make_evaluation(self.user))

    def suggestion(self, **angles):
        values = {"upper_arm_angle": 32.5, "lower_arm_angle": 110, "wrist_angle": 10, "neck_angle": 15, "trunk_angle": 30}
        return json.dumps({"photo": 1, "side": "derecho", "model": "mediapipe-pose-lite@0.10.14", "angles": {**values, **angles}})

    def test_suggestion_is_stored_apart_and_scores_use_registered_values(self):
        assessment = make_assessment(self.posture, ai_suggestion=self.suggestion(upper_arm_angle=95))
        self.assertEqual(assessment.ai_suggestion["angles"]["upper_arm_angle"], 95)
        self.assertEqual(assessment.grand_score, 6)  # el mismo del caso calculado a mano
        changed = {row["label"]: row["changed"] for row in assessment.ai_comparison}
        self.assertTrue(changed["Ángulo del brazo"])
        self.assertFalse(changed["Ángulo del tronco"])

    def test_malformed_or_hostile_values_are_discarded(self):
        for raw in ("no es json", "[1, 2]", json.dumps({"angles": "x"}), json.dumps({"angles": {"trunk_angle": True}})):
            self.assertEqual(make_assessment(make_posture(self.posture.evaluation, raw[:20]), ai_suggestion=raw).ai_suggestion, {}, raw)
        assessment = make_assessment(
            make_posture(self.posture.evaluation, "Fuera de rango"),
            ai_suggestion=json.dumps({"angles": {"trunk_angle": 999, "neck_angle": "15", "wrist_angle": 7.3}, "side": "<b>", "photo": "1"}),
        )
        self.assertEqual(
            assessment.ai_suggestion["angles"],
            {"upper_arm_angle": None, "lower_arm_angle": None, "wrist_angle": 7.5, "neck_angle": None, "trunk_angle": None},
        )
        self.assertIsNone(assessment.ai_suggestion["side"])
        self.assertFalse(assessment.ai_suggestion["frontal"])
        self.assertIsNone(assessment.ai_suggestion["photo"])

    def test_without_suggestion_nothing_is_stored(self):
        self.assertEqual(make_assessment(self.posture).ai_suggestion, {})

    def test_page_offers_the_assistant_and_detail_shows_the_trace(self):
        self.client.force_login(self.user)
        make_assessment(self.posture, ai_suggestion=self.suggestion(neck_angle=25))
        page = self.client.get(reverse("evaluations:assessment", args=[self.posture.pk]))
        self.assertContains(page, "data-pose-assist")
        self.assertContains(page, 'data-side="derecho"')
        self.assertContains(page, "pose-assist.js")
        detail = self.client.get(reverse("evaluations:detail", args=[self.posture.evaluation.pk]))
        self.assertContains(detail, "Ángulos medidos con apoyo de IA")
        self.assertContains(detail, "corregido")
