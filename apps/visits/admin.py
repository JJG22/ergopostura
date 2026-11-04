from django.contrib import admin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("scheduled_at", "position", "company", "contact_name")
    list_select_related = ("position__area__site__company",)
    search_fields = ("position__name", "position__area__site__company__name", "contact_name")
    date_hierarchy = "scheduled_at"
    readonly_fields = ("created_by",)
