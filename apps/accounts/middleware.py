from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

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
            target = reverse("accounts:password_change")
            allowed = (target, reverse("accounts:logout"))
            if request.path not in allowed and not request.path.startswith("/static/"):
                if is_htmx(request):
                    return HttpResponse(status=204, headers={"HX-Redirect": target})
                return redirect(target)
        return self.get_response(request)
