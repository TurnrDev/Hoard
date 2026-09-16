import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0019_remove_characterspell_add_character_spells"),
        ("compendium", "0002_native_system_definitions"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="native_system_id",
            field=models.CharField(default="5e", max_length=200),
        ),
        migrations.AddField(
            model_name="campaign",
            name="native_system_source",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="compendium.compendiumsource",
            ),
        ),
        migrations.AddField(
            model_name="character",
            name="native_resources",
            field=models.ManyToManyField(
                blank=True,
                related_name="+",
                to="compendium.compendiumentry",
            ),
        ),
        migrations.AddField(
            model_name="character",
            name="native_state",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="character",
            name="native_system_source",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="compendium.compendiumsource",
            ),
        ),
        migrations.AddField(
            model_name="character",
            name="native_system_id",
            field=models.CharField(default="5e", max_length=200),
        ),
        migrations.AddField(
            model_name="character",
            name="native_system_version",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.CreateModel(
            name="CharacterNativeEvent",
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
                (
                    "occurred_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="Occurred At",
                    ),
                ),
                (
                    "actor_username",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="Actor Username",
                    ),
                ),
                (
                    "campaign_era_abbreviation",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        null=True,
                        verbose_name="Campaign Era Abbreviation",
                    ),
                ),
                (
                    "campaign_year",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Campaign Year",
                    ),
                ),
                (
                    "campaign_day",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Campaign Day",
                    ),
                ),
                ("event_name", models.CharField(max_length=300)),
                ("payload", models.JSONField(default=dict)),
                ("system_identifier", models.CharField(max_length=200)),
                ("system_version", models.CharField(blank=True, max_length=50)),
                ("system_checksum", models.CharField(blank=True, max_length=64)),
                ("fired_events", models.JSONField(default=list)),
                ("changes", models.JSONField(default=list)),
                ("messages", models.JSONField(default=list)),
                ("interface_actions", models.JSONField(default=list)),
                ("delayed_effects", models.JSONField(default=list)),
                ("unsupported", models.JSONField(default=list)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="campaigns.campaign",
                        verbose_name="Campaign",
                    ),
                ),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="native_events",
                        to="campaigns.character",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="campaigns.campaigncontext",
                    ),
                ),
            ],
            options={
                "verbose_name": "Native Character Event",
                "verbose_name_plural": "Native Character Events",
            },
        ),
    ]
