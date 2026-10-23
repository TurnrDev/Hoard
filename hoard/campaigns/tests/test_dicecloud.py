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
    refresh_creature,
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

    def test_normalizes_skills_from_dicecloud_metadata(self):
        payload = self.payload()
        payload["creatureVariables"] = [
            {
                "acrobatics": {
                    "type": "skill",
                    "name": "Acrobatics",
                    "variableName": "acrobatics",
                    "ability": "intelligence",
                    "order": 20,
                    "proficiency": 0.5,
                    "value": 7,
                },
                "athletics": {
                    "skillType": "skill",
                    "name": "Athletics",
                    "variableName": "athletics",
                    "ability": "strength",
                    "order": 10,
                    "proficiency": 1,
                    "value": 5,
                },
                "dexteritySave": {
                    "type": "skill",
                    "name": "Dexterity Save",
                    "variableName": "dexteritySave",
                    "ability": "dexterity",
                    "order": 11,
                    "proficiency": 1,
                    "value": 8,
                },
                "initiative": {
                    "type": "skill",
                    "name": "Initiative",
                    "variableName": "initiative",
                    "ability": "dexterity",
                    "order": 9,
                    "proficiency": 0.5,
                    "value": 6,
                },
                "lightArmor": {
                    "type": "skill",
                    "name": "Light Armor",
                    "variableName": "lightArmor",
                    "order": 12,
                    "proficiency": 1,
                    "value": 3,
                },
            }
        ]

        profile = normalize_creature(self.creature_id, payload)

        self.assertEqual(
            profile["skills"],
            [
                {
                    "key": "acrobatics",
                    "name": "Acrobatics",
                    "ability": "intelligence",
                    "value": 7,
                    "proficiency": 0.5,
                    "order": 20,
                },
                {
                    "key": "athletics",
                    "name": "Athletics",
                    "ability": "strength",
                    "value": 5,
                    "proficiency": 1.0,
                    "order": 10,
                },
                {
                    "key": "initiative",
                    "name": "Initiative",
                    "ability": "dexterity",
                    "value": 6,
                    "proficiency": 0.5,
                    "order": 9,
                },
            ],
        )
        self.assertEqual(
            profile["saves"],
            {"dexterity": {"value": 8, "proficiency": 1.0}},
        )
        self.assertEqual(profile["stats"]["initiativeProficiency"], 0.5)

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

        self.assertEqual(
            profile["currency"],
            {
                "cp": 0,
                "sp": 7,
                "ep": 0,
                "gp": 14,
                "pp": 0,
                "gold_value": "14.7",
            },
        )

    @patch("hoard.campaigns.services.dicecloud.cache.set")
    @patch("hoard.campaigns.services.dicecloud.requests.get")
    def test_fetches_only_the_fixed_public_api_url(self, get, cache_set):
        response = Mock()
        response.json.return_value = self.payload()
        get.return_value = response

        fetch_and_normalize(self.creature_id)

        get.assert_called_once_with(
            f"https://dicecloud.com/api/creature/{self.creature_id}",
            headers={
                "Accept": "application/json",
                "User-Agent": "Hoard DiceCloud reader",
            },
            timeout=10,
        )
        response.raise_for_status.assert_called_once_with()
        cache_set.assert_called_once()

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_uses_cached_projection_without_a_live_fetch(self):
        profile = normalize_creature(self.creature_id, self.payload())
        cache.set(projection_cache_key(self.creature_id), profile, 60)
        with patch(
            "hoard.campaigns.services.dicecloud.fetch_and_normalize",
            side_effect=DiceCloudUnavailable("offline"),
        ) as fetch:
            self.assertEqual(load_creature(self.creature_id), profile)
        fetch.assert_not_called()

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_live_refresh_bypasses_a_cached_projection(self):
        cached = normalize_creature(self.creature_id, self.payload())
        refreshed = {**cached, "name": "Updated Ama"}
        cache.set(projection_cache_key(self.creature_id), cached, 60)

        with patch(
            "hoard.campaigns.services.dicecloud.fetch_and_normalize",
            return_value=refreshed,
        ) as fetch:
            self.assertEqual(refresh_creature(self.creature_id), refreshed)

        fetch.assert_called_once_with(self.creature_id)
