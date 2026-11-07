import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0004_remove_city_department"),
    ]

    operations = [
        migrations.CreateModel(
            name="Worker",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
                ("first_name", models.CharField(max_length=120, verbose_name="nombres")),
                ("last_name", models.CharField(max_length=120, verbose_name="apellidos")),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("CC", "Cédula de ciudadanía"),
                            ("CE", "Cédula de extranjería"),
                            ("PPT", "Permiso por protección temporal"),
                            ("PA", "Pasaporte"),
                            ("TI", "Tarjeta de identidad"),
                        ],
                        default="CC",
                        max_length=3,
                        verbose_name="tipo de documento",
                    ),
                ),
                (
                    "document_number",
                    models.CharField(
                        max_length=20,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[A-Za-z0-9]{4,20}$", "Escribe solo letras y números, sin puntos."
                            )
                        ],
                        verbose_name="número de documento",
                    ),
                ),
                ("hired_on", models.DateField(blank=True, null=True, verbose_name="fecha de ingreso al puesto")),
                ("is_active", models.BooleanField(default=True, verbose_name="trabaja actualmente en el puesto")),
                (
                    "position",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="workers",
                        to="companies.position",
                        verbose_name="puesto de trabajo",
                    ),
                ),
            ],
            options={
                "verbose_name": "trabajador",
                "verbose_name_plural": "trabajadores",
                "ordering": ["last_name", "first_name", "pk"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("position", "document_type", "document_number"),
                        name="worker_unique_document_in_position",
                    )
                ],
            },
        ),
    ]
