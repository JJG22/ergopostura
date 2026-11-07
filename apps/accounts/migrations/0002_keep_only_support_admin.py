"""Deja la base con una sola cuenta: el administrador de soporte.

Hasta aqui la base tenia datos de demostracion y roles que ya no existen (evaluador,
consulta, responsable de tarea). El sistema arranca de nuevo: el administrador crea al
ingeniero industrial y el ingeniero registra sus empresas reales.

Se conserva la cuenta de DJANGO_ADMIN_EMAIL. Si esa variable no esta definida, o la cuenta
no existe, se conservan los administradores para no dejar el sistema sin acceso.
Corre una sola vez por base de datos, como toda migracion.
"""
import os

from django.db import migrations

# De las hojas a la raiz, para respetar las llaves foraneas protegidas.
DATA_MODELS = (
    ("evaluations", "Recommendation"),
    ("evaluations", "RulaAssessment"),
    ("evaluations", "PosturePhoto"),
    ("evaluations", "Posture"),
    ("evaluations", "Evaluation"),
    ("visits", "Visit"),
    ("companies", "Position"),
    ("companies", "Area"),
    ("companies", "Site"),
)


def keep_only_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for app_label, model_name in DATA_MODELS:
        apps.get_model(app_label, model_name).objects.all().delete()

    email = os.environ.get("DJANGO_ADMIN_EMAIL", "").strip().lower()
    kept = User.objects.filter(email__iexact=email) if email else User.objects.none()
    if not kept.exists():
        kept = User.objects.filter(role="admin")
    User.objects.exclude(pk__in=list(kept.values_list("pk", flat=True))).delete()
    kept.update(role="admin", company=None, is_staff=True, is_superuser=True)

    apps.get_model("companies", "Company").objects.all().delete()
    apps.get_model("sessions", "Session").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("sessions", "0001_initial"),
        ("companies", "0004_remove_city_department"),
        ("visits", "0001_initial"),
        ("evaluations", "0003_rulaassessment_ai_suggestion"),
    ]

    operations = [migrations.RunPython(keep_only_admin, migrations.RunPython.noop)]
