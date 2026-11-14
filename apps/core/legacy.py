"""Direcciones de las antiguas pantallas de Django.

El servidor ya no genera páginas: la interfaz es el cliente React en /app/. Un enlace guardado
o compartido con la forma vieja («/empresas/3/», «/visitas/agenda/?ver=por_cerrar») se
redirige a la pantalla equivalente, conservando el número y los filtros.
"""
import re
from urllib.parse import quote

from django.http import HttpResponseRedirect, JsonResponse

from apps.api.errors import error_body

APP = "/app"

# (patrón de la dirección vieja, ruta en React). Los grupos se reemplazan en orden.
ROUTES = (
    (r"", "/"),
    (r"ingresar/", "/ingresar"),
    (r"salir/", "/ingresar"),
    (r"cuenta/contrasena/", "/cambiar-contrasena"),
    (r"usuarios/nuevo/", "/usuarios?crear=1"),
    (r"usuarios/.*", "/usuarios"),
    (r"empresas/(\d+)/.*", "/empresas/{0}"),
    (r"empresas/.*", "/empresas"),
    (r"contratos/nuevo/", "/contratos/nuevo"),
    (r"contratos/(\d+)/editar/", "/contratos/{0}/editar"),
    (r"contratos/(\d+)/.*", "/contratos/{0}"),
    (r"contratos/.*", "/contratos"),
    (r"visitas/agenda/", "/visitas/agenda"),
    (r"visitas/(\d+)/.*", "/visitas/{0}"),
    (r"visitas/.*", "/visitas"),
    (r"evaluaciones/(\d+)/informe/", "/evaluaciones/{0}/informe"),
    (r"evaluaciones/posturas/(\d+)/analisis/", "/evaluaciones/posturas/{0}/analisis"),
    (r"evaluaciones/(\d+)/.*", "/evaluaciones/{0}"),
    (r"evaluaciones/.*", "/evaluaciones"),
    (r"indicadores/.*", "/indicadores"),
    (r"tareas/.*", "/tareas"),
)
COMPILED = tuple((re.compile(pattern + r"\Z"), target) for pattern, target in ROUTES)

# Parámetros que las pantallas React leen con el mismo nombre que tenían.
KEPT_PARAMS = {"q", "estado", "ver", "vista", "fecha", "rol", "empresa", "visita", "pagina", "next"}


def target_for(path: str, query: dict[str, str]) -> str | None:
    for pattern, route in COMPILED:
        match = pattern.match(path)
        if match:
            target = APP + route.format(*match.groups())
            params = "&".join(f"{k}={v}" for k, v in query.items() if k in KEPT_PARAMS and v)
            if not params:
                return target
            return f"{target}{'&' if '?' in target else '?'}{params}"
    return None


def legacy_redirect(request, path=""):
    if path and not path.endswith("/"):
        path += "/"
    query = {key: quote(value, safe="/") for key, value in request.GET.items()}
    target = target_for(path, query)
    if target is None:
        return not_found(request)
    return HttpResponseRedirect(target)


def not_found(request, exception=None):
    return JsonResponse(error_body("not_found", "No encontramos lo que buscas."), status=404)


def server_error(request):
    return JsonResponse(error_body("server_error", "El servidor no pudo responder. Intenta de nuevo en un momento."), status=500)


def permission_denied(request, exception=None):
    return JsonResponse(error_body("permission_denied", "No tienes permiso para hacer esto."), status=403)


def bad_request(request, exception=None):
    return JsonResponse(error_body("bad_request", "La solicitud no es válida."), status=400)
