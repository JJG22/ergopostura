"""Cuentas: soporte gestiona todas; el ingeniero, solo los accesos de las empresas cliente.

Los formularios y selectores son los de apps.accounts, así que las reglas (roles que puede
crear cada quien, correo único, clave temporal, última cuenta de soporte) no se duplican.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors
from apps.accounts.forms import AccountCreateForm, AccountForm, TemporaryPasswordForm, creatable_roles
from apps.accounts.models import Role
from apps.accounts.permissions import Capability
from apps.companies.models import Company

from .common import invalid, paginate, save_form
from .companies import account_data
from .errors import error_response
from .permissions import HasCapability

MANAGE = (Capability.USER_MANAGE, Capability.COMPANY_USER_MANAGE)
DUPLICATE_EMAIL = "Ya existe una cuenta con este correo."


class AccountsBase(APIView):
    permission_classes = [IsAuthenticated, HasCapability]
    required_capabilities = MANAGE

    def managed(self, pk):
        return get_object_or_404(selectors.manageable_users(self.request.user), pk=pk)


class AccountListView(AccountsBase):
    def get(self, request):
        role = request.query_params.get("role", "")
        role = role if role in Role.values else ""
        accounts = selectors.search_users(request.user, request.query_params.get("q", ""), role)
        data = paginate(request, accounts, account_data, per_page=20)
        roles = creatable_roles(request.user)
        data["creatable_roles"] = [{"value": r.value, "label": r.label} for r in map(Role, roles)]
        # Soporte filtra por rol; el ingeniero solo ve cuentas de empresa, no necesita filtro.
        data["role_filter"] = [{"value": r.value, "label": r.label} for r in Role] if len(roles) > 1 else []
        data["companies"] = (
            [{"id": c.pk, "name": c.name} for c in Company.objects.filter(is_active=True).order_by("name")]
            if Role.COMPANY in roles else []
        )
        return Response(data)

    def post(self, request):
        form = AccountCreateForm(data=request.data, actor=request.user)
        return save_form(form, account_data, integrity_message=DUPLICATE_EMAIL, created=True)


class AccountDetailView(AccountsBase):
    def put(self, request, pk):
        form = AccountForm(data=request.data, instance=self.managed(pk), actor=request.user)
        return save_form(form, account_data, integrity_message=DUPLICATE_EMAIL)


class AccountPasswordView(AccountsBase):
    def post(self, request, pk):
        account = self.managed(pk)
        form = TemporaryPasswordForm(account, data=request.data)
        if not form.is_valid():
            return invalid(form)
        form.save()
        return Response(account_data(account))


class AccountActiveView(AccountsBase):
    """Desactivar en vez de borrar: la cuenta conserva su historia. Body: {"is_active": bool}."""

    def post(self, request, pk):
        account = self.managed(pk)
        wanted = request.data.get("is_active")
        if not isinstance(wanted, bool):
            return error_response("validation_error", "Indica si la cuenta queda activa.", status.HTTP_400_BAD_REQUEST,
                                  {"is_active": ["Indica si la cuenta queda activa."]})
        if not wanted and account.pk == request.user.pk:
            return error_response("conflict", "No puedes desactivar tu propia cuenta.", status.HTTP_409_CONFLICT)
        if not wanted and selectors.is_last_active_admin(account):
            return error_response("conflict", "Es la última cuenta de soporte activa: el sistema quedaría sin administración.",
                                  status.HTTP_409_CONFLICT)
        if account.is_active != wanted:
            account.is_active = wanted
            # Una cuenta inactiva pierde su sesión en la siguiente petición (ModelBackend).
            account.save(update_fields=["is_active", "is_staff", "is_superuser"])
        return Response(account_data(account))
