from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from .forms import LoginForm


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data["remember"]:
            self.request.session.set_expiry(0)
        return response


class AdminLoginRedirectView(RedirectView):
    """El panel de administracion usa el inicio de sesion del sistema.

    Quien ya tiene sesion pero no es administrador recibe 403: redirigirlo al login lo
    devolveria al panel, y de ahi otra vez al login, sin fin.
    """

    url = reverse_lazy("accounts:login")
    query_string = True

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            raise PermissionDenied
        return super().get(request, *args, **kwargs)
