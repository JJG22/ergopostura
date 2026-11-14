from datetime import date, datetime

from django.test import SimpleTestCase
from django.utils import timezone

from apps.companies.models import Company, Site
from apps.visits import agenda
from apps.visits.models import Visit



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




