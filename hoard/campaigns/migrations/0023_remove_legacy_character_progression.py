from django.db import migrations


class Migration(migrations.Migration):
    """Remove Hoard-owned class and level state in favour of native resources."""

    dependencies = [
        ("campaigns", "0022_character_death_state"),
    ]

    operations = [
        migrations.DeleteModel(name="CharacterChoice"),
        migrations.DeleteModel(name="CharacterClassLevel"),
        migrations.DeleteModel(name="CharacterLevelProgress"),
    ]
