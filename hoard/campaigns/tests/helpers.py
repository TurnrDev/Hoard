from __future__ import annotations

from django.contrib.auth import get_user_model

from hoard.campaigns.models import Campaign, Character, Player


def make_character(
    campaign: Campaign,
    name: str = 'Hero',
    *,
    active: bool = False,
    player: Player | bool = True,
) -> Character:
    membership = None
    if isinstance(player, Player):
        membership = player
    elif player:
        user = get_user_model().objects.create_user(username=f'{name}-{Player.objects.count()}')
        membership = Player.objects.create(campaign=campaign, user=user)
    return Character.objects.create(
        campaign=campaign,
        player=membership,
        name=name,
        race='Human',
        character_class='Fighter',
        strength=10,
        dexterity=10,
        constitution=10,
        intelligence=10,
        wisdom=10,
        charisma=10,
        is_active=active,
    )
