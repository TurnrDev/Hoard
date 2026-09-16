from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0021_repair_incomplete_native_runtime"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="is_dead",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="character",
            name="died_campaign_era",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="character",
            name="died_campaign_year",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="character",
            name="died_campaign_day",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
