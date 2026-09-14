from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0014_encounter_player_initiative"),
    ]

    operations = [
        migrations.AddField(
            model_name="encounter",
            name="initiative_tie_breaks",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Resolved non-unanimous ties as "
                    "{comma_separated_combatant_ids: chosen_combatant_id}."
                ),
            ),
        ),
    ]
