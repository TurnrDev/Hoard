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
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="loadout"
    )
    item = models.ForeignKey("compendium.CompendiumEntry", on_delete=models.CASCADE)
    equipped = models.BooleanField(default=False)
    label = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("character", "item"), name="unique_character_loadout_item"
            )
        ]


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
