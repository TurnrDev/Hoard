"""Lifecycle commands for campaign characters."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import CampaignContext, Character, CharacterHistory
from .health import CharacterHealthService
from .history import character_snapshot, record_character_history


class CharacterLifecycleService:
    """Creates, updates, and archives characters with recorded history."""

    def create_npc(
        self, context: CampaignContext, fields: dict[str, object]
    ) -> Character:
        """Create an active completed NPC in the acting GM's campaign."""
        allowed = {
            "name",
            "race",
            "character_class",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        }
        values = {key: value for key, value in fields.items() if key in allowed}
        character = Character.objects.create(
            campaign=context.campaign,
            is_active=True,
            is_build_complete=True,
            **values,
        )
        CharacterHealthService().create_baseline(character, created_by=context)
        record_character_history(
            character,
            reason=CharacterHistory.Reason.CREATE,
            before=None,
            created_by=context,
            description="Created NPC",
        )

        return character

    def update(
        self,
        context: CampaignContext,
        character: Character,
        fields: dict[str, object],
    ) -> Character:
        """Update supported character fields and record the resulting history."""
        before = character_snapshot(character)
        blocked = {"current_hp", "temporary_hp", "campaign", "context", "level"}
        allowed = set(before) | {
            "background_entry_id",
            "race_entry_id",
            "subrace_identifier",
            "npc_level",
            "spell_slot_current",
            "proficiency_bonus_adjustment",
        }
        unknown = set(fields) - allowed
        blocked_fields = set(fields) & blocked
        if unknown or blocked_fields:
            unsupported = ", ".join(sorted(unknown | blocked_fields))
            raise ValidationError(f"Unsupported character fields: {unsupported}")
        for key, value in fields.items():
            setattr(character, key, value)
        character.full_clean()
        character.save()
        record_character_history(
            character,
            reason=CharacterHistory.Reason.EDIT,
            before=before,
            created_by=context,
        )

        return character

    def archive(self, context: CampaignContext, character: Character) -> Character:
        """Archive a character and record the lifecycle change."""
        before = character_snapshot(character)
        character.is_archived = True
        character.is_active = False
        character.archived_at = timezone.now()
        character.save(update_fields=("is_archived", "is_active", "archived_at"))
        record_character_history(
            character,
            reason=CharacterHistory.Reason.EDIT,
            before=before,
            created_by=context,
            description="Archived character",
        )

        return character
