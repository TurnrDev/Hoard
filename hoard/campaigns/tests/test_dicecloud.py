from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from hoard.campaigns.services.dicecloud import (
    DiceCloudError,
    DiceCloudUnavailable,
    creature_id_from_input,
    fetch_and_normalize,
    load_creature,
    normalize_creature,
)


class DiceCloudServiceTests(SimpleTestCase):
    creature_id = "sfdxGdwav3hoNATLJ"

    def payload(self):
        return {
            "creatures": [
                {
                    "_id": self.creature_id,
                    "name": "Ama",
                    "public": True,
                    "picture": "https://images.example/ama.png",
                    "type": "pc",
                }
            ],
            "creatureVariables": [
                {"name": "level", "value": 5},
                {"name": "hitPoints", "value": 31},
                {"name": "armor", "value": 16},
                {"name": "gp", "value": 14},
            ],
            "creatureProperties": [{"name": "Example feature"}],
        }

    def test_accepts_only_a_creature_id_or_public_dicecloud_url(self):
        self.assertEqual(creature_id_from_input(self.creature_id), self.creature_id)
        self.assertEqual(
            creature_id_from_input(
                f"https://dicecloud.com/api/creature/{self.creature_id}"
            ),
            self.creature_id,
        )
        self.assertEqual(
            creature_id_from_input(
                f"https://dicecloud.com/character/{self.creature_id}/Ama"
            ),
            self.creature_id,
        )
        with self.assertRaises(DiceCloudError):
            creature_id_from_input("https://other.example/api/creature/anything")

    def test_normalizes_public_profile_without_persisting_raw_data(self):
        profile = normalize_creature(self.creature_id, self.payload())

        self.assertEqual(profile["name"], "Ama")
        self.assertEqual(profile["stats"], {"level": 5, "hitPoints": 31, "armor": 16})
        self.assertEqual(profile["currency"]["gp"], 14)
        self.assertFalse(profile["stale"])

    def test_normalizes_grouped_dicecloud_variables(self):
        payload = self.payload()
        payload["creatureVariables"] = [
            {
                "level": {"value": 5},
                "hitPoints": {"value": 31, "total": 44},
                "armor": {"value": 16},
                "gp": {"value": 14},
            }
        ]

        profile = normalize_creature(self.creature_id, payload)

        self.assertEqual(
            profile["stats"],
            {"level": 5, "hitPoints": 31, "maxHitPoints": 44, "armor": 16},
        )
        self.assertEqual(profile["currency"]["gp"], 14)

    @patch("hoard.campaigns.services.dicecloud.cache.set")
    @patch("hoard.campaigns.services.dicecloud.requests.get")
    def test_fetches_only_the_fixed_public_api_url(self, get, cache_set):
        response = Mock()
        response.json.return_value = self.payload()
        get.return_value = response

        fetch_and_normalize(self.creature_id)

        get.assert_called_once_with(
            f"https://dicecloud.com/api/creature/{self.creature_id}",
            headers={"Accept": "application/json", "User-Agent": "Hoard DiceCloud reader"},
            timeout=10,
        )
        response.raise_for_status.assert_called_once_with()
        cache_set.assert_called_once()

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_uses_last_projection_only_after_a_live_fetch_failure(self):
        profile = normalize_creature(self.creature_id, self.payload())
        with patch(
            "hoard.campaigns.services.dicecloud.fetch_and_normalize",
            return_value=profile,
        ):
            self.assertFalse(load_creature(self.creature_id)["stale"])
        cache.set(f"dicecloud:creature:{self.creature_id}", profile, 60)
        with patch(
            "hoard.campaigns.services.dicecloud.fetch_and_normalize",
            side_effect=DiceCloudUnavailable("offline"),
        ):
            self.assertTrue(load_creature(self.creature_id)["stale"])
