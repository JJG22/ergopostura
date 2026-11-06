from datetime import date, datetime, timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.core.tests.factories import make_area, make_company, make_position, make_site, make_user
from apps.visits import agenda
from apps.visits.models import Visit

HTMX = {"HTTP_HX_REQUEST": "true"}


def local(day: date, hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime(day.year, day.month, day.day, hour, minute))


def fake_visit(pk, when, company_id=1):
    company = SimpleNamespace(pk=company_id)
    position = SimpleNamespace(area=SimpleNamespace(site=SimpleNamespace(company_id=company_id, company=company)))
    return SimpleNamespace(pk=pk, scheduled_at=when, position=position)


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

    def week(self, visits, now=None):
        period = agenda.build_period(agenda.WEEK, self.today, self.today)
        return agenda.place(period, visits, now)

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

    def test_position_follows_the_hour(self):
        period = self.week([fake_visit(1, local(date(2026, 11, 5), 9, 30))])
        self.assertEqual(period.days[3].events[0].top, int(2.5 * agenda.HOUR_HEIGHT))

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

    def test_month_shows_three_chips_and_counts_the_rest(self):
        period = agenda.build_period(agenda.MONTH, self.today, self.today)
        agenda.place(period, [fake_visit(pk, local(date(2026, 11, 10), 8 + pk)) for pk in range(5)])
        day = next(day for day in period.days if day.date == date(2026, 11, 10))
        self.assertEqual((len(day.visible_events), day.hidden_count), (3, 2))

    def test_each_company_keeps_its_color(self):
        self.assertEqual(agenda.color_of(9), agenda.color_of(9))
        self.assertNotEqual(agenda.color_of(1), agenda.color_of(2))


class CalendarViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(name="Mi empresa")
        cls.position = make_position(make_area(make_site(cls.company)))
        cls.foreign = make_position(make_area(make_site(make_company(name="Ajena")), name="Otra"))
        cls.when = timezone.localtime(timezone.now() + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
        cls.visit = Visit.objects.create(position=cls.position, scheduled_at=cls.when)
        cls.foreign_visit = Visit.objects.create(position=cls.foreign, scheduled_at=cls.when)

    def get(self, **params):
        return self.client.get(reverse("visits:list"), params)

    def test_month_shows_visits_of_the_period(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        response = self.get(fecha=self.when.date().isoformat())
        self.assertEqual(set(response.context["visits"]), {self.visit, self.foreign_visit})
        self.assertContains(response, reverse("visits:detail", args=[self.visit.pk]))

    def test_company_user_only_sees_its_visits_and_legend(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        response = self.get(fecha=self.when.date().isoformat(), vista="semana")
        self.assertEqual(response.context["visits"], [self.visit])
        self.assertNotContains(response, "Ajena")

    def test_week_view_and_unknown_view(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertEqual(self.get(vista="semana").context["period"].view, agenda.WEEK)
        self.assertEqual(self.get(vista="año", fecha="no-es-fecha").context["period"].view, agenda.MONTH)

    def test_managers_get_create_shortcuts_and_readers_do_not(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertContains(self.get(vista="semana"), "cal-slot")
        self.client.force_login(make_user(role=Role.EVALUATOR))
        self.assertNotContains(self.get(vista="semana"), "cal-slot")
        self.assertNotContains(self.get(), "cal-add")

    def test_query_count_does_not_grow_with_visits(self):
        for days in range(3, 8):
            Visit.objects.create(position=self.position, scheduled_at=self.when + timedelta(days=days))
        self.client.force_login(make_user(role=Role.ADMIN))
        # sesion, usuario, visitas del periodo y proximas visitas
        with self.assertNumQueries(4):
            self.get()

    def test_detail_opens_as_modal_or_page(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        url = reverse("visits:detail", args=[self.visit.pk])
        self.assertContains(self.client.get(url, **HTMX), 'class="overlay"')
        page = self.client.get(url)
        self.assertContains(page, "Volver al calendario")
        self.assertContains(page, reverse("visits:update", args=[self.visit.pk]))


class CreateFromCalendarTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user(role=Role.ADMIN))

    def initial(self, **params):
        return self.client.get(reverse("visits:create"), params).context["form"].initial

    def test_future_date_and_hour_are_prefilled(self):
        day = timezone.localdate() + timedelta(days=3)
        initial = self.initial(fecha=day.isoformat(), hora="14")
        self.assertEqual(initial["date"], day)
        self.assertEqual(initial["time"].hour, 14)

    def test_past_or_invalid_values_are_ignored(self):
        initial = self.initial(fecha=(timezone.localdate() - timedelta(days=1)).isoformat(), hora="99")
        self.assertNotIn("date", initial)
        self.assertNotIn("time", initial)
        self.assertNotIn("time", self.initial(hora="x"))
