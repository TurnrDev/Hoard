from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0017_character_inspiration_expires_at"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="encountercombatant",
            name="show_hp_bar",
        ),
    ]
