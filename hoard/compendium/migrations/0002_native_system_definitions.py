from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("compendium", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="compendiumsource",
            name="minimum_app_version",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="compendiumsource",
            name="package_checksum",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="compendiumsource",
            name="package_layout",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="compendiumsource",
            name="system_definition",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="compendiumsource",
            name="version",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="compendiumentry",
            name="kind",
            field=models.CharField(max_length=100),
        ),
    ]
