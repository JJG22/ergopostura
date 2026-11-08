from django.db import migrations, models


def create_row(apps, schema_editor):
    apps.get_model("visits", "ScheduleLock").objects.get_or_create(pk=1)


class Migration(migrations.Migration):

    dependencies = [
        ("visits", "0002_visit_by_site_with_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScheduleLock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ],
            options={"verbose_name": "bloqueo de agenda"},
        ),
        migrations.RunPython(create_row, migrations.RunPython.noop),
    ]
