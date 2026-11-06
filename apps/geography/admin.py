from django.contrib import admin

from .models import Department, Municipality


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "api_id")
    search_fields = ("name",)


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "api_id")
    list_filter = ("department",)
    list_select_related = ("department",)
    search_fields = ("name", "department__name")
