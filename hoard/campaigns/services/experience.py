from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Campaign, PartyExperienceAward


def award_shared_experience(
    campaign: Campaign,
    amount: int,
    description: str = "",
    dry_run: bool = False,
    created_by=None,
    return_transaction: bool = False,
) -> int | tuple[int, PartyExperienceAward]:
    """Split an award by the campaign's configured XP recipient count."""
    if amount <= 0:
        raise ValidationError("XP awards must be positive.")

    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        recipient_count = campaign.experience_recipient_count
        per_player, remainder = divmod(amount, recipient_count)
        if not per_player:
            raise ValidationError("This award would grant zero XP to every player.")
        if dry_run:
            return per_player

        award = PartyExperienceAward.objects.create(
            campaign=campaign,
            amount=amount,
            recipient_count=recipient_count,
            awarded_per_player=per_player,
            discarded_amount=remainder,
            reason="award",
            description=description,
            created_by=created_by,
            actor_username=(
                created_by.user.get_username() if created_by is not None else "System"
            ),
            campaign_era_abbreviation=campaign.calendar_era_abbreviation,
            campaign_year=campaign.calendar_year,
            campaign_day=campaign.calendar_day,
        )
        campaign.shared_experience += per_player
        campaign.save(update_fields=("shared_experience",))
        return (per_player, award) if return_transaction else per_player
