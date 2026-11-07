from datetime import date, timedelta
from unittest import mock

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.core.tests.factories import (
    at,
    make_company,
    make_contract,
    make_site,
    make_user,
    make_visit,
)
from apps.visits import rules
from apps.visits.forms import VisitForm
from apps.visits.models import Visit

HTMX = {"HTTP_HX_REQUEST": "true"}


def next_weekday(weekday: int, after: date | None = None) -> date:
    """El proximo dia de la semana pedido (0 = lunes), al menos dos dias despues de hoy."""
    day = (after or timezone.localdate()) + timedelta(days=2)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day


class VisitTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(name="Mi empresa")
        cls.site = make_site(cls.company)
        cls.contract = make_contract(cls.company)
        cls.foreign = make_company(name="Ajena")
        cls.foreign_site = make_site(cls.foreign, name="Sede ajena")
        make_contract(cls.foreign)
        cls.member = make_user(role=Role.COMPANY, company=cls.company)
        cls.engineer = make_user(role=Role.ENGINEER)
        cls.tuesday = next_weekday(1)

    def data(self, **changes):
        return {
            "date": self.tuesday.isoformat(),
            "time": "09:00",
            "duration_minutes": "120",
            "site": self.site.pk,
            "purpose": "Evaluar empaque",
            "contact_name": "Marta Salazar",
            **changes,
        }

    def form(self, user=None, instance=None, **changes):
        return VisitForm(data=self.data(**changes), user=user or self.member, instance=instance)


class VisitRuleTests(VisitTestCase):
    def errors(self, **changes):
        form = self.form(**changes)
        self.assertFalse(form.is_valid())
        return " ".join(form.non_field_errors())

    def test_valid_visit_saves_local_time_and_who_scheduled_it(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        visit = form.save()
        self.assertEqual(timezone.localtime(visit.scheduled_at).hour, 9)
        self.assertEqual(visit.requested_by, self.member)
        self.assertEqual(visit.status, Visit.Status.SCHEDULED)
        self.assertEqual(visit.company, self.company)

    def test_needs_one_hour_of_notice(self):
        soon = timezone.localtime() + timedelta(minutes=30)
        with mock.patch.object(rules, "WORK_START", soon.time().replace(hour=0)), \
                mock.patch.object(rules, "WORK_END", soon.time().replace(hour=23, minute=59)):
            message = self.errors(date=soon.date().isoformat(), time=soon.strftime("%H:%M"), duration_minutes="60")
        self.assertIn("una hora de anticipación", message)

    def test_sundays_and_after_hours_are_rejected(self):
        self.assertIn("lunes a sábado", self.errors(date=next_weekday(6).isoformat()))
        self.assertIn("terminar a más tardar", self.errors(time="17:00"))
        self.assertIn("empezar desde", self.errors(time="06:00"))

    def test_date_outside_the_contract_is_rejected(self):
        late = next_weekday(1, after=self.contract.end_date)
        self.assertIn("contrato vigente", self.errors(date=late.isoformat()))

    def test_company_without_contract_cannot_schedule(self):
        company = make_company(name="Sin contrato")
        site = make_site(company)
        user = make_user(role=Role.COMPANY, company=company)
        form = VisitForm(data=self.data(site=site.pk), user=user)
        self.assertFalse(form.is_valid())
        self.assertIn("contrato vigente", " ".join(form.non_field_errors()))

    def test_overlap_with_any_company_is_rejected(self):
        make_visit(self.foreign_site, at(self.tuesday, 10))
        self.assertIn("ya tiene una visita", self.errors(time="09:00"))
        self.assertTrue(self.form(time="12:00").is_valid())

    def test_cancelled_visits_free_their_slot(self):
        make_visit(self.foreign_site, at(self.tuesday, 9), status=Visit.Status.CANCELLED)
        self.assertTrue(self.form().is_valid())

    def test_back_to_back_visits_are_allowed(self):
        make_visit(self.foreign_site, at(self.tuesday, 7))
        self.assertTrue(self.form(time="09:00").is_valid())

    def test_site_of_another_company_is_rejected(self):
        self.assertIn("site", self.form(site=self.foreign_site.pk).errors)

    def test_rescheduling_does_not_collide_with_itself(self):
        visit = make_visit(self.site, at(self.tuesday, 9), duration_minutes=120)
        form = self.form(instance=visit, time="10:00")
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_only_the_purpose_skips_the_schedule_rules(self):
        # Aunque la fecha ya no cumpla una regla nueva, cambiar el motivo no obliga a moverla.
        visit = make_visit(self.site, at(self.tuesday, 9), duration_minutes=120)
        visit.duration_minutes = 120
        with mock.patch.object(rules, "WORK_START", rules.WORK_START.replace(hour=10)):
            form = self.form(instance=visit, purpose="Otro motivo")
            self.assertTrue(form.is_valid(), form.errors)

    def test_database_checks_completed_and_cancelled_states(self):
        visit = make_visit(self.site)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Visit.objects.filter(pk=visit.pk).update(status=Visit.Status.COMPLETED)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Visit.objects.filter(pk=visit.pk).update(status=Visit.Status.CANCELLED)

    def test_site_with_visits_cannot_be_deleted(self):
        make_visit(self.site)
        with self.assertRaises(ProtectedError):
            self.site.delete()


class VisitAccessTests(VisitTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.visit = make_visit(cls.site, at(cls.tuesday, 9))
        cls.foreign_visit = make_visit(cls.foreign_site, at(cls.tuesday, 14))

    def test_anonymous_is_sent_to_login(self):
        for url in (reverse("visits:list"), reverse("visits:create"), reverse("visits:detail", args=[self.visit.pk])):
            self.assertIn("/ingresar/", self.client.get(url)["Location"])

    def test_only_the_company_schedules(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("visits:create")).status_code, 200)
        for user in (self.engineer, make_user(role=Role.ADMIN)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("visits:create")).status_code, 403, user.role)
            self.assertEqual(self.client.post(reverse("visits:create"), self.data()).status_code, 403)
        self.assertEqual(Visit.objects.count(), 2)

    def test_company_only_sees_and_changes_its_visits(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("visits:detail", args=[self.foreign_visit.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("visits:update", args=[self.foreign_visit.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("visits:cancel", args=[self.foreign_visit.pk]), {"cancellation_reason": "x"}).status_code,
            404,
        )

    def test_support_sees_no_visits(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertEqual(self.client.get(reverse("visits:detail", args=[self.visit.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("visits:agenda")).status_code, 403)

    def test_engineer_cannot_reschedule(self):
        self.client.force_login(self.engineer)
        self.assertEqual(self.client.get(reverse("visits:update", args=[self.visit.pk])).status_code, 403)

    def test_company_cannot_mark_a_visit_as_done(self):
        past = make_visit(self.site, at(timezone.localdate() - timedelta(days=1), 9))
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(reverse("visits:complete", args=[past.pk])).status_code, 403)
        past.refresh_from_db()
        self.assertTrue(past.is_scheduled)


class VisitLifecycleTests(VisitTestCase):
    def test_company_schedules_from_the_modal_and_returns_to_the_calendar(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("visits:create"), self.data(), **HTMX)
        self.assertEqual(response.status_code, 204)
        self.assertIn(f"fecha={self.tuesday.isoformat()}", response["HX-Redirect"])
        self.assertEqual(Visit.objects.get().requested_by, self.member)

    def test_errors_stay_in_the_modal(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("visits:create"), self.data(time="05:00"), **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "empezar desde")
        self.assertFalse(Visit.objects.exists())

    def test_slot_taken_at_the_same_moment_becomes_a_form_error(self):
        self.client.force_login(self.member)
        # Simula que otra empresa guardo ese horario justo despues de validar el formulario.
        with mock.patch.object(rules, "overlapping_visit", side_effect=[None, Visit()]):
            response = self.client.post(reverse("visits:create"), self.data(), **HTMX)
        self.assertContains(response, "acaba de tomar ese horario")
        self.assertFalse(Visit.objects.exists())

    def test_company_reschedules_and_cancels_with_a_reason(self):
        visit = make_visit(self.site, at(self.tuesday, 9))
        self.client.force_login(self.member)
        self.client.post(reverse("visits:update", args=[visit.pk]), self.data(time="13:00"))
        visit.refresh_from_db()
        self.assertEqual(timezone.localtime(visit.scheduled_at).hour, 13)

        self.assertContains(self.client.post(reverse("visits:cancel", args=[visit.pk]), {"cancellation_reason": ""}), "obligatorio")
        self.client.post(reverse("visits:cancel", args=[visit.pk]), {"cancellation_reason": "Inventario"})
        visit.refresh_from_db()
        self.assertEqual(visit.status, Visit.Status.CANCELLED)
        self.assertEqual(visit.cancelled_by, self.member)

    def test_company_cannot_cancel_a_visit_that_already_started(self):
        past = make_visit(self.site, at(timezone.localdate() - timedelta(days=1), 9))
        self.client.force_login(self.member)
        response = self.client.post(reverse("visits:cancel", args=[past.pk]), {"cancellation_reason": "Tarde"})
        self.assertEqual(response.status_code, 404)

    def test_engineer_records_a_past_visit_and_can_then_evaluate(self):
        past = make_visit(self.site, at(timezone.localdate() - timedelta(days=1), 9))
        self.client.force_login(self.engineer)
        detail = self.client.get(reverse("visits:detail", args=[past.pk]))
        self.assertContains(detail, "Por cerrar")
        self.assertContains(detail, "Registrar realizada")
        self.client.post(reverse("visits:complete", args=[past.pk]), {"completion_notes": "Todo bien"})
        past.refresh_from_db()
        self.assertTrue(past.is_completed)
        self.assertEqual(past.completed_by, self.engineer)
        self.assertContains(self.client.get(reverse("visits:detail", args=[past.pk])), "Nueva evaluación")

    def test_future_visit_cannot_be_marked_as_done(self):
        visit = make_visit(self.site, at(self.tuesday, 9))
        self.client.force_login(self.engineer)
        self.assertEqual(self.client.post(reverse("visits:complete", args=[visit.pk])).status_code, 404)

    def test_engineer_can_cancel_a_visit_that_did_not_happen(self):
        past = make_visit(self.site, at(timezone.localdate() - timedelta(days=1), 9))
        self.client.force_login(self.engineer)
        self.client.post(reverse("visits:cancel", args=[past.pk]), {"cancellation_reason": "La planta estaba cerrada"})
        past.refresh_from_db()
        self.assertEqual(past.status, Visit.Status.CANCELLED)

    def test_agenda_tabs(self):
        upcoming = make_visit(self.site, at(self.tuesday, 9))
        to_close = make_visit(self.site, at(timezone.localdate() - timedelta(days=2), 9))
        done = make_visit(self.site, at(timezone.localdate() - timedelta(days=3), 9), status=Visit.Status.COMPLETED)
        self.client.force_login(self.engineer)
        url = reverse("visits:agenda")
        self.assertEqual(list(self.client.get(url).context["visits"]), [upcoming])
        self.assertEqual(list(self.client.get(url, {"ver": "por_cerrar"}).context["visits"]), [to_close])
        self.assertEqual(list(self.client.get(url, {"ver": "historial"}).context["visits"]), [done])
        # La empresa no tiene la pestana de cierre: ve las proximas.
        self.client.force_login(self.member)
        self.assertEqual(list(self.client.get(url, {"ver": "por_cerrar"}).context["visits"]), [upcoming])


class VisitEvaluationsTests(VisitTestCase):
    def test_company_only_sees_completed_evaluations_of_the_visit(self):
        from apps.evaluations.models import Evaluation
        from apps.core.tests.factories import make_area, make_position

        visit = make_visit(self.site, at(timezone.localdate() - timedelta(days=2)), status=Visit.Status.COMPLETED)
        position = make_position(make_area(self.site))
        common = {"position": position, "visit": visit, "evaluator": self.engineer,
                  "evaluated_on": timezone.localdate(), "activity_description": "x"}
        draft = Evaluation.objects.create(**common)
        done = Evaluation.objects.create(**common, status=Evaluation.Status.COMPLETED, completed_at=timezone.now())
        self.client.force_login(self.member)
        listed = list(self.client.get(reverse("visits:detail", args=[visit.pk])).context["evaluations"])
        self.assertEqual(listed, [done])
        self.client.force_login(self.engineer)
        listed = list(self.client.get(reverse("visits:detail", args=[visit.pk])).context["evaluations"])
        self.assertEqual(listed, [draft, done])
