from datetime import time
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability, has_capability
from apps.contracts.services import current_contract
from apps.core.views import ModalFormMixin, full_reload_url, is_htmx
from apps.evaluations.selectors import visible_evaluations

from . import agenda, rules, selectors
from .forms import CancelVisitForm, CompleteVisitForm, VisitForm
from .models import LEVELS, Visit

VIEW_CAPABILITIES = (Capability.VISIT_VIEW_ALL, Capability.VISIT_VIEW_OWN)
UPCOMING_LIMIT = 6


def calendar_url(view: str = agenda.MONTH, day=None) -> str:
    """Calendario en la vista y la fecha indicadas; sin datos, el mes actual."""
    params = {}
    if view != agenda.MONTH:
        params["vista"] = view
    if day is not None:
        params["fecha"] = day.isoformat()
    url = reverse("visits:list")
    return f"{url}?{urlencode(params)}" if params else url


def requested_view(request) -> str:
    view = request.GET.get("vista")
    return view if view in agenda.VIEWS else agenda.MONTH


def visit_calendar_url(visit, view=agenda.MONTH) -> str:
    return calendar_url(view, timezone.localtime(visit.scheduled_at).date())


def can_schedule(user) -> bool:
    """La empresa agenda solo si esta activa y tiene sedes registradas."""
    company = getattr(user, "company", None)
    return (
        has_capability(user, Capability.VISIT_SCHEDULE)
        and company is not None
        and company.is_active
        and company.sites.exists()
    )


class VisitCalendarView(CapabilityRequiredMixin, TemplateView):
    """Calendario de visitas por mes o por semana, al estilo de un calendario de escritorio."""

    required_capabilities = VIEW_CAPABILITIES
    template_name = "visits/calendar.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        now = timezone.now()
        today = timezone.localdate(now)
        view = requested_view(self.request)
        period = agenda.build_period(view, agenda.parse_date(self.request.GET.get("fecha"), today), today)
        bounds = period.bounds()
        visits = list(selectors.visits_between(user, *bounds))
        agenda.place(period, visits, now, busy=selectors.busy_between(user, *bounds))

        companies = {visit.company.pk: visit.company for visit in visits}
        legend = [(company, agenda.color_of(pk)) for pk, company in sorted(companies.items(), key=lambda i: i[1].name)]
        upcoming = list(selectors.upcoming_visits(user)[:UPCOMING_LIMIT])
        for visit in upcoming:
            visit.color = agenda.color_of(visit.company.pk)
            visit.current_level = visit.level_at(now)

        schedule = can_schedule(user)
        return super().get_context_data(
            period=period,
            visits=visits,
            legend=legend,
            levels=[LEVELS[key] for key in ("programada", "cercana", "hoy", "en_curso", "por_cerrar", "realizada")],
            upcoming=upcoming,
            to_close=selectors.visits_to_close(user) if has_capability(user, Capability.VISIT_ATTEND) else [],
            can_schedule=schedule,
            schedule_blocker=self._schedule_blocker(user) if not schedule else "",
            contract=current_contract(user.company) if user.company_id else None,
            month_url=calendar_url(agenda.MONTH, period.anchor),
            week_url=calendar_url(agenda.WEEK, period.today if period.contains_today else period.anchor),
            previous_url=calendar_url(view, period.previous),
            next_url=calendar_url(view, period.next),
            today_url=calendar_url(view),
            **kwargs,
        )

    @staticmethod
    def _schedule_blocker(user) -> str:
        if not has_capability(user, Capability.VISIT_SCHEDULE):
            return ""
        if not user.company.is_active:
            return "La empresa está inactiva: no puede agendar visitas."
        return "El ingeniero aún no ha registrado las sedes de la empresa. Cuando lo haga, podrás agendar."


class VisitAgendaView(CapabilityRequiredMixin, ListView):
    """Lista de visitas en orden, para quien prefiere leerlas que verlas en el calendario."""

    required_capabilities = VIEW_CAPABILITIES
    template_name = "visits/agenda.html"
    context_object_name = "visits"
    paginate_by = 15
    TABS = ("proximas", "por_cerrar", "historial")

    @property
    def tab(self) -> str:
        value = self.request.GET.get("ver", "proximas")
        if value == "por_cerrar" and not has_capability(self.request.user, Capability.VISIT_ATTEND):
            return "proximas"
        return value if value in self.TABS else "proximas"

    def get_queryset(self):
        user = self.request.user
        if self.tab == "historial":
            return selectors.past_visits(user)
        if self.tab == "por_cerrar":
            return selectors.visits_to_close(user)
        return selectors.upcoming_visits(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        for visit in context["visits"]:
            visit.current_level = visit.level_at(now)
        context.update(tab=self.tab, can_schedule=can_schedule(self.request.user))
        return context


class VisitDetailView(CapabilityRequiredMixin, DetailView):
    required_capabilities = VIEW_CAPABILITIES
    context_object_name = "visit"

    def get_template_names(self):
        return ["visits/_detail_modal.html" if is_htmx(self.request) else "visits/detail.html"]

    def get_queryset(self):
        return selectors.visible_visits(self.request.user).select_related(
            "requested_by", "completed_by", "cancelled_by"
        )

    def get_context_data(self, **kwargs):
        visit = self.object
        user = self.request.user
        now = timezone.now()
        attends = has_capability(user, Capability.VISIT_ATTEND)
        schedules = has_capability(user, Capability.VISIT_SCHEDULE)
        return super().get_context_data(
            level=visit.level_at(now),
            color=agenda.color_of(visit.company.pk),
            calendar_back_url=visit_calendar_url(visit),
            can_reschedule=schedules and visit.is_scheduled and visit.scheduled_at > now + rules.MIN_NOTICE,
            can_cancel=visit.is_scheduled and ((schedules and visit.scheduled_at > now) or attends),
            can_complete=attends and visit.is_scheduled and visit.scheduled_at <= now,
            can_evaluate=visit.is_completed and has_capability(user, Capability.EVALUATION_MANAGE),
            # Solo las que el usuario puede ver: la empresa no ve evaluaciones en curso.
            evaluations=visible_evaluations(user).filter(visit=visit).order_by("pk") if visit.is_completed else [],
            **kwargs,
        )


class ScheduleMixin(CapabilityRequiredMixin):
    required_capabilities = (Capability.VISIT_SCHEDULE,)


class VisitFormViewMixin(ScheduleMixin, ModalFormMixin):
    form_class = VisitForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and has_capability(request.user, Capability.VISIT_SCHEDULE):
            if not can_schedule(request.user):
                messages.error(request, VisitCalendarView._schedule_blocker(request.user))
                return redirect("visits:list")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def get_cancel_url(self):
        return reverse("visits:list")

    def get_success_url(self):
        # Vuelve al calendario en la fecha de la visita, para que se vea donde quedo.
        return visit_calendar_url(self.object, requested_view(self.request))

    def form_valid(self, form):
        with transaction.atomic():
            # Dos empresas no pueden tomar el mismo horario: se revisa otra vez con la agenda bloqueada.
            rules.lock_schedule()
            data = form.cleaned_data
            if rules.overlapping_visit(form.instance.scheduled_at, data["duration_minutes"], form.instance.pk):
                form.add_error(None, "Otra empresa acaba de tomar ese horario. Elige otra hora.")
                return self.form_invalid(form)
            self.object = form.save()
        messages.success(self.request, self.success_title)
        return _done(self.request, self.get_success_url())


class VisitCreateView(VisitFormViewMixin, CreateView):
    title = "Agendar visita"
    submit_label = "Agendar visita"
    note = "El ingeniero verá la visita en su calendario. Puedes reprogramarla o cancelarla hasta una hora antes."
    success_title = "Visita agendada"

    def get_initial(self):
        """Desde el calendario llegan la fecha y la hora de la celda elegida."""
        initial = super().get_initial()
        today = timezone.localdate()
        day = agenda.parse_date(self.request.GET.get("fecha"), None)
        if day is not None and day >= today:
            initial["date"] = day
        try:
            hour = int(self.request.GET.get("hora", ""))
        except ValueError:
            hour = None
        if hour is not None and rules.WORK_START.hour <= hour < rules.WORK_END.hour:
            initial["time"] = time(hour)
        return initial


class VisitUpdateView(VisitFormViewMixin, UpdateView):
    title = "Reprogramar visita"
    submit_label = "Guardar cambios"
    success_title = "Visita reprogramada"

    def get_queryset(self):
        limit = timezone.now() + rules.MIN_NOTICE
        return selectors.visible_visits(self.request.user).filter(
            status=Visit.Status.SCHEDULED, scheduled_at__gt=limit
        )


class VisitActionMixin(ModalFormMixin):
    """Formulario corto sobre una visita programada: registrarla o cancelarla."""

    def get_queryset(self):
        return selectors.visible_visits(self.request.user).filter(status=Visit.Status.SCHEDULED)

    def get_cancel_url(self):
        return reverse("visits:detail", args=[self.object.pk])

    def get_success_url(self):
        return visit_calendar_url(self.object)

    def form_valid(self, form):
        self.apply(form.instance)
        form.save()
        messages.success(self.request, self.success_title)
        return _done(self.request, self.get_success_url())


class VisitCompleteView(CapabilityRequiredMixin, VisitActionMixin, UpdateView):
    """El ingeniero registra que la visita se hizo; desde ahi puede evaluar."""

    required_capabilities = (Capability.VISIT_ATTEND,)
    form_class = CompleteVisitForm
    title = "Registrar visita realizada"
    submit_label = "Registrar como realizada"
    success_title = "Visita registrada como realizada"
    note = "Después podrás crear las evaluaciones RULA de los puestos observados en esta visita."

    def get_queryset(self):
        return super().get_queryset().filter(scheduled_at__lte=timezone.now())

    def apply(self, visit):
        visit.status = Visit.Status.COMPLETED
        visit.completed_at = timezone.now()
        visit.completed_by = self.request.user


class VisitCancelView(CapabilityRequiredMixin, VisitActionMixin, UpdateView):
    required_capabilities = (Capability.VISIT_SCHEDULE, Capability.VISIT_ATTEND)
    form_class = CancelVisitForm
    title = "Cancelar visita"
    submit_label = "Cancelar visita"
    success_title = "Visita cancelada"

    @cached_property
    def by_company(self) -> bool:
        return not has_capability(self.request.user, Capability.VISIT_ATTEND)

    def get_queryset(self):
        visits = super().get_queryset()
        # La empresa cancela antes de que empiece; el ingeniero, tambien una que no se hizo.
        return visits.filter(scheduled_at__gt=timezone.now()) if self.by_company else visits

    def get_context_data(self, **kwargs):
        self.note = (
            "El horario quedará libre en el calendario."
            if self.by_company
            else "La empresa verá el motivo. Si la visita se hizo, regístrala como realizada en vez de cancelarla."
        )
        return super().get_context_data(**kwargs)

    def apply(self, visit):
        visit.status = Visit.Status.CANCELLED
        visit.cancelled_at = timezone.now()
        visit.cancelled_by = self.request.user


def _done(request, url):
    if is_htmx(request):
        return HttpResponse(status=204, headers={"HX-Redirect": full_reload_url(url)})
    return redirect(url)

