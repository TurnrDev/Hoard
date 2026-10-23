import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def clear_legacy_character_data(apps, schema_editor):
    Character = apps.get_model("campaigns", "Character")
    EncounterCombatant = apps.get_model("campaigns", "EncounterCombatant")
    HealthTransaction = apps.get_model("campaigns", "HealthTransaction")
    ExperienceEntry = apps.get_model("campaigns", "ExperienceEntry")
    ExperienceTransaction = apps.get_model("campaigns", "ExperienceTransaction")
    ExperienceAccount = apps.get_model("campaigns", "ExperienceAccount")
    MoneyEntry = apps.get_model("campaigns", "MoneyEntry")
    MoneyTransaction = apps.get_model("campaigns", "MoneyTransaction")
    MoneyAccount = apps.get_model("campaigns", "MoneyAccount")
    PartyExperienceAward = apps.get_model("campaigns", "PartyExperienceAward")

    for character in Character.objects.exclude(portrait=""):
        character.portrait.delete(save=False)

    npc_ids = list(Character.objects.filter(kind="npc").values_list("pk", flat=True))
    for combatant in EncounterCombatant.objects.filter(
        character_id__in=npc_ids
    ).select_related("character"):
        character = combatant.character
        combatant.name = character.name
        combatant.current_hp = character.current_hp
        combatant.max_hp = character.rolled_hit_points
        combatant.character_id = None
        combatant.save(update_fields=("name", "current_hp", "max_hp", "character"))

    HealthTransaction.objects.all().delete()

    for transaction in (
        ExperienceTransaction.objects.order_by("occurred_at", "pk")
        .select_related("campaign", "created_by__user")
        .prefetch_related("entries__account")
    ):
        recipient_amounts = [
            entry.amount
            for entry in transaction.entries.all()
            if not entry.account.is_system
        ]
        if not recipient_amounts:
            continue
        per_player, remainder = divmod(sum(recipient_amounts), len(recipient_amounts))
        PartyExperienceAward.objects.create(
            campaign=transaction.campaign,
            amount=(
                transaction.requested_amount
                if transaction.requested_amount
                else sum(recipient_amounts)
            ),
            recipient_count=len(recipient_amounts),
            awarded_per_player=per_player,
            discarded_amount=transaction.discarded_amount + abs(remainder),
            reason=transaction.reason,
            description=transaction.description,
            created_by=transaction.created_by,
            actor_username=transaction.actor_username,
            campaign_era_abbreviation=transaction.campaign_era_abbreviation,
            campaign_year=transaction.campaign_year,
            campaign_day=transaction.campaign_day,
            occurred_at=transaction.occurred_at,
        )

    ExperienceEntry.objects.all().delete()
    ExperienceTransaction.objects.update(reversal_of=None)
    ExperienceTransaction.objects.all().delete()
    ExperienceAccount.objects.all().delete()
    MoneyEntry.objects.all().delete()
    MoneyTransaction.objects.update(reversal_of=None)
    MoneyTransaction.objects.all().delete()
    MoneyAccount.objects.all().delete()

    Character.objects.filter(kind="npc").delete()
    Character.objects.update(is_active=False)


def seed_experience_recipient_counts(apps, schema_editor):
    Campaign = apps.get_model("campaigns", "Campaign")
    PartyExperienceAward = apps.get_model("campaigns", "PartyExperienceAward")

    for campaign in Campaign.objects.all().iterator():
        latest_award = (
            PartyExperienceAward.objects.filter(campaign_id=campaign.pk)
            .order_by("-occurred_at", "-pk")
            .first()
        )
        if latest_award is None:
            continue
        campaign.experience_recipient_count = latest_award.recipient_count
        campaign.save(update_fields=("experience_recipient_count",))


class Migration(migrations.Migration):
    dependencies = [("campaigns", "0003_restore_encounter_tracking")]
    atomic = False

    operations = [
        migrations.AddField(
            model_name="character",
            name="dicecloud_creature_id",
            field=models.CharField(blank=True, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="PartyExperienceAward",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.IntegerField()),
                ("recipient_count", models.PositiveIntegerField()),
                ("awarded_per_player", models.IntegerField()),
                ("discarded_amount", models.PositiveIntegerField(default=0)),
                ("reason", models.CharField(default="award", max_length=20)),
                ("description", models.TextField(blank=True)),
                ("actor_username", models.CharField(blank=True, max_length=150)),
                (
                    "campaign_era_abbreviation",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("campaign_year", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "campaign_day",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "occurred_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="party_xp_awards",
                        to="campaigns.campaign",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="party_xp_awards",
                        to="campaigns.campaigncontext",
                    ),
                ),
            ],
            options={"ordering": ("-occurred_at", "-pk")},
        ),
        migrations.RunPython(clear_legacy_character_data, migrations.RunPython.noop),
        migrations.RemoveField(model_name="character", name="ability_bonuses"),
        migrations.RemoveField(
            model_name="character", name="ability_score_adjustments"
        ),
        migrations.RemoveField(
            model_name="character", name="background_ability_bonuses"
        ),
        migrations.RemoveField(model_name="character", name="character_class"),
        migrations.RemoveField(model_name="character", name="charisma"),
        migrations.RemoveField(model_name="character", name="constitution"),
        migrations.RemoveField(model_name="character", name="dexterity"),
        migrations.RemoveField(model_name="character", name="hp_ability"),
        migrations.RemoveField(model_name="character", name="hp_adjustment"),
        migrations.RemoveField(model_name="character", name="initiative_adjustment"),
        migrations.RemoveField(model_name="character", name="intelligence"),
        migrations.RemoveField(model_name="character", name="jack_of_all_trades"),
        migrations.RemoveField(model_name="character", name="kind"),
        migrations.RemoveField(model_name="character", name="portrait"),
        migrations.RemoveField(
            model_name="character", name="proficiency_bonus_adjustment"
        ),
        migrations.RemoveField(model_name="character", name="race"),
        migrations.RemoveField(model_name="character", name="remarkable_athlete"),
        migrations.RenameField(
            model_name="character",
            old_name="rolled_hit_points",
            new_name="max_hp",
        ),
        migrations.AlterField(
            model_name="character",
            name="current_hp",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="character",
            name="max_hp",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="character",
            name="name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RemoveField(model_name="character", name="save_adjustments"),
        migrations.RemoveField(model_name="character", name="save_proficiencies"),
        migrations.RemoveField(model_name="character", name="skill_adjustments"),
        migrations.RemoveField(model_name="character", name="skill_proficiencies"),
        migrations.RemoveField(model_name="character", name="strength"),
        migrations.RemoveField(model_name="character", name="temporary_hp"),
        migrations.RemoveField(model_name="character", name="wisdom"),
        migrations.AlterField(
            model_name="character",
            name="context",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="character",
                to="campaigns.campaigncontext",
            ),
        ),
        migrations.AddConstraint(
            model_name="character",
            constraint=models.UniqueConstraint(
                condition=~models.Q(dicecloud_creature_id=""),
                fields=("campaign", "dicecloud_creature_id"),
                name="unique_dicecloud_creature_per_campaign",
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="experience_recipient_count",
            field=models.PositiveSmallIntegerField(
                default=1, verbose_name="XP Recipient Count"
            ),
        ),
        migrations.RunPython(
            seed_experience_recipient_counts, migrations.RunPython.noop
        ),
        migrations.DeleteModel(name="HealthTransaction"),
        migrations.DeleteModel(name="ExperienceEntry"),
        migrations.DeleteModel(name="MoneyEntry"),
        migrations.DeleteModel(name="ExperienceTransaction"),
        migrations.DeleteModel(name="MoneyTransaction"),
        migrations.DeleteModel(name="ExperienceAccount"),
        migrations.DeleteModel(name="MoneyAccount"),
    ]
