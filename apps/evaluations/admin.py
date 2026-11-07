from django.contrib import admin

from apps.core.admin import ReadOnlyAdmin

from .models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(ReadOnlyAdmin):
    """Solo consulta: los puntajes y el estado se manejan desde el flujo de la aplicacion."""

    list_display = ("code", "position", "evaluator", "evaluated_on", "status")
    list_filter = ("status",)
    list_select_related = ("position", "evaluator")
    search_fields = ("position__name", "position__area__site__company__name")
