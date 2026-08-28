from django.db import migrations


def migrate_spell_slots(apps, schema_editor):
    Character = apps.get_model("campaigns", "Character")
    for character in Character.objects.exclude(spell_slots={}):
        if not character.spell_slot_current:
            character.spell_slot_current = character.spell_slots
            character.save(update_fields=("spell_slot_current",))


class Migration(migrations.Migration):
    dependencies = [("campaigns", "0009_character_has_inspiration_and_more")]

    operations = [
        migrations.RunPython(migrate_spell_slots, migrations.RunPython.noop),
        migrations.RemoveField(model_name="character", name="spell_slots"),
    ]
