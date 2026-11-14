from datetime import date, timedelta
from unittest import mock

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
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






