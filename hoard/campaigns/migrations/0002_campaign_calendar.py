from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("campaigns", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="calendar_era_abbreviation",
            field=models.CharField(default="PD", max_length=20),
        ),
        migrations.AddField(
            model_name="campaign",
            name="calendar_era_name",
            field=models.CharField(default="Powder Dynasty", max_length=100),
        ),
        migrations.AddField(
            model_name="campaign",
            name="calendar_year",
            field=models.PositiveIntegerField(default=81),
        ),
        migrations.AddField(
            model_name="campaign",
            name="calendar_day",
            field=models.PositiveSmallIntegerField(default=137),
        ),
    ]
