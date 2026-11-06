"""Carga la copia de api-colombia.com guardada en el repositorio.

Asi una instalacion nueva tiene el catalogo sin depender de la red al migrar.
"""
from django.db import migrations

from apps.geography import catalog


def load_catalog(apps, schema_editor):
    catalog.load(
        catalog.read_snapshot(),
        apps.get_model("geography", "Department"),
        apps.get_model("geography", "Municipality"),
    )


class Migration(migrations.Migration):

    dependencies = [("geography", "0001_initial")]

    operations = [migrations.RunPython(load_catalog, migrations.RunPython.noop)]
