from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("empresas/", include("apps.companies.urls")),
    path("geografia/", include("apps.geography.urls")),
    path("visitas/", include("apps.visits.urls")),
    path("evaluaciones/", include("apps.evaluations.urls")),
    path("indicadores/", include("apps.indicators.urls")),
    path("tareas/", include("apps.tasks.urls")),
]
