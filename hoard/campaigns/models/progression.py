from __future__ import annotations

from django.db import models


class CharacterClassLevel(models.Model):
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="class_levels"
    )
    level = models.PositiveSmallIntegerField()
    class_entry = models.ForeignKey(
        "compendium.CompendiumEntry", null=True, blank=True, on_delete=models.SET_NULL
    )
    class_name = models.CharField(max_length=200)
    subclass_identifier = models.CharField(max_length=200, blank=True)
    subclass_name = models.CharField(max_length=200, blank=True)
    is_override = models.BooleanField(default=False)

    class Meta:
        ordering = ("level",)
        constraints = [
            models.UniqueConstraint(
                fields=("character", "level"), name="unique_character_class_level"
            )
        ]


class CharacterChoice(models.Model):
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="build_choices"
    )
    origin_entry = models.ForeignKey(
        "compendium.CompendiumEntry", null=True, blank=True, on_delete=models.SET_NULL
    )
    level = models.PositiveSmallIntegerField(default=1)
    identifier = models.CharField(max_length=300)
    kind = models.CharField(max_length=50)
    values = models.JSONField(default=list)
    is_override = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("character", "level", "identifier"),
                name="unique_character_build_choice",
            )
        ]


class CharacterLevelProgress(models.Model):
    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.CASCADE, related_name="level_progress"
    )
    level = models.PositiveSmallIntegerField()
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("level",)
        constraints = [
            models.UniqueConstraint(
                fields=("character", "level"), name="unique_character_level_progress"
            )
        ]
