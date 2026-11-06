import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("api_id", models.PositiveIntegerField(unique=True, verbose_name="id en la API")),
                ("name", models.CharField(max_length=80, unique=True, verbose_name="nombre")),
            ],
            options={
                "verbose_name": "departamento",
                "verbose_name_plural": "departamentos",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Municipality",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("api_id", models.PositiveIntegerField(unique=True, verbose_name="id en la API")),
                ("name", models.CharField(max_length=100, verbose_name="nombre")),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="municipalities",
                        to="geography.department",
                        verbose_name="departamento",
                    ),
                ),
            ],
            options={
                "verbose_name": "municipio",
                "verbose_name_plural": "municipios",
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        models.F("department"),
                        django.db.models.functions.text.Lower("name"),
                        name="municipality_unique_name_in_department",
                    )
                ],
            },
        ),
    ]
