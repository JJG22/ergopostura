from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.api.errors import error_body
from apps.core.views import is_htmx


class PasswordChangeRequiredMiddleware:
    """Quien entra con una contrasena temporal debe cambiarla antes de usar el sistema.

    Solo se permiten la pagina de cambio, cerrar sesion y los archivos estaticos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            if request.path.startswith("/api/"):
                return self._api(request)
            if request.path.startswith("/app/"):
                return self.get_response(request)  # React muestra su propia pantalla de cambio.
            target = reverse("accounts:password_change")
            allowed = (target, reverse("accounts:logout"))
            if request.path not in allowed and not request.path.startswith("/static/"):
                if is_htmx(request):
                    return HttpResponse(status=204, headers={"HX-Redirect": target})
                return redirect(target)
        return self.get_response(request)

    def _api(self, request):
        if request.path.startswith("/api/v1/auth/"):
            return self.get_response(request)
        return JsonResponse(
            error_body("password_change_required", "Cambia tu contraseña temporal para continuar."), status=403
        )
