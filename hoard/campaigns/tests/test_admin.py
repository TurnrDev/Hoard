from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase, TestCase

from hoard.campaigns.models import (
    Campaign,
    Character,
    ExperienceEntry,
    InventoryEntry,
    MoneyEntry,
)

from .helpers import make_character


class AdminTests(SimpleTestCase):
    def test_ledger_entries_are_registered_as_read_only(self) -> None:
        for model in (InventoryEntry, MoneyEntry, ExperienceEntry):
            model_admin = admin.site._registry[model]
            self.assertFalse(
                model_admin.has_add_permission(self.client.request().wsgi_request)
            )
            self.assertFalse(
                model_admin.has_change_permission(self.client.request().wsgi_request)
            )
            self.assertFalse(
                model_admin.has_delete_permission(self.client.request().wsgi_request)
            )


class CharacterAdminTests(TestCase):
    def test_admin_activation_posts_shared_experience_baseline(self) -> None:
        campaign = Campaign.objects.create(name="Hoard", shared_experience=7)
        character = make_character(campaign)
        character.is_active = True
        form = type("CharacterForm", (), {"changed_data": ["is_active"]})()
        model_admin = admin.site._registry[Character]
        model_admin.save_model(
            RequestFactory().post("/admin/"), character, form, change=False
        )
        character.refresh_from_db()
        self.assertTrue(character.is_active)
        self.assertEqual(character.experience, 7)
