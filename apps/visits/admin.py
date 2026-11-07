from django.contrib import admin

from apps.core.admin import ReadOnlyAdmin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(ReadOnlyAdmin):
    list_display = ("scheduled_at", "company", "site", "status", "contact_name")
    list_filter = ("status",)
    list_select_related = ("site__company",)
    search_fields = ("site__name", "site__company__name", "contact_name")
    date_hierarchy = "scheduled_at"
