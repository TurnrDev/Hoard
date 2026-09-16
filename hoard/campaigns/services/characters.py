"""Lifecycle commands for campaign characters."""

from django.core.exceptions import ValidationError

from ..models import CampaignContext, Character


class CharacterLifecycleService:
    """Create and update the minimal campaign character profile."""

    def create_npc(
        self, context: CampaignContext, fields: dict[str, object]
    ) -> Character:
        """Create an active NPC in the acting GM's campaign."""
        allowed = {"name", "race", "character_class"}
        values = {key: value for key, value in fields.items() if key in allowed}
        character = Character.objects.create(
            campaign=context.campaign,
            kind=Character.Kind.NPC,
            is_active=True,
            **values,
        )

        return character

    def update(
        self,
        context: CampaignContext,
        character: Character,
        fields: dict[str, object],
    ) -> Character:
        """Update the supported minimal profile fields."""
        allowed = {"name", "race", "character_class", "kind", "is_active"}
        unknown = set(fields) - allowed
        if unknown:
            unsupported = ", ".join(sorted(unknown))
            raise ValidationError(f"Unsupported character fields: {unsupported}")
        for key, value in fields.items():
            setattr(character, key, value)
        character.full_clean()
        character.save()

        return character

    def archive(self, context: CampaignContext, character: Character) -> Character:
        """Deactivate a character while retaining its ledger history."""
        character.is_active = False
        character.save(update_fields=("is_active",))

        return character
