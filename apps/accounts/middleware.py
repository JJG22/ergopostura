from django.http import JsonResponse
from django.shortcuts import redirect

from apps.api.errors import error_body

CHANGE_PASSWORD = "/app/cambiar-contrasena"


class PasswordChangeRequiredMiddleware:
    """Quien entra con una contraseña temporal debe cambiarla antes de usar el sistema.

    La API solo le responde lo de su sesión (/api/v1/auth/); el cliente React le muestra la
    pantalla de cambio. El panel técnico lo envía a esa misma pantalla.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            path = request.path
            if path.startswith("/api/"):
                if not path.startswith("/api/v1/auth/"):
                    return JsonResponse(
                        error_body("password_change_required", "Cambia tu contraseña temporal para continuar."), status=403
                    )
            elif path.startswith("/admin/"):
                return redirect(CHANGE_PASSWORD)
        return self.get_response(request)
