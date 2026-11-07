from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import CreateView, FormView, ListView, RedirectView, UpdateView

from apps.companies.models import Company
from apps.core.views import ModalFormMixin, full_reload_url, is_htmx

from . import selectors
from .forms import (
    AccountCreateForm,
    AccountForm,
    LoginForm,
    OwnPasswordForm,
    TemporaryPasswordForm,
    creatable_roles,
)
from .mixins import CapabilityRequiredMixin
from .models import Role
from .permissions import Capability

MANAGE_CAPABILITIES = (Capability.USER_MANAGE, Capability.COMPANY_USER_MANAGE)


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


class OwnPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = OwnPasswordForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("dashboard:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Contraseña actualizada")
        return response


def users_url(user=None) -> str:
    """Vuelve a la lista de cuentas, o al detalle de la empresa si la cuenta es de una."""
    if user is not None and user.company_id:
        return f"{reverse('companies:detail', args=[user.company_id])}#accesos"
    return reverse("accounts:users")


class UserListView(CapabilityRequiredMixin, ListView):
    required_capabilities = MANAGE_CAPABILITIES
    template_name = "accounts/users.html"
    context_object_name = "accounts"
    paginate_by = 20

    @property
    def role_filter(self) -> str:
        role = self.request.GET.get("rol", "")
        return role if role in Role.values else ""

    def get_queryset(self):
        return selectors.search_users(self.request.user, self.request.GET.get("q", ""), self.role_filter)

    def get_context_data(self, **kwargs):
        user = self.request.user
        # Soporte filtra por rol; el ingeniero solo ve cuentas de empresa, no necesita filtro.
        roles = list(Role) if len(creatable_roles(user)) > 1 else []
        return super().get_context_data(
            query=self.request.GET.get("q", "").strip(),
            role_filter=self.role_filter,
            roles=roles,
            can_create=bool(creatable_roles(user)),
            **kwargs,
        )


class UserCreateView(CapabilityRequiredMixin, ModalFormMixin, CreateView):
    required_capabilities = MANAGE_CAPABILITIES
    form_class = AccountCreateForm
    title = "Crear cuenta"
    submit_label = "Crear cuenta"
    success_title = "Cuenta creada"
    integrity_error_message = "Ya existe una cuenta con este correo."

    @cached_property
    def company(self):
        value = self.request.GET.get("empresa", "")
        return Company.objects.filter(pk=value, is_active=True).first() if value.isdigit() else None

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "actor": self.request.user, "company": self.company}

    def get_context_data(self, **kwargs):
        if self.company is not None:
            self.title = f"Crear acceso para {self.company.name}"
        self.note = (
            "Comparte el correo y la contraseña temporal por un canal seguro. "
            "Al primer ingreso, el sistema pedirá una contraseña nueva."
        )
        return super().get_context_data(**kwargs)

    def get_cancel_url(self):
        if self.company is None:
            return users_url()
        return f"{reverse('companies:detail', args=[self.company.pk])}#accesos"

    def get_success_url(self):
        return users_url(self.object)


class ManagedUserMixin(CapabilityRequiredMixin):
    required_capabilities = MANAGE_CAPABILITIES

    def get_queryset(self):
        return selectors.manageable_users(self.request.user)

    def get_managed(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)


class UserUpdateView(ManagedUserMixin, ModalFormMixin, UpdateView):
    form_class = AccountForm
    title = "Editar cuenta"
    success_title = "Cuenta actualizada"
    integrity_error_message = "Ya existe una cuenta con este correo."

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "actor": self.request.user}

    def get_cancel_url(self):
        return users_url(self.object)

    def get_success_url(self):
        return users_url(self.object)


class UserPasswordView(ManagedUserMixin, ModalFormMixin, FormView):
    form_class = TemporaryPasswordForm
    title = "Asignar contraseña temporal"
    submit_label = "Guardar contraseña"
    success_title = "Contraseña temporal asignada"

    @cached_property
    def managed(self):
        return self.get_managed(self.kwargs["pk"])

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.managed}

    def get_context_data(self, **kwargs):
        self.note = f"Cuenta: {self.managed.email}. La sesión abierta de esa persona se cerrará."
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, self.success_title)
        url = users_url(self.managed)
        if is_htmx(self.request):
            return HttpResponse(status=204, headers={"HX-Redirect": full_reload_url(url)})
        return redirect(url)

    def get_cancel_url(self):
        return users_url(self.managed)


class UserToggleActiveView(ManagedUserMixin, View):
    """Desactivar en vez de borrar: la cuenta conserva su historia (evaluaciones, visitas)."""

    def post(self, request, pk):
        managed = self.get_managed(pk)
        if managed.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
        elif selectors.is_last_active_admin(managed):
            messages.error(request, "Es la última cuenta de soporte activa: el sistema quedaría sin administración.")
        else:
            managed.is_active = not managed.is_active
            # Una cuenta inactiva pierde su sesion en la siguiente peticion (ModelBackend).
            managed.save(update_fields=["is_active", "is_staff", "is_superuser"])
            messages.success(request, "Cuenta activada" if managed.is_active else "Cuenta desactivada")
        return redirect(users_url(managed))

