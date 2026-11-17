"""Portada pública en la raíz del sitio: presenta el servicio a empresas que aún no son clientes.

Es una página estática (static/landing/index.html) que carga sus archivos desde /static/landing/;
el ingreso y todo lo demás siguen en el cliente React bajo /app/.
"""
from functools import lru_cache

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET

INDEX = settings.BASE_DIR / "static" / "landing" / "index.html"


@lru_cache(maxsize=1)
def _index() -> str:
    return INDEX.read_text(encoding="utf-8")


@require_GET
def landing(request):
    if not INDEX.exists():
        raise Http404("La portada no está disponible.")
    html = INDEX.read_text(encoding="utf-8") if settings.DEBUG else _index()
    response = HttpResponse(html)
    response["Cache-Control"] = "no-cache"
    return response
