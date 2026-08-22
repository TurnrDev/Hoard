from __future__ import annotations

from django.db import models


class CompendiumRepository(models.Model):
    """A registered repository, or the internal home for campaign custom entries."""

    identifier = models.CharField(max_length=200, unique=True)
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="compendium_repositories",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    repository_url = models.URLField(blank=True)
    github_repository = models.CharField(max_length=300, blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name", "identifier")

    def __str__(self) -> str:
        return self.name


class CompendiumSource(models.Model):
    """One imported system/resource collection inside a repository."""

    repository = models.ForeignKey(
        CompendiumRepository, on_delete=models.CASCADE, related_name="sources"
    )
    identifier = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name", "identifier")
        constraints = [
            models.UniqueConstraint(
                fields=("repository", "identifier"),
                name="unique_compendium_source_repository_identifier",
            )
        ]

    def __str__(self) -> str:
        return f"{self.repository}: {self.name}"


class CompendiumEntry(models.Model):
    """A reference entry imported from a pack or created for one campaign."""

    class Kind(models.TextChoices):
        ITEM = "item", "Item"
        WEAPON = "weapon", "Weapon"
        ARMOR = "armor", "Armor"
        SPELL = "spell", "Spell"
        FEAT = "feat", "Feat"
        CLASS = "class", "Class"
        RACE = "race", "Race"
        BACKGROUND = "background", "Background"
        MONSTER = "monster", "Monster"

    source = models.ForeignKey(
        CompendiumSource, on_delete=models.CASCADE, related_name="entries"
    )
    created_by = models.ForeignKey(
        "campaigns.CampaignContext",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_compendium_entries",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    source_identifier = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    source_book = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    cost_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    cost_currency = models.CharField(max_length=3, blank=True)
    weight_amount = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    weight_unit = models.CharField(max_length=20, blank=True)
    rarity = models.CharField(max_length=50, blank=True)
    is_magic = models.BooleanField(null=True, blank=True)
    requires_attunement = models.BooleanField(null=True, blank=True)
    data = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "kind", "source_identifier"),
                name="unique_compendium_entry_source",
            )
        ]
        indexes = [models.Index(fields=("source", "kind", "name"))]
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
