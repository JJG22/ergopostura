import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Primero el municipio como opcional; 0003 lo completa y 0004 lo vuelve obligatorio."""

    dependencies = [
        ("companies", "0001_initial"),
        ("geography", "0002_load_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="municipality",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="companies",
                to="geography.municipality",
                verbose_name="municipio",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="municipality",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sites",
                to="geography.municipality",
                verbose_name="municipio",
            ),
        ),
    ]
