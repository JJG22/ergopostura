from django.contrib import admin

from .models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    """Solo consulta: los puntajes y el estado se manejan desde el flujo de la aplicacion."""

    list_display = ("code", "position", "evaluator", "evaluated_on", "status")
    list_filter = ("status",)
    list_select_related = ("position", "evaluator")
    search_fields = ("position__name", "position__area__site__company__name")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
