"""Vistas de la API v1. Son adaptadores: validan con los mismos formularios y consultan con los
mismos selectores que la aplicación, y responden JSON.
"""
from django.contrib.auth import login, logout, update_session_auth_hash
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.forms import LoginForm, OwnPasswordForm
from apps.dashboard.panels import greeting, panel_for

from . import presenters
from .errors import error_response
from .permissions import HasCapability


def form_errors(form) -> dict[str, list[str]]:
    return {("__all__" if name == "__all__" else name): [str(e) for e in errors] for name, errors in form.errors.items()}


class CsrfView(APIView):
    """Entrega la cookie CSRF que el cliente reenvía en cada petición que modifica datos."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"ok": True})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """Inicio de sesión por cookie. Exige CSRF aunque aún no haya sesión (evita el login CSRF)."""

    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        data = request.data
        form = LoginForm(request, data={
            "username": data.get("email", ""),
            "password": data.get("password", ""),
            "remember": data.get("remember") is True,
        })
        if not form.is_valid():
            fields = form_errors(form)
            message = fields.get("__all__", ["Revisa los datos marcados."])[0]
            return error_response("invalid_credentials" if "__all__" in fields else "validation_error",
                                  message, status.HTTP_400_BAD_REQUEST, fields)
        login(request, form.get_user())
        if not form.cleaned_data["remember"]:
            request.session.set_expiry(0)
        return Response(presenters.session_data(request.user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionView(APIView):
    """Quién soy, qué puedo hacer y qué menú me corresponde."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(presenters.session_data(request.user))


class PasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        form = OwnPasswordForm(request.user, data={
            "old_password": data.get("old_password", ""),
            "new_password1": data.get("new_password1", ""),
            "new_password2": data.get("new_password2", ""),
        })
        if not form.is_valid():
            return error_response("validation_error", "Revisa los datos marcados.", status.HTTP_400_BAD_REQUEST, form_errors(form))
        user = form.save()
        # Cambiar la contraseña invalida las demás sesiones, pero conserva la actual.
        update_session_auth_hash(request, user)
        return Response(presenters.session_data(user))


class DashboardView(APIView):
    """Panel principal del rol: los mismos datos que la pantalla actual, en JSON."""

    permission_classes = [IsAuthenticated, HasCapability]

    def get(self, request):
        user = request.user
        now = timezone.now()
        context = panel_for(user).build_context(user)
        local = timezone.localtime(now)
        data = {
            "role": user.role,
            "greeting": greeting(local.hour),
            "today": local.date().isoformat(),
            "display_name": user.first_name or user.email,
        }
        builder = {"admin": _support, "ingeniero": _engineer, "empresa": _company}[user.role]
        data.update(builder(context, now))
        return Response(data)


def _support(context, now) -> dict:
    return {
        "users_by_role": context["users_by_role"],
        "has_engineer": context["has_engineer"],
        "ai_ready": context["ai_ready"],
        "recent_accounts": [
            {**presenters.user_data(u), "is_active": u.is_active} for u in context["recent_accounts"]
        ],
    }


def _engineer(context, now) -> dict:
    today = timezone.localdate(now)
    return {
        "totals": context["totals"],
        "contract_counts": context["contract_counts"],
        "steps": [{"label": label, "done": done} for label, done in context["steps"]],
        "onboarding": context["onboarding"],
        "to_close": [presenters.visit_data(v, now) for v in context["to_close"]],
        "to_close_count": context["to_close_count"],
        "upcoming_visits": [presenters.visit_data(v, now) for v in context["upcoming_visits"]],
        "without_evaluation": [presenters.visit_data(v, now) for v in context["without_evaluation"]],
        "expiring_contracts": [presenters.contract_data(c, today) for c in context["expiring_contracts"]],
        "drafts_count": context["drafts_count"],
        "recent_evaluations": [presenters.evaluation_data(e) for e in context["recent_evaluations"]],
    }


def _company(context, now) -> dict:
    company = context["company"]
    contract = context["contract"]
    return {
        "company": {"id": company.pk, "name": company.name} if company else None,
        "counts": context["counts"],
        "contract": presenters.contract_data(contract) if contract else None,
        "pending_count": context["pending_count"],
        "upcoming_visits": [presenters.visit_data(v, now) for v in context["upcoming_visits"]],
        "recent_evaluations": [presenters.evaluation_data(e) for e in context["recent_evaluations"]],
    }

