"""La visita pasa de un puesto a una sede, con duracion, motivo y estado.

La tabla esta vacia: accounts.0002 borro los datos de demostracion.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

USER = settings.AUTH_USER_MODEL


def user_fk(related_name, verbose_name):
    return models.ForeignKey(
        blank=True,
        editable=False,
        null=True,
        on_delete=django.db.models.deletion.SET_NULL,
        related_name=related_name,
        to=USER,
        verbose_name=verbose_name,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("visits", "0001_initial"),
        ("accounts", "0002_keep_only_support_admin"),
        ("companies", "0005_worker"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="visit", name="visit_unique_position_datetime"),
        migrations.RemoveField(model_name="visit", name="position"),
        migrations.RemoveField(model_name="visit", name="created_by"),
        migrations.AddField(
            model_name="visit",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="visits",
                to="companies.site",
                verbose_name="sede",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="visit",
            name="duration_minutes",
            field=models.PositiveSmallIntegerField(
                choices=[(60, "1 hora"), (120, "2 horas"), (180, "3 horas"), (240, "4 horas"), (480, "Jornada (8 horas)")],
                default=120,
                verbose_name="duración",
            ),
        ),
        migrations.AddField(
            model_name="visit",
            name="purpose",
            field=models.TextField(
                default="",
                help_text="Qué áreas o puestos quieren que se evalúen, o qué necesitan del servicio.",
                verbose_name="motivo de la visita",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="visit",
            name="contact_name",
            field=models.CharField(max_length=150, verbose_name="persona que recibe la visita"),
        ),
        migrations.AddField(
            model_name="visit",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=30, verbose_name="teléfono de contacto"),
        ),
        migrations.AddField(
            model_name="visit",
            name="status",
            field=models.CharField(
                choices=[("programada", "Programada"), ("realizada", "Realizada"), ("cancelada", "Cancelada")],
                default="programada",
                max_length=20,
                verbose_name="estado",
            ),
        ),
        migrations.AddField(model_name="visit", name="requested_by", field=user_fk("requested_visits", "agendada por")),
        migrations.AddField(
            model_name="visit",
            name="completed_at",
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name="registrada como realizada el"),
        ),
        migrations.AddField(model_name="visit", name="completed_by", field=user_fk("completed_visits", "registrada por")),
        migrations.AddField(
            model_name="visit",
            name="completion_notes",
            field=models.TextField(blank=True, verbose_name="observaciones de la visita"),
        ),
        migrations.AddField(
            model_name="visit",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name="cancelada el"),
        ),
        migrations.AddField(model_name="visit", name="cancelled_by", field=user_fk("cancelled_visits", "cancelada por")),
        migrations.AddField(
            model_name="visit",
            name="cancellation_reason",
            field=models.CharField(blank=True, max_length=300, verbose_name="motivo de la cancelación"),
        ),
        migrations.AddConstraint(
            model_name="visit",
            constraint=models.CheckConstraint(
                condition=models.Q(models.Q(("status", "realizada"), _negated=True), ("completed_at__isnull", False), _connector="OR"),
                name="visit_completed_has_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="visit",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("status", "cancelada"), _negated=True),
                    models.Q(("cancelled_at__isnull", False), models.Q(("cancellation_reason", ""), _negated=True)),
                    _connector="OR",
                ),
                name="visit_cancelled_has_reason",
            ),
        ),
        migrations.AddConstraint(
            model_name="visit",
            constraint=models.CheckConstraint(condition=models.Q(("duration_minutes__gt", 0)), name="visit_duration_positive"),
        ),
        migrations.AddIndex(
            model_name="visit",
            index=models.Index(fields=["status", "scheduled_at"], name="visit_status_start"),
        ),
    ]
