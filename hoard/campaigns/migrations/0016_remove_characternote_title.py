from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0015_encounter_initiative_tie_breaks"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="characternote",
            name="title",
        ),
    ]
