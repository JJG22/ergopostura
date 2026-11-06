import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("companies", "0003_assign_municipalities")]

    operations = [
        migrations.RemoveField(model_name="company", name="city"),
        migrations.RemoveField(model_name="company", name="department"),
        migrations.RemoveField(model_name="site", name="city"),
        migrations.RemoveField(model_name="site", name="department"),
        migrations.AlterField(
            model_name="company",
            name="municipality",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="companies",
                to="geography.municipality",
                verbose_name="municipio",
            ),
        ),
        migrations.AlterField(
            model_name="site",
            name="municipality",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sites",
                to="geography.municipality",
                verbose_name="municipio",
            ),
        ),
    ]
