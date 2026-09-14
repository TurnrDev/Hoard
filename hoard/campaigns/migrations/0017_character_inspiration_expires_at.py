from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0016_remove_characternote_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="inspiration_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
