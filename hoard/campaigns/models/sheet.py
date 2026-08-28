from __future__ import annotations

from django.db import models


class CharacterNote(models.Model):
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="notes"
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("pk",)


class CharacterFeature(models.Model):
    class Kind(models.TextChoices):
        FEAT = "feat", "Feat"
        FEATURE = "feature", "Feature"

    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="features"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.FEAT)
    catalogue_entry = models.ForeignKey(
        "compendium.CompendiumEntry", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name", "pk")


class CharacterSpell(models.Model):
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="spells"
    )
    catalogue_entry = models.ForeignKey(
        "compendium.CompendiumEntry", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=200)
    level = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    prepared = models.BooleanField(default=True)

    class Meta:
        ordering = ("level", "name", "pk")


class CharacterLoadout(models.Model):
    class Slot(models.TextChoices):
        ARMOR = "armor", "Armor"
        SHIELD = "shield", "Shield"
        WEAPON = "weapon", "Weapon"
        OTHER = "other", "Other"
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="loadout"
    )
    item = models.ForeignKey("compendium.CompendiumEntry", on_delete=models.CASCADE)
    equipped = models.BooleanField(default=False)
    slot = models.CharField(max_length=20, choices=Slot.choices, default=Slot.OTHER)
    label = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("character", "item"), name="unique_character_loadout_item"
            )
        ]


class CharacterEffect(models.Model):
    class RestExpiry(models.TextChoices):
        MANUAL = "manual", "Manual"
        SHORT = "short", "Short rest"
        LONG = "long", "Long rest"

    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="effects"
    )
    source = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    duration = models.CharField(max_length=200, blank=True)
    reminder = models.TextField(blank=True)
    expires_on_rest = models.CharField(
        max_length=20, choices=RestExpiry.choices, default=RestExpiry.MANUAL
    )
    # A list of {target, value, label}; targets are validated at the API edge.
    modifiers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("name", "pk")


class CharacterCompanion(models.Model):
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="companions"
    )
    monster_template = models.ForeignKey(
        "compendium.CompendiumEntry", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=200)
    armor_class = models.PositiveSmallIntegerField(default=10)
    max_hp = models.PositiveSmallIntegerField(default=1)
    current_hp = models.IntegerField(default=1)
    speed = models.CharField(max_length=100, blank=True)
    abilities = models.JSONField(default=dict, blank=True)
    attacks = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name", "pk")
