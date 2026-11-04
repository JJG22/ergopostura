from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("empresas/", include("apps.companies.urls")),
    path("visitas/", include("apps.visits.urls")),
]
