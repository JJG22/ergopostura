import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

ROLES = [("admin", "Soporte técnico"), ("ingeniero", "Ingeniero industrial"), ("empresa", "Empresa cliente")]


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_keep_only_support_admin"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="user", name="user_role_valid"),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(choices=ROLES, max_length=20, verbose_name="rol"),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(("role__in", ["admin", "ingeniero", "empresa"])), name="user_role_valid"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(default=False, verbose_name="debe cambiar la contraseña"),
        ),
        migrations.AddField(
            model_name="user",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_users",
                to=settings.AUTH_USER_MODEL,
                verbose_name="creada por",
            ),
        ),
    ]
