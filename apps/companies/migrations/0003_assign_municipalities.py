"""Reemplaza ciudad (texto libre) y departamento (lista fija) por un municipio del catalogo.

Cada registro existente se asocia al municipio con el mismo nombre en su departamento,
sin distinguir tildes ni mayusculas. Si el texto no corresponde a ningun municipio, se
usa la capital del departamento y se avisa en la salida, para no frenar el despliegue
ni perder el registro.
"""
from django.db import migrations

from apps.geography import catalog

# Nombres de la lista fija anterior que la API escribe distinto.
DEPARTMENT_ALIASES = {
    "bogota d.c.": "bogota",
    "san andres, providencia y santa catalina": "san andres y providencia",
}


def assign_municipalities(apps, schema_editor):
    Department = apps.get_model("geography", "Department")
    Municipality = apps.get_model("geography", "Municipality")
    capitals = {item["id"]: item.get("capital_id") for item in catalog.read_snapshot()["departments"]}
    departments = {catalog.normalize(d.name): d for d in Department.objects.all()}

    def resolve(record):
        key = catalog.normalize(record.department)
        department = departments.get(DEPARTMENT_ALIASES.get(key, key))
        if department is None:
            raise RuntimeError(f"Departamento desconocido: {record.department!r} en {record!r}")
        municipalities = {catalog.normalize(m.name): m for m in Municipality.objects.filter(department=department)}
        found = municipalities.get(catalog.normalize(record.city))
        if found is None:
            found = Municipality.objects.filter(api_id=capitals.get(department.api_id)).first()
            found = found or Municipality.objects.filter(department=department).first()
            print(f"\n  Aviso: «{record.city}» no está en {department.name}; se asignó {found.name}.")
        return found

    for model_name in ("Company", "Site"):
        for record in apps.get_model("companies", model_name).objects.all():
            record.municipality = resolve(record)
            record.save(update_fields=["municipality"])


class Migration(migrations.Migration):

    dependencies = [("companies", "0002_municipality")]

    operations = [migrations.RunPython(assign_municipalities, migrations.RunPython.noop)]
