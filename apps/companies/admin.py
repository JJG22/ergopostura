from django.contrib import admin

from .models import Area, Company, Position, Site


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "nit_display", "municipality", "is_active")
    list_filter = ("is_active", "municipality__department")
    list_select_related = ("municipality__department",)
    search_fields = ("name", "nit")
    autocomplete_fields = ("municipality",)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "municipality")
    list_select_related = ("company", "municipality")
    search_fields = ("name", "company__name")
    autocomplete_fields = ("municipality",)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "site")
    list_select_related = ("site",)
    search_fields = ("name", "site__name")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "area")
    list_select_related = ("area",)
    search_fields = ("name", "area__name")
