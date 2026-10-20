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
    projection_cache_key,
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

    def test_normalizes_race_and_class_from_creature_properties(self):
        payload = self.payload()
        payload["creatureProperties"] = [
            {"_id": "race-slot", "name": "Race", "type": "propertySlot"},
            {
                "_id": "sea-folk",
                "name": "Sea Folk",
                "parentId": "race-slot",
                "type": "feature",
            },
            {
                "_id": "ranger",
                "name": "Ranger",
                "type": "class",
                "subclassName": "Hunter",
            },
            {"name": "Level 1", "type": "classLevel", "parentId": "ranger"},
            {"name": "Level 2", "type": "classLevel", "parentId": "ranger"},
            {"name": "Level 3", "type": "classLevel", "parentId": "ranger"},
            {
                "_id": "bard",
                "name": "Bard [Multiclass]",
                "type": "class",
            },
            {"name": "Level 1", "type": "classLevel", "parentId": "bard"},
            {"name": "Level 2", "type": "classLevel", "parentId": "bard"},
        ]

        profile = normalize_creature(self.creature_id, payload)

        self.assertEqual(profile["details"]["race"], "Sea Folk")
        self.assertEqual(profile["details"]["class"], "Ranger (Hunter) 3 / Bard 2")

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

    def test_normalizes_currency_from_nested_inventory_containers(self):
        payload = self.payload()
        payload["creatureVariables"] = [{"gp": {"value": 999}}]
        payload["creatureProperties"] = [
            {
                "_id": "backpack",
                "name": "Backpack",
                "type": "container",
                "contents": [
                    {
                        "_id": "gold",
                        "name": "Gold Pieces",
                        "type": "item",
                        "quantity": 14,
                    },
                    {
                        "_id": "pouch",
                        "name": "Coin pouch",
                        "type": "container",
                        "contents": [
                            {
                                "_id": "silver",
                                "name": "Silver Pieces",
                                "type": "item",
                                "data": {"quantity": {"value": 7}},
                            }
                        ],
                    },
                ],
            }
        ]

        profile = normalize_creature(self.creature_id, payload)

        self.assertEqual(profile["currency"], {
            "cp": 0,
            "sp": 7,
            "ep": 0,
            "gp": 14,
            "pp": 0,
            "gold_value": "14.7",
        })

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
        cache.set(projection_cache_key(self.creature_id), profile, 60)
        with patch(
            "hoard.campaigns.services.dicecloud.fetch_and_normalize",
            side_effect=DiceCloudUnavailable("offline"),
        ):
            self.assertTrue(load_creature(self.creature_id)["stale"])
