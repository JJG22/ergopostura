from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability
from apps.companies.cascade import PositionCascadeView
from apps.core.views import ModalFormMixin

from . import selectors
from .forms import VisitForm


class VisitListView(CapabilityRequiredMixin, ListView):
    required_capabilities = (Capability.VISIT_VIEW_ALL, Capability.VISIT_VIEW_OWN)
    template_name = "visits/list.html"
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
        return reverse("visits:list")


class VisitCreateView(VisitFormViewMixin, CreateView):
    title = "Registrar visita acordada"
    submit_label = "Guardar visita"
    note = "Guarda la información básica de la visita. No se enviarán notificaciones."
    success_title = "Visita registrada"


class VisitUpdateView(VisitFormViewMixin, UpdateView):
    title = "Editar visita"
    success_title = "Visita actualizada"

    def get_queryset(self):
        return selectors.visible_visits(self.request.user)


class VisitCascadeView(PositionCascadeView):
    required_capabilities = (Capability.VISIT_MANAGE,)
    form_class = VisitForm
