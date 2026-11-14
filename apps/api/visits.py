"""Visitas: calendario, agenda y acciones (agendar, reprogramar, registrar, cancelar).

El calendario se arma con apps.visits.agenda, igual que la pantalla actual: el servidor
decide en qué día y a qué altura va cada visita, y el cliente solo lo dibuja. Los horarios
de otras empresas viajan como «Ocupado», sin ningún dato de ellas.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import Capability, has_capability
from apps.contracts.services import current_contract
from apps.evaluations.selectors import visible_evaluations
from apps.visits import agenda, rules, selectors
from apps.visits.forms import CancelVisitForm, CompleteVisitForm, VisitForm
from apps.visits.models import LEVELS, Visit

from . import presenters
from .common import choices, invalid, paginate
from .errors import error_response
from .permissions import HasCapability

VIEW = (Capability.VISIT_VIEW_ALL, Capability.VISIT_VIEW_OWN)
UPCOMING_LIMIT = 6
SHOWN_LEVELS = ("programada", "cercana", "hoy", "en_curso", "por_cerrar", "realizada")


def local(value):
    return presenters.iso(timezone.localtime(value)) if value else None


def visit_row(visit, now) -> dict:
    return {
        "id": visit.pk,
        "company": {"id": visit.company.pk, "name": visit.company.name},
        "site": visit.site.name,
        "municipality": visit.site.municipality.name,
        "starts_at": local(visit.scheduled_at),
        "ends_at": local(visit.ends_at),
        "duration_minutes": visit.duration_minutes,
        "contact_name": visit.contact_name,
        "status": visit.status,
        "level": presenters.level_data(visit.level_at(now)),
        "color": agenda.color_of(visit.company.pk),
    }


def event_data(event, shows_company: bool) -> dict:
    data = {
        "busy": event.busy,
        "starts_at": local(event.start),
        "ends_at": local(event.end),
        "top": event.top,
        "height": event.height,
        "left": event.left_percent,
        "width": event.width_percent,
    }
    if not event.busy:
        visit = event.visit
        data.update(
            id=visit.pk,
            title=visit.company.name if shows_company else visit.site.name,
            company=visit.company.name,
            color=event.color,
            level=presenters.level_data(event.level),
        )
    return data


def schedule_info(user) -> dict:
    schedules = has_capability(user, Capability.VISIT_SCHEDULE)
    allowed = rules.can_schedule(user)
    contract = current_contract(user.company) if user.company_id else None
    return {
        "can_schedule": allowed,
        "schedules": schedules,
        "blocker": rules.schedule_blocker(user),
        "contract": {
            "code": contract.display_code,
            "start_date": presenters.iso(contract.start_date),
            "end_date": presenters.iso(contract.end_date),
        } if contract else None,
    }


class CalendarView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = VIEW

    def get(self, request):
        user = request.user
        now = timezone.now()
        today = timezone.localdate(now)
        view = request.query_params.get("view")
        view = view if view in agenda.VIEWS else agenda.MONTH
        period = agenda.build_period(view, agenda.parse_date(request.query_params.get("date"), today), today)
        bounds = period.bounds()
        visits = list(selectors.visits_between(user, *bounds))
        agenda.place(period, visits, now, busy=selectors.busy_between(user, *bounds))
        shows_company = has_capability(user, Capability.VISIT_VIEW_ALL)
        companies = {visit.company.pk: visit.company.name for visit in visits}
        upcoming = list(selectors.upcoming_visits(user)[:UPCOMING_LIMIT])
        to_close = selectors.visits_to_close(user) if has_capability(user, Capability.VISIT_ATTEND) else []

        return Response({
            "view": period.view,
            "title": period.title[:1].upper() + period.title[1:],
            "anchor": presenters.iso(period.anchor),
            "previous": presenters.iso(period.previous),
            "next": presenters.iso(period.next),
            "today": presenters.iso(today),
            "contains_today": period.contains_today,
            "first_hour": period.first_hour,
            "last_hour": period.last_hour,
            "hour_height": agenda.HOUR_HEIGHT,
            "grid_height": period.grid_height,
            "now_top": period.now_top,
            "hours": [label for _, label in period.hour_rows],
            "days": [
                {
                    "date": presenters.iso(day.date),
                    "in_period": day.in_period,
                    "is_today": day.is_today,
                    "is_past": day.is_past,
                    "weekday": day.weekday_name,
                    "events": [event_data(event, shows_company) for event in day.events],
                    # Horas libres para agendar, dentro del horario de trabajo.
                    "open_hours": [hour for hour, _ in day.open_slots
                                   if rules.WORK_START.hour <= hour < rules.WORK_END.hour and day.date.weekday() != 6],
                }
                for day in period.days
            ],
            "max_chips": agenda.MAX_CHIPS_PER_DAY,
            "shows_company": shows_company,
            "legend": [{"name": name, "color": agenda.color_of(pk)} for pk, name in sorted(companies.items(), key=lambda i: i[1])],
            "levels": [presenters.level_data(LEVELS[key]) for key in SHOWN_LEVELS],
            "upcoming": [visit_row(v, now) for v in upcoming],
            "to_close": [visit_row(v, now) for v in to_close],
            **schedule_info(user),
        })


class AgendaView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = VIEW
    TABS = ("proximas", "por_cerrar", "historial")

    def get(self, request):
        user = request.user
        tab = request.query_params.get("tab", "proximas")
        attends = has_capability(user, Capability.VISIT_ATTEND)
        if tab not in self.TABS or (tab == "por_cerrar" and not attends):
            tab = "proximas"
        visits = {
            "historial": lambda: selectors.past_visits(user),
            "por_cerrar": lambda: selectors.visits_to_close(user),
            "proximas": lambda: selectors.upcoming_visits(user),
        }[tab]()
        now = timezone.now()
        data = paginate(request, visits, lambda v: visit_row(v, now), per_page=15)
        data.update(tab=tab, attends=attends, **schedule_info(user))
        return Response(data)


def visit_detail(visit, user) -> dict:
    now = timezone.now()
    attends = has_capability(user, Capability.VISIT_ATTEND)
    schedules = has_capability(user, Capability.VISIT_SCHEDULE)
    person = lambda account: str(account) if account else None  # noqa: E731
    evaluations = visible_evaluations(user).filter(visit=visit).order_by("pk") if visit.is_completed else []
    return {
        **visit_row(visit, now),
        "site": visit.site.name,
        "site_id": visit.site_id,
        "address": visit.site.address,
        "duration_label": visit.get_duration_minutes_display(),
        "purpose": visit.purpose,
        "contact_phone": visit.contact_phone,
        "requested_by": person(visit.requested_by),
        "created_at": local(visit.created_at),
        "completed_by": person(visit.completed_by),
        "completed_at": local(visit.completed_at),
        "completion_notes": visit.completion_notes,
        "cancelled_by": person(visit.cancelled_by),
        "cancelled_at": local(visit.cancelled_at),
        "cancellation_reason": visit.cancellation_reason,
        "evaluations": [{"id": e.pk, "code": e.code, "url": f"/evaluaciones/{e.pk}"} for e in evaluations],
        "can_reschedule": schedules and visit.is_scheduled and visit.scheduled_at > now + rules.MIN_NOTICE,
        "can_cancel": visit.is_scheduled and ((schedules and visit.scheduled_at > now) or attends),
        "can_complete": attends and visit.is_scheduled and visit.scheduled_at <= now,
        "can_evaluate": visit.is_completed and has_capability(user, Capability.EVALUATION_MANAGE),
        "cancel_by_company": not attends,
        "new_evaluation_url": f"/evaluaciones?visita={visit.pk}",
    }


def save_visit(form) -> Response | Visit:
    """Dos empresas no pueden tomar el mismo horario: se revisa otra vez con la agenda bloqueada."""
    if not form.is_valid():
        return invalid(form)
    with transaction.atomic():
        rules.lock_schedule()
        if rules.overlapping_visit(form.instance.scheduled_at, form.cleaned_data["duration_minutes"], form.instance.pk):
            form.add_error(None, "Otra empresa acaba de tomar ese horario. Elige otra hora.")
            return invalid(form)
        return form.save()


def blocked(user) -> Response | None:
    if not rules.can_schedule(user):
        return error_response("permission_denied", rules.schedule_blocker(user), status.HTTP_403_FORBIDDEN)
    return None


class VisitOptionsView(APIView):
    """Lo que necesita el formulario de agendar: sedes de la empresa, duraciones y horario."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.VISIT_SCHEDULE,)

    def get(self, request):
        company = request.user.company
        sites = company.sites.select_related("municipality").order_by("name") if company else []
        return Response({
            "sites": [{"value": str(s.pk), "label": f"{s.name} · {s.municipality.name}"} for s in sites],
            "durations": choices(Visit.DURATION_CHOICES),
            "work_start": rules.WORK_START.strftime("%H:%M"),
            "work_end": rules.WORK_END.strftime("%H:%M"),
            **schedule_info(request.user),
        })


class VisitListView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.VISIT_SCHEDULE,)

    def post(self, request):
        if (response := blocked(request.user)) is not None:
            return response
        result = save_visit(VisitForm(data=request.data, user=request.user))
        if isinstance(result, Response):
            return result
        return Response(visit_row(result, timezone.now()), status=status.HTTP_201_CREATED)


class VisitDetailView(APIView):
    permission_classes = [IsAuthenticated, HasCapability]

    def get_permissions(self):
        self.required_capabilities = VIEW if self.request.method == "GET" else (Capability.VISIT_SCHEDULE,)
        return super().get_permissions()

    def get(self, request, pk):
        visit = get_object_or_404(
            selectors.visible_visits(request.user).select_related("requested_by", "completed_by", "cancelled_by"), pk=pk
        )
        return Response(visit_detail(visit, request.user))

    def put(self, request, pk):
        """Reprogramar: solo una visita programada, con al menos una hora de anticipación."""
        if (response := blocked(request.user)) is not None:
            return response
        limit = timezone.now() + rules.MIN_NOTICE
        visit = get_object_or_404(
            selectors.visible_visits(request.user).filter(status=Visit.Status.SCHEDULED, scheduled_at__gt=limit), pk=pk
        )
        result = save_visit(VisitForm(data=request.data, instance=visit, user=request.user))
        if isinstance(result, Response):
            return result
        return Response(visit_row(result, timezone.now()))


class VisitCompleteView(APIView):
    """El ingeniero registra que la visita se hizo; desde ahí puede evaluar."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.VISIT_ATTEND,)

    def post(self, request, pk):
        visit = get_object_or_404(
            selectors.visible_visits(request.user).filter(status=Visit.Status.SCHEDULED, scheduled_at__lte=timezone.now()), pk=pk
        )
        form = CompleteVisitForm(data=request.data, instance=visit)
        if not form.is_valid():
            return invalid(form)
        visit.status = Visit.Status.COMPLETED
        visit.completed_at = timezone.now()
        visit.completed_by = request.user
        form.save()
        return Response(visit_detail(visit, request.user))


class VisitCancelView(APIView):
    """La empresa cancela antes de que empiece; el ingeniero, también una que no se hizo."""

    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = (Capability.VISIT_SCHEDULE, Capability.VISIT_ATTEND)

    def post(self, request, pk):
        visits = selectors.visible_visits(request.user).filter(status=Visit.Status.SCHEDULED)
        if not has_capability(request.user, Capability.VISIT_ATTEND):
            visits = visits.filter(scheduled_at__gt=timezone.now())
        visit = get_object_or_404(visits, pk=pk)
        form = CancelVisitForm(data=request.data, instance=visit)
        if not form.is_valid():
            return invalid(form)
        visit.status = Visit.Status.CANCELLED
        visit.cancelled_at = timezone.now()
        visit.cancelled_by = request.user
        form.save()
        return Response(visit_detail(visit, request.user))
