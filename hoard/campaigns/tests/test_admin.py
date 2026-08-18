from django.contrib import admin
from django.test import SimpleTestCase

from hoard.campaigns.models import ExperienceEntry, InventoryEntry, MoneyEntry


class AdminTests(SimpleTestCase):
    def test_ledger_entries_are_registered_as_read_only(self) -> None:
        for model in (InventoryEntry, MoneyEntry, ExperienceEntry):
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(self.client.request().wsgi_request))
            self.assertFalse(model_admin.has_change_permission(self.client.request().wsgi_request))
            self.assertFalse(model_admin.has_delete_permission(self.client.request().wsgi_request))
