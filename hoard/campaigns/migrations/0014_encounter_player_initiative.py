from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0013_encounter_current_combatant"),
    ]

    operations = [
        migrations.AddField(
            model_name="encounter",
            name="initiative_tie_choices",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Temporary exact-tie votes as "
                    "{player_context_id: preferred_combatant_id}. All keys are "
                    "decimal strings because JSON object keys are strings."
                ),
            ),
        ),
        migrations.AddField(
            model_name="encountercombatant",
            name="initiative_modifier",
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="encountercombatant",
            name="initiative_roll",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
