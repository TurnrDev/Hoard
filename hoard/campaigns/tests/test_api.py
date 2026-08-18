from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django.test import TestCase

from hoard.campaigns.models import Campaign, InventoryItem, Player
from hoard.campaigns.services import grant_loot

from .helpers import make_character


class CampaignApiTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.gm_user = user_model.objects.create_user(username='gm', password='password')
        self.player_user = user_model.objects.create_user(username='player', password='password')
        self.campaign = Campaign.objects.create(name='Hoard')
        self.gm = Player.objects.create(campaign=self.campaign, user=self.gm_user, is_game_master=True)
        self.player = Player.objects.create(campaign=self.campaign, user=self.player_user)
        self.gm_character = make_character(self.campaign, 'GM hero', player=self.gm)
        self.player_character = make_character(self.campaign, 'Player hero', player=self.player)
        self.item = InventoryItem.objects.create(campaign=None, name='Torch', source_identifier='torch', source_system='5e', source_repository='https://example.test')

    def test_members_can_create_items_but_only_gms_can_grant_loot(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.post(
            f'/api/campaigns/{self.campaign.pk}/items/', {'name': 'Homebrew rope', 'description': 'Very ropey.'}, content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['created_by_id'], self.player.pk)
        response = self.client.post(
            f'/api/campaigns/{self.campaign.pk}/actions/grant-loot/', {'recipient_id': self.player_character.pk, 'item_id': self.item.pk, 'quantity': 1}, content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.gm_user)
        response = self.client.post(
            f'/api/campaigns/{self.campaign.pk}/actions/grant-loot/', {'recipient_id': self.player_character.pk, 'item_id': self.item.pk, 'quantity': 1}, content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.player_character.inventory[self.item], 1)

    def test_players_only_receive_their_own_character_state(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.get(f'/api/campaigns/{self.campaign.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([character['id'] for character in response.json()['characters']], [self.player_character.pk])

    def test_login_campaign_list_and_history_respect_membership(self) -> None:
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get('/api/auth/csrf/')
        token = csrf_response.json()['csrfToken']
        response = client.post('/api/auth/login/', {'username': 'player', 'password': 'password'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        response = client.get('/api/campaigns/')
        self.assertEqual(response.json(), [{'id': self.campaign.pk, 'name': 'Hoard', 'is_game_master': False}])

        grant_loot(recipient=self.gm_character, item=self.item, quantity=1)
        grant_loot(recipient=self.player_character, item=self.item, quantity=1)
        response = client.get(f'/api/campaigns/{self.campaign.pk}/transactions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
