from django.contrib import admin

from apps.core.admin import ReadOnlyAdmin

from .models import Area, Company, Position, Site, Worker


@admin.register(Company)
class CompanyAdmin(ReadOnlyAdmin):
    list_display = ("name", "nit_display", "municipality", "is_active")
    list_filter = ("is_active", "municipality__department")
    list_select_related = ("municipality__department",)
    search_fields = ("name", "nit")


@admin.register(Site)
class SiteAdmin(ReadOnlyAdmin):
    list_display = ("name", "company", "municipality")
    list_select_related = ("company", "municipality")
    search_fields = ("name", "company__name")


@admin.register(Area)
class AreaAdmin(ReadOnlyAdmin):
    list_display = ("name", "site")
    list_select_related = ("site",)
    search_fields = ("name", "site__name")


@admin.register(Position)
class PositionAdmin(ReadOnlyAdmin):
    list_display = ("name", "area")
    list_select_related = ("area",)
    search_fields = ("name", "area__name")


@admin.register(Worker)
class WorkerAdmin(ReadOnlyAdmin):
    list_display = ("full_name", "position", "is_active")
    list_select_related = ("position",)
    search_fields = ("first_name", "last_name", "position__name")
