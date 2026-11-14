from django.contrib import admin
from django.urls import include, path, re_path

from apps.accounts.views import AdminLoginRedirectView
from apps.core.spa import spa

urlpatterns = [
    # Un solo inicio de sesion: el del sistema. Conserva ?next= para volver al panel.
    path("admin/login/", AdminLoginRedirectView.as_view()),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api.urls")),
    re_path(r"^app/(?P<path>.*)$", spa, name="spa"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("empresas/", include("apps.companies.urls")),
    path("contratos/", include("apps.contracts.urls")),
    path("geografia/", include("apps.geography.urls")),
    path("visitas/", include("apps.visits.urls")),
    path("evaluaciones/", include("apps.evaluations.urls")),
    path("indicadores/", include("apps.indicators.urls")),
    path("tareas/", include("apps.tasks.urls")),
]
