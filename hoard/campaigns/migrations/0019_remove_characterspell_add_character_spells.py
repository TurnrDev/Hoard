from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("campaigns", "0018_remove_encountercombatant_show_hp_bar")]

    operations = [
        migrations.DeleteModel(name="CharacterSpell"),
        migrations.AddField(
            model_name="character",
            name="spells",
            field=models.ManyToManyField(blank=True, to="compendium.compendiumentry"),
        ),
    ]
