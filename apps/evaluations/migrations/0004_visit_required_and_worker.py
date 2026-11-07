"""La evaluacion exige una visita realizada y puede indicar el trabajador observado.

La tabla esta vacia: accounts.0002 borro los datos de demostracion.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0003_rulaassessment_ai_suggestion"),
        ("accounts", "0002_keep_only_support_admin"),
        ("companies", "0005_worker"),
        ("visits", "0002_visit_by_site_with_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="evaluation",
            name="visit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="evaluations",
                to="visits.visit",
                verbose_name="visita realizada",
            ),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="worker",
            field=models.ForeignKey(
                blank=True,
                help_text="Opcional. Quien realizaba la actividad durante la observación.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="evaluations",
                to="companies.worker",
                verbose_name="trabajador observado",
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="evaluator",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="evaluations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ingeniero evaluador",
            ),
        ),
    ]
