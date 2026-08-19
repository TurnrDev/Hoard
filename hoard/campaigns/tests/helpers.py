from __future__ import annotations

from django.contrib.auth import get_user_model

from hoard.campaigns.models import Campaign, CampaignContext, Character


def make_character(
    campaign: Campaign,
    name: str = "Hero",
    *,
    active: bool = False,
    context: CampaignContext | bool = True,
) -> Character:
    membership = None
    if isinstance(context, CampaignContext):
        membership = context
    elif context:
        user = get_user_model().objects.create_user(
            username=f"{name}-{CampaignContext.objects.count()}"
        )
        membership = CampaignContext.objects.create(
            campaign=campaign, user=user, kind=CampaignContext.Kind.PC
        )
    return Character.objects.create(
        campaign=campaign,
        context=membership,
        name=name,
        race="Human",
        character_class="Fighter",
        strength=10,
        dexterity=10,
        constitution=10,
        intelligence=10,
        wisdom=10,
        charisma=10,
        is_active=active,
    )
