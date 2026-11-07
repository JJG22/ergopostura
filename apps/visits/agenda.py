"""Calendario de visitas por mes o por semana, sin dependencias de la base de datos.

Recibe las visitas ya consultadas y calcula como ubicarlas: en que celda del mes cae cada
una, y en la semana a que altura y con que ancho, cuando dos coinciden en la misma hora.
Las semanas empiezan el lunes, como en el calendario colombiano.
"""
import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.utils import timezone

MONTH = "mes"
WEEK = "semana"
VIEWS = (MONTH, WEEK)

MONTH_NAMES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
WEEKDAY_NAMES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

HOUR_HEIGHT = 48
DEFAULT_FIRST_HOUR = 7
DEFAULT_LAST_HOUR = 19
MAX_CHIPS_PER_DAY = 3
PALETTE_SIZE = 8


def parse_date(value, default: date) -> date:
    try:
        return date.fromisoformat(value) if value else default
    except (TypeError, ValueError):
        return default


def hour_label(hour: int) -> str:
    suffix = "a. m." if hour < 12 else "p. m."
    return f"{hour % 12 or 12} {suffix}"


def color_of(company_id: int) -> int:
    """Cada empresa conserva su color en todas las vistas."""
    return company_id % PALETTE_SIZE


@dataclass
class Event:
    """Una visita en el calendario, o un horario ocupado por otra empresa (visit=None)."""

    visit: object
    start: datetime
    minutes: int
    color: int
    level: object = None
    top: int = 0
    height: int = HOUR_HEIGHT
    column: int = 0
    columns: int = 1

    @property
    def busy(self) -> bool:
        return self.visit is None

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.minutes)

    @property
    def cancelled(self) -> bool:
        return self.visit is not None and self.visit.status == "cancelada"

    @property
    def left_percent(self) -> float:
        return round(100 * self.column / self.columns, 2)

    @property
    def width_percent(self) -> float:
        return round(100 / self.columns, 2)


@dataclass
class Day:
    date: date
    today: date
    in_period: bool = True
    events: list[Event] = field(default_factory=list)
    # Horas de la semana en que aun se puede registrar una visita, con su fila en la grilla.
    open_slots: list[tuple[int, int]] = field(default_factory=list)

    @property
    def is_today(self) -> bool:
        return self.date == self.today

    @property
    def is_past(self) -> bool:
        return self.date < self.today

    @property
    def visible_events(self) -> list[Event]:
        return self.events[:MAX_CHIPS_PER_DAY]

    @property
    def hidden_count(self) -> int:
        return max(0, len(self.events) - MAX_CHIPS_PER_DAY)

    @property
    def weekday_name(self) -> str:
        return WEEKDAY_NAMES[self.date.weekday()]


@dataclass
class Period:
    view: str
    anchor: date
    start: date
    end: date  # exclusivo
    title: str
    previous: date
    next: date
    today: date
    days: list[Day]
    first_hour: int = DEFAULT_FIRST_HOUR
    last_hour: int = DEFAULT_LAST_HOUR
    now_top: int | None = None

    @property
    def weeks(self) -> list[list[Day]]:
        return [self.days[index:index + 7] for index in range(0, len(self.days), 7)]

    @property
    def weekday_headers(self) -> tuple[str, ...]:
        return WEEKDAY_NAMES

    @property
    def hour_rows(self) -> list[tuple[int, str]]:
        return [(row, hour_label(hour)) for row, hour in enumerate(range(self.first_hour, self.last_hour))]

    @property
    def grid_height(self) -> int:
        return (self.last_hour - self.first_hour) * HOUR_HEIGHT

    @property
    def contains_today(self) -> bool:
        return self.start <= self.today < self.end

    def bounds(self) -> tuple[datetime, datetime]:
        """Inicio y fin del periodo en la zona horaria del sistema, para consultar."""
        zone = timezone.get_current_timezone()
        return (
            datetime.combine(self.start, time.min, tzinfo=zone),
            datetime.combine(self.end, time.min, tzinfo=zone),
        )


def _month_period(anchor: date, today: date) -> Period:
    first = anchor.replace(day=1)
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month)
    previous = (first - timedelta(days=1)).replace(day=1)
    following = (first + timedelta(days=32)).replace(day=1)
    days = [Day(day, today, in_period=day.month == first.month) for week in weeks for day in week]
    return Period(
        view=MONTH,
        anchor=first,
        start=weeks[0][0],
        end=weeks[-1][-1] + timedelta(days=1),
        title=f"{MONTH_NAMES[first.month - 1]} de {first.year}",
        previous=previous,
        next=following,
        today=today,
        days=days,
    )


def _week_title(start: date, last: date) -> str:
    if start.month == last.month:
        return f"{start.day} – {last.day} de {MONTH_NAMES[start.month - 1]} de {start.year}"
    if start.year == last.year:
        return (
            f"{start.day} de {MONTH_NAMES[start.month - 1]} – "
            f"{last.day} de {MONTH_NAMES[last.month - 1]} de {start.year}"
        )
    return (
        f"{start.day} de {MONTH_NAMES[start.month - 1]} de {start.year} – "
        f"{last.day} de {MONTH_NAMES[last.month - 1]} de {last.year}"
    )


def _week_period(anchor: date, today: date) -> Period:
    start = anchor - timedelta(days=anchor.weekday())
    days = [Day(start + timedelta(days=offset), today) for offset in range(7)]
    return Period(
        view=WEEK,
        anchor=start,
        start=start,
        end=start + timedelta(days=7),
        title=_week_title(start, start + timedelta(days=6)),
        previous=start - timedelta(days=7),
        next=start + timedelta(days=7),
        today=today,
        days=days,
    )


def build_period(view: str, anchor: date, today: date) -> Period:
    return _week_period(anchor, today) if view == WEEK else _month_period(anchor, today)


def place(period: Period, visits, now: datetime | None = None, busy=()) -> Period:
    """Reparte las visitas en los dias del periodo y calcula su posicion en la semana.

    busy son pares (inicio, minutos) de visitas que el usuario no puede ver: se dibujan
    como «Ocupado», sin empresa ni enlace.
    """
    by_date = {day.date: day for day in period.days}
    moment = now or timezone.now()
    for visit in visits:
        start = timezone.localtime(visit.scheduled_at)
        day = by_date.get(start.date())
        if day is not None:
            day.events.append(
                Event(visit, start, visit.duration_minutes, color_of(visit.site.company_id), visit.level_at(moment))
            )
    for scheduled_at, minutes in busy:
        start = timezone.localtime(scheduled_at)
        day = by_date.get(start.date())
        if day is not None:
            day.events.append(Event(None, start, minutes, -1))
    for day in period.days:
        day.events.sort(key=lambda event: (event.start, event.busy, event.visit.pk if event.visit else 0))

    if period.view == WEEK:
        _fit_hours(period)
        for day in period.days:
            _assign_columns(day.events)
            for event in day.events:
                event.top = _offset(period, event.start)
                event.height = max(22, round(min(event.minutes, _minutes_left(period, event.start)) * HOUR_HEIGHT / 60) - 2)
        if now is not None:
            now = timezone.localtime(now)
            _open_slots(period, now)
            if period.contains_today and period.first_hour <= now.hour < period.last_hour:
                period.now_top = _offset(period, now)
    return period


def _open_slots(period: Period, now: datetime) -> None:
    """Hoy solo se ofrecen las horas que no han empezado; los dias pasados, ninguna."""
    for day in period.days:
        for row, hour in enumerate(range(period.first_hour, period.last_hour)):
            if day.date > now.date() or (day.date == now.date() and hour > now.hour):
                day.open_slots.append((hour, row))


def _minutes_left(period: Period, moment: datetime) -> int:
    return period.last_hour * 60 - (moment.hour * 60 + moment.minute)


def _offset(period: Period, moment: datetime) -> int:
    minutes = (moment.hour - period.first_hour) * 60 + moment.minute
    return round(minutes * HOUR_HEIGHT / 60)


def _fit_hours(period: Period) -> None:
    """Amplia el horario visible si alguna visita cae antes o despues del habitual."""
    starts = [event.start for day in period.days for event in day.events]
    if not starts:
        return
    period.first_hour = min(period.first_hour, min(start.hour for start in starts))
    # Minuto del dia en que termina el bloque mas tardio; una visita a las 23:30 llega a medianoche.
    events = [event for day in period.days for event in day.events]
    latest_end = max(min(24 * 60, event.start.hour * 60 + event.start.minute + event.minutes) for event in events)
    period.last_hour = max(period.last_hour, -(-latest_end // 60))


def _assign_columns(events: list[Event]) -> None:
    """Las visitas que se cruzan se dibujan lado a lado, como en un calendario de escritorio."""
    cluster: list[Event] = []
    cluster_end = None
    for event in events:
        if cluster and event.start >= cluster_end:
            _close_cluster(cluster)
            cluster = []
        cluster_end = max(cluster_end, event.end) if cluster else event.end
        cluster.append(event)
    if cluster:
        _close_cluster(cluster)


def _close_cluster(cluster: list[Event]) -> None:
    column_ends: list[datetime] = []
    for event in cluster:
        for index, end in enumerate(column_ends):
            if event.start >= end:
                event.column = index
                column_ends[index] = event.end
                break
        else:
            event.column = len(column_ends)
            column_ends.append(event.end)
    for event in cluster:
        event.columns = len(column_ends)
