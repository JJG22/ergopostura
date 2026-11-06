from datetime import time
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability
from apps.companies.cascade import PositionCascadeView
from apps.core.views import ModalFormMixin, is_htmx

from . import agenda, selectors
from .forms import VisitForm

VIEW_CAPABILITIES = (Capability.VISIT_VIEW_ALL, Capability.VISIT_VIEW_OWN)
UPCOMING_LIMIT = 5


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
        visits = list(selectors.visits_between(user, *period.bounds()))
        agenda.place(period, visits, now)

        companies = {visit.company.pk: visit.company for visit in visits}
        legend = [(company, agenda.color_of(pk)) for pk, company in sorted(companies.items(), key=lambda i: i[1].name)]
        upcoming = list(selectors.upcoming_visits(user)[:UPCOMING_LIMIT])
        for visit in upcoming:
            visit.color = agenda.color_of(visit.company.pk)

        return super().get_context_data(
            period=period,
            visits=visits,
            legend=legend,
            upcoming=upcoming,
            month_url=calendar_url(agenda.MONTH, period.anchor),
            week_url=calendar_url(agenda.WEEK, period.today if period.contains_today else period.anchor),
            previous_url=calendar_url(view, period.previous),
            next_url=calendar_url(view, period.next),
            today_url=calendar_url(view),
            **kwargs,
        )


class VisitAgendaView(CapabilityRequiredMixin, ListView):
    """Lista de visitas proximas o pasadas, para quien prefiere leerlas en orden."""

    required_capabilities = VIEW_CAPABILITIES
    template_name = "visits/agenda.html"
    context_object_name = "visits"
    paginate_by = 15

    @property
    def showing_past(self) -> bool:
        return self.request.GET.get("ver") == "pasadas"

    def get_queryset(self):
        user = self.request.user
        return selectors.past_visits(user) if self.showing_past else selectors.upcoming_visits(user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(showing_past=self.showing_past, **kwargs)


class VisitDetailView(CapabilityRequiredMixin, DetailView):
    required_capabilities = VIEW_CAPABILITIES
    context_object_name = "visit"

    def get_template_names(self):
        return ["visits/_detail_modal.html" if is_htmx(self.request) else "visits/detail.html"]

    def get_queryset(self):
        return selectors.visible_visits(self.request.user).select_related("created_by")

    def get_context_data(self, **kwargs):
        local = timezone.localtime(self.object.scheduled_at)
        return super().get_context_data(
            is_past=self.object.scheduled_at < timezone.now(),
            color=agenda.color_of(self.object.company.pk),
            calendar_back_url=calendar_url(agenda.MONTH, local.date()),
            **kwargs,
        )


class VisitManageMixin(CapabilityRequiredMixin):
    required_capabilities = (Capability.VISIT_MANAGE,)


class VisitFormViewMixin(VisitManageMixin, ModalFormMixin):
    form_class = VisitForm
    integrity_error_message = "Ya hay una visita registrada para este puesto en esa fecha y hora."

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def get_cancel_url(self):
        return reverse("visits:list")

    def get_success_url(self):
        # Vuelve al calendario en la fecha de la visita, para que se vea donde quedo.
        day = timezone.localtime(self.object.scheduled_at).date()
        return calendar_url(requested_view(self.request), day)


class VisitCreateView(VisitFormViewMixin, CreateView):
    title = "Registrar visita acordada"
    submit_label = "Guardar visita"
    note = "Guarda la información básica de la visita. No se enviarán notificaciones."
    success_title = "Visita registrada"

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
        if hour is not None and 0 <= hour <= 23:
            initial["time"] = time(hour)
        return initial


class VisitUpdateView(VisitFormViewMixin, UpdateView):
    title = "Editar visita"
    success_title = "Visita actualizada"

    def get_queryset(self):
        return selectors.visible_visits(self.request.user)


class VisitCascadeView(PositionCascadeView):
    required_capabilities = (Capability.VISIT_MANAGE,)
    form_class = VisitForm
