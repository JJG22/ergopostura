from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability, capabilities_of

from . import selectors


class TaskListView(CapabilityRequiredMixin, ListView):
    required_capabilities = (Capability.TASK_VIEW_ALL, Capability.TASK_VIEW_OWN, Capability.EVALUATION_MANAGE)
    template_name = "tasks/list.html"
    context_object_name = "recommendations"
    paginate_by = 15

    @property
    def showing_attended(self) -> bool:
        return self.request.GET.get("ver") == "atendidas"

    @property
    def query(self) -> str:
        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        select = (
            selectors.attended_recommendations if self.showing_attended else selectors.pending_recommendations
        )
        return select(self.request.user, self.query)

    def get_context_data(self, **kwargs):
        user = self.request.user
        capabilities = capabilities_of(user)
        return super().get_context_data(
            query=self.query,
            showing_attended=self.showing_attended,
            in_progress=selectors.evaluations_in_progress(user),
            shows_recommendations=bool(capabilities & {Capability.TASK_VIEW_ALL, Capability.TASK_VIEW_OWN}),
            # El responsable de tarea atiende recomendaciones sin acceder a la evidencia.
            can_open_evaluation=bool(
                capabilities
                & {
                    Capability.EVALUATION_VIEW_ALL,
                    Capability.EVALUATION_VIEW_OWN,
                }
            ),
            **kwargs,
        )


class AttendMixin(CapabilityRequiredMixin):
    required_capabilities = (Capability.TASK_ATTEND,)

    def recommendation(self, request, pk):
        return get_object_or_404(selectors.recommendations_for(request.user), pk=pk)


class AttendView(AttendMixin, View):
    def post(self, request, pk):
        recommendation = self.recommendation(request, pk)
        recommendation.attended_at = timezone.now()
        recommendation.attended_by = request.user
        recommendation.save(update_fields=["attended_at", "attended_by", "updated_at"])
        messages.success(request, "Recomendación atendida")
        return redirect("tasks:list")


class ReopenView(AttendMixin, View):
    def post(self, request, pk):
        recommendation = self.recommendation(request, pk)
        recommendation.attended_at = None
        recommendation.attended_by = None
        recommendation.save(update_fields=["attended_at", "attended_by", "updated_at"])
        messages.success(request, "Recomendación pendiente de nuevo")
        return redirect(f"{reverse('tasks:list')}?ver=atendidas")
