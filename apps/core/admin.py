"""Marca del panel de administracion.

El panel tecnico lo usa soporte para mantenimiento. Soporte no evalua, no agenda ni registra
empresas: esos datos se ven en modo consulta para diagnosticar, y solo se editan desde la
aplicacion, por quien tiene el rol para hacerlo.
"""
from django.contrib import admin
from django.contrib.auth.models import Group

admin.site.site_header = "ErgoPostura"
admin.site.site_title = "ErgoPostura"
admin.site.index_title = "Administración del sistema"
admin.site.site_url = "/"
admin.site.enable_nav_sidebar = True

# Los permisos salen del rol de cada usuario (apps/accounts/permissions.py); los grupos de
# Django no se usan y mostrarlos haria creer que asignar uno cambia algo.
admin.site.unregister(Group)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Consulta sin cambios: los datos del negocio los gestiona el rol que corresponde."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
