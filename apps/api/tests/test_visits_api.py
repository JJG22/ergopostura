from datetime import timedelta

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
from apps.visits.models import Visit
from apps.visits.tests.test_visits import next_weekday

from .test_api import ApiTestCase


class VisitsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.company = make_company(name="Mi empresa")
        self.site = make_site(self.company)
        make_contract(self.company)
        self.foreign = make_company(name="Ajena")
        self.foreign_site = make_site(self.foreign, name="Sede ajena")
        make_contract(self.foreign)
        self.member = make_user(role=Role.COMPANY, company=self.company, email="empresa@ergopostura.test")
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.tuesday = next_weekday(1)

    def payload(self, **changes):
        return {"date": self.tuesday.isoformat(), "time": "09:00", "duration_minutes": "120", "site": self.site.pk,
                "purpose": "Evaluar empaque", "contact_name": "Marta Salazar", **changes}

    def test_company_schedules_and_rules_come_from_the_form(self):
        self.login(self.member.email)
        headers = self.csrf()
        response = self.client.post("/api/v1/visits/", self.payload(time="06:00"), format="json", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("07:00", response.json()["error"]["message"])
        response = self.client.post("/api/v1/visits/", self.payload(), format="json", **headers)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["level"]["key"] in {"programada", "cercana"}, True)

    def test_company_cannot_use_a_foreign_site(self):
        self.login(self.member.email)
        response = self.client.post("/api/v1/visits/", self.payload(site=self.foreign_site.pk), format="json", **self.csrf())
        self.assertEqual(response.status_code, 400)
        self.assertIn("site", response.json()["error"]["fields"])

    def test_calendar_hides_other_companies_as_busy(self):
        make_visit(site=self.foreign_site, scheduled_at=at(self.tuesday, 9))
        own = make_visit(site=self.site, scheduled_at=at(self.tuesday, 14))
        self.login(self.member.email)
        data = self.client.get(f"/api/v1/visits/calendar/?view=semana&date={self.tuesday.isoformat()}").json()
        events = [e for day in data["days"] for e in day["events"]]
        busy = [e for e in events if e["busy"]]
        mine = [e for e in events if not e["busy"]]
        self.assertEqual(len(busy), 1)
        self.assertNotIn("company", busy[0])
        self.assertEqual(mine[0]["id"], own.pk)
        self.assertEqual(mine[0]["title"], self.site.name)
        self.assertTrue(data["can_schedule"])
        self.assertEqual(len(data["days"]), 7)

    def test_engineer_sees_all_and_has_no_schedule_button(self):
        make_visit(site=self.foreign_site, scheduled_at=at(self.tuesday, 9))
        self.login(self.engineer.email)
        data = self.client.get(f"/api/v1/visits/calendar/?date={self.tuesday.isoformat()}").json()
        events = [e for day in data["days"] for e in day["events"]]
        self.assertEqual([e["company"] for e in events], ["Ajena"])
        self.assertFalse(data["can_schedule"])
        self.assertEqual(data["view"], "mes")

    def test_engineer_completes_past_visit_and_company_cannot(self):
        past = make_visit(site=self.site, scheduled_at=timezone.now() - timedelta(hours=5))
        self.login(self.member.email)
        self.assertEqual(self.client.post(f"/api/v1/visits/{past.pk}/complete/", {}, format="json", **self.csrf()).status_code, 403)
        self.client.post("/api/v1/auth/logout/", **self.csrf())
        self.login(self.engineer.email)
        headers = self.csrf()
        agenda = self.client.get("/api/v1/visits/agenda/?tab=por_cerrar").json()
        self.assertEqual([v["id"] for v in agenda["results"]], [past.pk])
        response = self.client.post(f"/api/v1/visits/{past.pk}/complete/", {"completion_notes": "Todo bien"}, format="json", **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "realizada")
        self.assertTrue(response.json()["can_evaluate"])

    def test_cancel_requires_reason_and_company_only_before_start(self):
        upcoming = make_visit(site=self.site, scheduled_at=at(self.tuesday, 9))
        self.login(self.member.email)
        headers = self.csrf()
        response = self.client.post(f"/api/v1/visits/{upcoming.pk}/cancel/", {"cancellation_reason": ""}, format="json", **headers)
        self.assertEqual(response.status_code, 400)
        response = self.client.post(f"/api/v1/visits/{upcoming.pk}/cancel/", {"cancellation_reason": "Cambio de planes"}, format="json", **headers)
        self.assertEqual(response.json()["status"], "cancelada")
        started = make_visit(site=self.site, scheduled_at=timezone.now() - timedelta(minutes=30))
        self.assertEqual(self.client.post(f"/api/v1/visits/{started.pk}/cancel/", {"cancellation_reason": "x"}, format="json", **headers).status_code, 404)

    def test_reschedule_and_foreign_visit_is_not_found(self):
        visit = make_visit(site=self.site, scheduled_at=at(self.tuesday, 9))
        foreign = make_visit(site=self.foreign_site, scheduled_at=at(self.tuesday, 15))
        self.login(self.member.email)
        headers = self.csrf()
        response = self.client.put(f"/api/v1/visits/{visit.pk}/", self.payload(time="11:00"), format="json", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(timezone.localtime(Visit.objects.get(pk=visit.pk).scheduled_at).hour, 11)
        self.assertEqual(self.client.get(f"/api/v1/visits/{foreign.pk}/").status_code, 404)

    def test_company_without_sites_gets_the_reason(self):
        lonely = make_user(role=Role.COMPANY, company=make_company(name="Sin sedes"))
        self.login(lonely.email)
        response = self.client.post("/api/v1/visits/", self.payload(), format="json", **self.csrf())
        self.assertEqual(response.status_code, 403)
        self.assertIn("sedes", response.json()["error"]["message"])
