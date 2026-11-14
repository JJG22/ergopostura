from rest_framework.permissions import BasePermission

from apps.accounts.permissions import capabilities_of


class HasCapability(BasePermission):
    """La API usa la misma política de permisos que la aplicación: capacidades por rol.

    La vista declara `required_capabilities`; basta con tener una de ellas.
    Una vista sin capacidades declaradas solo exige sesión.
    """

    def has_permission(self, request, view):
        required = getattr(view, "required_capabilities", ())
        if not required:
            return True
        return bool(capabilities_of(request.user).intersection(required))
