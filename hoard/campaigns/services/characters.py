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
        allowed = {
            "name",
            "race",
            "character_class",
            "kind",
            "is_active",
            "rolled_hit_points",
            "hp_ability",
            "hp_adjustment",
            "initiative_adjustment",
            "proficiency_bonus_adjustment",
            "ability_bonuses",
            "background_ability_bonuses",
            "ability_score_adjustments",
            "skill_proficiencies",
            "skill_adjustments",
            "save_proficiencies",
            "save_adjustments",
            "jack_of_all_trades",
            "remarkable_athlete",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        }
        unknown = set(fields) - allowed
        if unknown:
            unsupported = ", ".join(sorted(unknown))
            raise ValidationError(f"Unsupported character fields: {unsupported}")
        for key, value in fields.items():
            setattr(character, key, value)

        if self.requires_profile_setup(context, character):
            required_fields = {
                "name": character.name.strip(),
                "race": character.race.strip(),
                "class": character.character_class.strip(),
            }
            missing_fields = [
                label for label, value in required_fields.items() if not value
            ]

            if missing_fields:
                fields_list = ", ".join(missing_fields)
                raise ValidationError(
                    f"Complete the character's {fields_list} before activating it."
                )

            character.is_active = True

        character.full_clean()
        character.save()

        return character

    def requires_profile_setup(
        self, context: CampaignContext, character: Character
    ) -> bool:
        """Return whether the owning player is completing an invited PC profile."""
        return (
            context.kind == CampaignContext.Kind.PC
            and character.kind == Character.Kind.PC
            and character.context_id == context.pk
            and not character.is_active
        )

    def archive(self, context: CampaignContext, character: Character) -> Character:
        """Deactivate a character while retaining its ledger history."""
        character.is_active = False
        character.save(update_fields=("is_active",))

        return character
