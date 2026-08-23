from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    XP_LEVEL_THRESHOLDS,
    Campaign,
    CampaignLevelEvent,
    CharacterLevelProgress,
)


def approve_campaign_level(campaign: Campaign, *, created_by) -> CampaignLevelEvent:
    with transaction.atomic():
        locked = Campaign.objects.select_for_update().get(pk=campaign.pk)
        if locked.level >= 20:
            raise ValidationError("The campaign is already level 20.")
        if CharacterLevelProgress.objects.filter(
            character__campaign=locked,
            character__is_active=True,
            character__context__isnull=False,
            level=locked.level,
            is_complete=False,
        ).exists():
            raise ValidationError(
                "All active players must finish their current level up."
            )
        next_level = locked.level + 1
        if locked.shared_experience < XP_LEVEL_THRESHOLDS[next_level - 1]:
            raise ValidationError("The campaign does not have enough XP to level up.")
        previous = locked.level
        locked.level = next_level
        locked.save(update_fields=("level",))
        CharacterLevelProgress.objects.bulk_create(
            [
                CharacterLevelProgress(character=character, level=next_level)
                for character in locked.characters.filter(
                    is_active=True, is_archived=False, context__isnull=False
                )
            ],
            ignore_conflicts=True,
        )
        return CampaignLevelEvent.objects.create(
            campaign=locked,
            created_by=created_by,
            previous_level=previous,
            next_level=next_level,
        )
