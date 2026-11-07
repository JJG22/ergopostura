from datetime import date, datetime, timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.companies.models import Company, Site
from apps.core.tests.factories import at, make_company, make_contract, make_site, make_user, make_visit
from apps.visits import agenda
from apps.visits.models import Visit

HTMX = {"HTTP_HX_REQUEST": "true"}


def local(day: date, hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime(day.year, day.month, day.day, hour, minute))


def fake_visit(pk, when, company_id=1, minutes=60, status=Visit.Status.SCHEDULED):
    """Visita sin guardar: el calendario no necesita la base de datos."""
    company = Company(pk=company_id, name=f"Empresa {company_id}")
    return Visit(pk=pk, site=Site(pk=company_id, company=company, name="Sede"), scheduled_at=when,
                 duration_minutes=minutes, status=status)


class PeriodTests(SimpleTestCase):
    today = date(2026, 11, 6)

    def test_month_starts_on_monday_and_covers_whole_weeks(self):
        period = agenda.build_period(agenda.MONTH, self.today, self.today)
        self.assertEqual(period.start, date(2026, 10, 26))
        self.assertEqual(period.start.weekday(), 0)
        self.assertEqual(len(period.days) % 7, 0)
        self.assertEqual(period.title, "noviembre de 2026")
        self.assertEqual((period.previous, period.next), (date(2026, 10, 1), date(2026, 12, 1)))
        self.assertFalse(period.days[0].in_period)

    def test_december_moves_to_january_of_next_year(self):
        period = agenda.build_period(agenda.MONTH, date(2026, 12, 31), self.today)
        self.assertEqual(period.next, date(2027, 1, 1))

    def test_week_title_across_months_and_years(self):
        self.assertEqual(agenda.build_period(agenda.WEEK, self.today, self.today).title, "2 – 8 de noviembre de 2026")
        crossing = agenda.build_period(agenda.WEEK, date(2026, 12, 31), self.today)
        self.assertEqual(crossing.title, "28 de diciembre de 2026 – 3 de enero de 2027")

    def test_garbage_date_falls_back(self):
        self.assertEqual(agenda.parse_date("2026-13-40", self.today), self.today)
        self.assertEqual(agenda.parse_date(None, self.today), self.today)

    def test_hour_labels(self):
        self.assertEqual([agenda.hour_label(h) for h in (0, 9, 12, 15)], ["12 a. m.", "9 a. m.", "12 p. m.", "3 p. m."])


class PlacementTests(SimpleTestCase):
    today = date(2026, 11, 6)

    def week(self, visits, now=None, busy=()):
        period = agenda.build_period(agenda.WEEK, self.today, self.today)
        return agenda.place(period, visits, now or local(self.today, 6), busy)

    def test_visits_outside_the_period_are_ignored(self):
        period = self.week([fake_visit(1, local(date(2026, 12, 1), 9))])
        self.assertFalse(any(day.events for day in period.days))

    def test_overlapping_visits_go_side_by_side(self):
        day = date(2026, 11, 5)
        period = self.week([fake_visit(1, local(day, 9)), fake_visit(2, local(day, 9, 30)), fake_visit(3, local(day, 11))])
        first, second, alone = period.days[3].events
        self.assertEqual((first.column, second.column, first.columns), (0, 1, 2))
        self.assertEqual((alone.column, alone.columns), (0, 1))
        self.assertEqual(second.left_percent, 50.0)

    def test_position_and_height_follow_the_hour_and_duration(self):
        period = self.week([fake_visit(1, local(date(2026, 11, 5), 9, 30), minutes=120)])
        event = period.days[3].events[0]
        self.assertEqual(event.top, int(2.5 * agenda.HOUR_HEIGHT))
        self.assertEqual(event.height, 2 * agenda.HOUR_HEIGHT - 2)

    def test_hours_widen_for_early_or_late_visits(self):
        period = self.week([fake_visit(1, local(date(2026, 11, 5), 5)), fake_visit(2, local(date(2026, 11, 5), 23, 30))])
        self.assertEqual((period.first_hour, period.last_hour), (5, 24))

    def test_only_future_slots_are_open(self):
        period = self.week([], now=local(self.today, 10, 15))
        by_date = {day.date: day for day in period.days}
        self.assertEqual(by_date[date(2026, 11, 5)].open_slots, [])
        self.assertEqual(by_date[self.today].open_slots[0][0], 11)
        self.assertEqual(len(by_date[date(2026, 11, 7)].open_slots), agenda.DEFAULT_LAST_HOUR - agenda.DEFAULT_FIRST_HOUR)
        self.assertIsNotNone(period.now_top)

    def test_busy_slots_carry_no_visit_data(self):
        period = self.week([], busy=[(local(date(2026, 11, 5), 10), 120)])
        event = period.days[3].events[0]
        self.assertTrue(event.busy)
        self.assertIsNone(event.visit)
        self.assertEqual(event.minutes, 120)

    def test_each_event_carries_its_level(self):
        now = local(self.today, 12)
        period = self.week([
            fake_visit(1, local(date(2026, 11, 5), 9)),
            fake_visit(2, local(date(2026, 11, 7), 9)),
            fake_visit(3, local(date(2026, 11, 4), 9), status=Visit.Status.COMPLETED),
        ], now=now)
        levels = {event.visit.pk: event.level.key for day in period.days for event in day.events}
        self.assertEqual(levels, {1: "por_cerrar", 2: "cercana", 3: "realizada"})

    def test_month_shows_three_chips_and_counts_the_rest(self):
        period = agenda.build_period(agenda.MONTH, self.today, self.today)
        agenda.place(period, [fake_visit(pk, local(date(2026, 11, 10), 8 + pk)) for pk in range(1, 6)])
        day = next(day for day in period.days if day.date == date(2026, 11, 10))
        self.assertEqual((len(day.visible_events), day.hidden_count), (3, 2))

    def test_each_company_keeps_its_color(self):
        self.assertEqual(agenda.color_of(9), agenda.color_of(9))
        self.assertNotEqual(agenda.color_of(1), agenda.color_of(2))


class LevelTests(SimpleTestCase):
    def test_levels_follow_the_time_left(self):
        now = local(date(2026, 11, 6), 10)
        cases = {
            "programada": local(date(2026, 11, 20), 9),
            "cercana": local(date(2026, 11, 8), 9),
            "hoy": local(date(2026, 11, 6), 15),
            "en_curso": local(date(2026, 11, 6), 9, 30),
            "por_cerrar": local(date(2026, 11, 5), 9),
        }
        for expected, when in cases.items():
            self.assertEqual(fake_visit(1, when).level_at(now).key, expected, expected)

    def test_recorded_states_win_over_the_clock(self):
        now = local(date(2026, 11, 6), 10)
        past = local(date(2026, 11, 5), 9)
        self.assertEqual(fake_visit(1, past, status=Visit.Status.COMPLETED).level_at(now).key, "realizada")
        self.assertEqual(fake_visit(1, past, status=Visit.Status.CANCELLED).level_at(now).key, "cancelada")


class CalendarViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(name="Mi empresa")
        cls.site = make_site(cls.company)
        make_contract(cls.company)
        cls.foreign = make_company(name="Ajena S.A.")
        cls.foreign_site = make_site(cls.foreign, name="Sede ajena")
        cls.day = timezone.localdate() + timedelta(days=2)
        cls.visit = make_visit(cls.site, at(cls.day, 9))
        cls.foreign_visit = make_visit(cls.foreign_site, at(cls.day, 14))

    def get(self, **params):
        return self.client.get(reverse("visits:list"), params)

    def test_engineer_sees_every_company_and_cannot_schedule(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        response = self.get(fecha=self.day.isoformat())
        self.assertEqual(set(response.context["visits"]), {self.visit, self.foreign_visit})
        self.assertContains(response, "Ajena S.A.")
        self.assertNotContains(response, "Agendar visita")
        self.assertNotContains(self.get(vista="semana", fecha=self.day.isoformat()), "cal-slot")

    def test_company_sees_its_visits_and_others_only_as_busy(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        response = self.get(fecha=self.day.isoformat(), vista="semana")
        self.assertEqual(response.context["visits"], [self.visit])
        self.assertContains(response, "Ocupado")
        self.assertNotContains(response, "Ajena")
        self.assertNotContains(response, reverse("visits:detail", args=[self.foreign_visit.pk]))
        self.assertContains(response, "cal-slot")
        self.assertContains(response, "Agendar visita")

    def test_company_without_sites_is_told_why_it_cannot_schedule(self):
        empty = make_company(name="Sin sedes")
        self.client.force_login(make_user(role=Role.COMPANY, company=empty))
        response = self.get()
        self.assertFalse(response.context["can_schedule"])
        self.assertContains(response, "aún no ha registrado las sedes")

    def test_support_has_no_calendar(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertEqual(self.get().status_code, 403)

    def test_week_view_and_unknown_view(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        self.assertEqual(self.get(vista="semana").context["period"].view, agenda.WEEK)
        self.assertEqual(self.get(vista="año", fecha="no-es-fecha").context["period"].view, agenda.MONTH)

    def test_query_count_does_not_grow_with_visits(self):
        for days in range(3, 8):
            make_visit(self.site, at(self.day + timedelta(days=days), 9))
        self.client.force_login(make_user(role=Role.ENGINEER))
        with self.assertNumQueries(5):
            self.get()

    def test_detail_opens_as_modal_or_page(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        url = reverse("visits:detail", args=[self.visit.pk])
        self.assertContains(self.client.get(url, **HTMX), 'class="overlay"')
        page = self.client.get(url)
        self.assertContains(page, "Volver al calendario")
        self.assertContains(page, reverse("visits:update", args=[self.visit.pk]))


class CreateFromCalendarTests(TestCase):
    def setUp(self):
        company = make_company()
        make_site(company)
        make_contract(company)
        self.client.force_login(make_user(role=Role.COMPANY, company=company))

    def initial(self, **params):
        return self.client.get(reverse("visits:create"), params).context["form"].initial

    def test_future_date_and_hour_are_prefilled(self):
        day = timezone.localdate() + timedelta(days=3)
        initial = self.initial(fecha=day.isoformat(), hora="14")
        self.assertEqual(initial["date"], day)
        self.assertEqual(initial["time"].hour, 14)

    def test_past_invalid_or_after_hours_values_are_ignored(self):
        initial = self.initial(fecha=(timezone.localdate() - timedelta(days=1)).isoformat(), hora="99")
        self.assertNotIn("date", initial)
        self.assertNotIn("time", initial)
        self.assertNotIn("time", self.initial(hora="x"))
        self.assertNotIn("time", self.initial(hora="20"))
