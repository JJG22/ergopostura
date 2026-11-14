"""Entrega la página de React compilada. Todas las rutas bajo /app/ devuelven el mismo HTML y
React decide qué pantalla mostrar. El servidor no arma pantallas: solo entrega datos por la API.
"""
from functools import lru_cache

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

INDEX = settings.BASE_DIR / "frontend" / "dist" / "index.html"
MISSING = (
    "<!doctype html><meta charset=utf-8><title>ErgoPostura</title>"
    "<p style='font-family:sans-serif;padding:24px'>El cliente React aún no está compilado. "
    "En desarrollo ábrelo en http://localhost:5173/app/; para publicarlo, ejecuta <code>npm run build</code> en <code>frontend/</code>.</p>"
)


@lru_cache(maxsize=1)
def _index() -> str:
    return INDEX.read_text(encoding="utf-8")


@require_GET
@ensure_csrf_cookie
def spa(request, path=""):
    if not INDEX.exists():
        return HttpResponse(MISSING, status=503)
    html = _index() if not settings.DEBUG else INDEX.read_text(encoding="utf-8")
    response = HttpResponse(html)
    # El HTML siempre se revalida; los archivos JS y CSS llevan huella en el nombre y se cachean.
    response["Cache-Control"] = "no-cache"
    return response
