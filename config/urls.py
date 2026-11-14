"""El servidor es una API: /api/v1/ responde JSON y /app/ entrega el cliente React.

La única página que genera el servidor es el panel técnico de Django (/admin/), para soporte.
Las direcciones de las antiguas pantallas se redirigen a su equivalente en React.
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from apps.core.legacy import legacy_redirect
from apps.core.spa import spa

handler400 = "apps.core.legacy.bad_request"
handler403 = "apps.core.legacy.permission_denied"
handler404 = "apps.core.legacy.not_found"
handler500 = "apps.core.legacy.server_error"

urlpatterns = [
    # Un solo inicio de sesión: el de la aplicación. Conserva ?next= para volver al panel técnico.
    path("admin/login/", RedirectView.as_view(url="/app/ingresar", query_string=True)),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api.urls")),
    re_path(r"^app/(?P<path>.*)$", spa, name="spa"),
    re_path(r"^(?P<path>.*)$", legacy_redirect),
]
