"""Marca del panel de administracion.

El panel lo usa solo el administrador para gestionar usuarios y datos maestros, asi que se
presenta como parte de ErgoPostura y no como la herramienta generica de Django.
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
