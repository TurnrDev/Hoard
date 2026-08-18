from django.contrib.auth import get_user_model

from hoard.campaigns.models import Campaign, Character, Player


def make_character(campaign, name='Hero', *, active=False, player=True):
    membership = None
    if player:
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
