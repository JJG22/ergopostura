from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from .panels import panel_for


def greeting(hour: int) -> str:
    if hour < 12:
        return "Buenos días"
    return "Buenas tardes" if hour < 19 else "Buenas noches"


class HomeView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        return [panel_for(self.request.user).template]

    def get_context_data(self, **kwargs):
        user = self.request.user
        now = timezone.localtime()
        context = super().get_context_data(**kwargs)
        context.update(
            today=now,
            greeting=greeting(now.hour),
            display_name=user.first_name or user.email,
            **panel_for(user).build_context(user),
        )
        return context
