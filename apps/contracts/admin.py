from django.contrib import admin

from apps.core.admin import ReadOnlyAdmin

from .models import Contract


@admin.register(Contract)
class ContractAdmin(ReadOnlyAdmin):
    list_display = ("display_code", "company", "kind", "start_date", "end_date")
    list_filter = ("kind",)
    list_select_related = ("company",)
    search_fields = ("code", "company__name", "responsible_name")
    exclude = ("file_data", "ai_summary")
