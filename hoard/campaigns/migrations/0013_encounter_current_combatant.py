import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0012_encounter_encountercombatant_conditionevent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="encounter",
            name="current_combatant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="campaigns.encountercombatant",
            ),
        ),
    ]
