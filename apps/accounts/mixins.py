from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import resolve_url

from apps.core.views import is_htmx

from .permissions import Capability, capabilities_of


class CapabilityRequiredMixin(LoginRequiredMixin):
    """Exige sesion y al menos una de las capacidades indicadas.

    Sin sesion redirige al login; con sesion pero sin permiso responde 403.
    Una vista sin capacidades declaradas se niega: el acceso nunca es implicito.
    """

    required_capabilities: tuple[Capability, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            if is_htmx(request):
                # Con la sesion vencida, recarga la pagina en vez de meter el login en un modal.
                return HttpResponse(status=204, headers={"HX-Redirect": resolve_url(settings.LOGIN_URL)})
            return self.handle_no_permission()
        if not capabilities_of(user).intersection(self.required_capabilities):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
