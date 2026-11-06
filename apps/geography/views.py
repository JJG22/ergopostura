from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .forms import municipality_choices


class MunicipalityOptionsView(LoginRequiredMixin, View):
    """Opciones de municipio del departamento elegido, para la lista dependiente."""

    def get(self, request):
        department, municipalities = municipality_choices(request.GET.get("department"))
        return render(
            request,
            "geography/_municipality_options.html",
            {"department": department, "municipalities": municipalities},
        )
