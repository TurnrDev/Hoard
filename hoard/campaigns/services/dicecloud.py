"""Read-only access to public DiceCloud creature documents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Lock

import requests
from django.core.cache import cache
from django.utils import timezone

CREATURE_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{8,80}$")
API_URL_PATTERN = re.compile(
    r"^https://dicecloud\.com/api/creature/(?P<id>[A-Za-z0-9]{8,80})/?$"
)
CHARACTER_URL_PATTERN = re.compile(
    r"^https://dicecloud\.com/character/(?P<id>[A-Za-z0-9]{8,80})(?:/[^/?#]+)?/?$"
)
CACHE_TTL_SECONDS = int(timedelta(hours=24).total_seconds())
REQUEST_TIMEOUT_SECONDS = 10
ABILITY_NAMES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)
SKILL_NAMES = (
    "acrobatics",
    "animalHandling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleightOfHand",
    "stealth",
    "survival",
)


class DiceCloudError(Exception):
    """A public DiceCloud creature could not be loaded or understood."""


class DiceCloudUnavailable(DiceCloudError):
    """A live fetch failed and no usable cached projection exists."""


executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="dicecloud")
in_flight: dict[str, Future[dict[str, object]]] = {}
in_flight_lock = Lock()


def creature_id_from_input(value: str) -> str:
    candidate = value.strip()
    match = API_URL_PATTERN.fullmatch(candidate) or CHARACTER_URL_PATTERN.fullmatch(
        candidate
    )
    creature_id = match.group("id") if match else candidate
    if not CREATURE_ID_PATTERN.fullmatch(creature_id):
        raise DiceCloudError("Enter a DiceCloud creature ID or public character/API URL.")

    return creature_id


def cached_projection(creature_id: str) -> dict[str, object] | None:
    result = cache.get(f"dicecloud:creature:{creature_id}")
    return result if isinstance(result, dict) else None


def load_creature(creature_id: str) -> dict[str, object]:
    """Fetch current data, falling back only after a live upstream failure."""
    with in_flight_lock:
        future = in_flight.get(creature_id)
        if future is None:
            future = executor.submit(fetch_and_normalize, creature_id)
            in_flight[creature_id] = future

    try:
        return future.result()
    except DiceCloudError:
        cached = cached_projection(creature_id)
        if cached is not None:
            return {**cached, "stale": True}
        raise
    finally:
        if future.done():
            with in_flight_lock:
                if in_flight.get(creature_id) is future:
                    del in_flight[creature_id]


def fetch_and_normalize(creature_id: str) -> dict[str, object]:
    url = f"https://dicecloud.com/api/creature/{creature_id}"
    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Hoard DiceCloud reader",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise DiceCloudUnavailable("DiceCloud is unavailable right now.") from error

    projection = normalize_creature(creature_id, payload)
    cache.set(f"dicecloud:creature:{creature_id}", projection, CACHE_TTL_SECONDS)
    return projection


def normalize_creature(creature_id: str, payload: object) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise DiceCloudError("DiceCloud returned an invalid creature document.")
    creatures = payload.get("creatures")
    if not isinstance(creatures, list) or not creatures or not isinstance(creatures[0], Mapping):
        raise DiceCloudError("The DiceCloud creature is unavailable or not public.")
    creature = creatures[0]
    if creature.get("_id") != creature_id or not creature.get("public"):
        raise DiceCloudError("The DiceCloud creature is unavailable or not public.")

    variables = variable_values(payload.get("creatureVariables"))
    properties = payload.get("creatureProperties")
    image = creature.get("picture") or creature.get("avatarPicture")
    now = timezone.now().isoformat()
    return {
        "id": creature_id,
        "source_url": f"https://dicecloud.com/api/creature/{creature_id}",
        "fetched_at": now,
        "stale": False,
        "name": text(creature.get("name"), "Unnamed character"),
        "image_url": image if isinstance(image, str) else None,
        "type": text(creature.get("type"), "pc"),
        "details": {
            "description": text(creature.get("description"), ""),
            "alignment": text(creature.get("alignment"), ""),
            "gender": text(creature.get("gender"), ""),
            "race": text(creature.get("race"), ""),
            "class": text(creature.get("class"), ""),
        },
        "stats": canonical_stats(variables),
        "abilities": statistic_group(variables, ABILITY_NAMES),
        "saves": saving_throws(variables),
        "skills": statistic_group(variables, SKILL_NAMES),
        "resources": resources(variables, properties),
        "equipment": collection_entries(payload, properties, "item", "equipment"),
        "spells": collection_entries(payload, properties, "spell"),
        "features": collection_entries(payload, properties, "feature", "action"),
        "currency": currency(variables),
    }


def variable_values(values: object) -> dict[str, object]:
    if not isinstance(values, list):
        return {}

    result: dict[str, object] = {}
    for group in values:
        if not isinstance(group, Mapping):
            continue
        add_variable_value(result, group)
        for key, value in group.items():
            if isinstance(value, Mapping):
                add_variable_value(result, value, fallback_name=key)

    return result


def add_variable_value(
    result: dict[str, object],
    variable: Mapping[str, object],
    *,
    fallback_name: object = None,
) -> None:
    name = variable.get("variableName", variable.get("name", fallback_name))
    if not isinstance(name, str) or not name:
        return

    value = variable.get("value", variable.get("total"))
    if isinstance(value, Mapping):
        value = value.get("value", variable.get("total"))
    result[name] = value

    total = variable.get("total")
    if name == "hitPoints" and isinstance(total, (int, float, str)):
        result["maxHitPoints"] = total


def canonical_stats(variables: Mapping[str, object]) -> dict[str, object]:
    names = (
        "level",
        "hitPoints",
        "maxHitPoints",
        "tempHP",
        "armor",
        "initiative",
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
        "strengthSave",
        "dexteritySave",
        "constitutionSave",
        "intelligenceSave",
        "wisdomSave",
        "charismaSave",
    )
    return {name: variables.get(name) for name in names if name in variables}


def statistic_group(
    variables: Mapping[str, object], names: tuple[str, ...]
) -> dict[str, int | str | None]:
    return {name: display_value(variables.get(name)) for name in names if name in variables}


def saving_throws(variables: Mapping[str, object]) -> dict[str, int | str | None]:
    result = {}
    for ability in ABILITY_NAMES:
        variable_name = f"{ability}Save"
        if variable_name in variables:
            result[ability] = display_value(variables[variable_name])
    return result


def resources(
    variables: Mapping[str, object], properties: object
) -> list[dict[str, int | str | None]]:
    entries = []
    for name, value in variables.items():
        lowered = name.lower()
        if any(marker in lowered for marker in ("resource", "slot", "uses")):
            entries.append(entry(name, "", "resource", value))
    entries.extend(property_entries(properties, "resource"))
    return entries


def collection_entries(
    payload: Mapping[str, object],
    properties: object,
    *categories: str,
) -> list[dict[str, int | str | None]]:
    result = []
    for category in categories:
        result.extend(property_entries(properties, category))
        plural = f"{category}s"
        result.extend(raw_entries(payload.get(plural), category))
        result.extend(raw_entries(payload.get(f"creature{category.title()}s"), category))
    return unique_entries(result)


def property_entries(properties: object, category: str) -> list[dict[str, int | str | None]]:
    if not isinstance(properties, list):
        return []
    return [
        property_entry(value)
        for value in properties
        if isinstance(value, Mapping)
        and category in text(value.get("type"), "").lower()
    ]


def raw_entries(values: object, category: str) -> list[dict[str, int | str | None]]:
    if not isinstance(values, list):
        return []
    return [
        property_entry(value, category)
        for value in values
        if isinstance(value, Mapping)
    ]


def property_entry(
    value: Mapping[str, object], fallback_type: str = "property"
) -> dict[str, int | str | None]:
    description = value.get("description")
    if isinstance(description, Mapping):
        description = description.get("text")
    return entry(
        text(value.get("name"), "Unnamed entry"),
        text(description, ""),
        text(value.get("type"), fallback_type),
        value.get("value"),
    )


def entry(
    name: str, description: str, entry_type: str, value: object
) -> dict[str, int | str | None]:
    return {
        "name": name,
        "description": description,
        "type": entry_type,
        "value": display_value(value),
    }


def unique_entries(
    entries: list[dict[str, int | str | None]]
) -> list[dict[str, int | str | None]]:
    result = []
    seen = set()
    for value in entries:
        key = (value["type"], value["name"])
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def display_value(value: object) -> int | str | None:
    if isinstance(value, (int, float, str)):
        return value
    return None


def currency(variables: Mapping[str, object]) -> dict[str, int | str]:
    aliases = {
        "cp": ("cp", "copper"),
        "sp": ("sp", "silver"),
        "ep": ("ep", "electrum"),
        "gp": ("gp", "gold"),
        "pp": ("pp", "platinum"),
    }
    totals = {
        denomination: integer(next((variables.get(key) for key in keys if key in variables), 0))
        for denomination, keys in aliases.items()
    }
    totals["gold_value"] = str(
        Decimal(totals["cp"]) / 100
        + Decimal(totals["sp"]) / 10
        + Decimal(totals["ep"]) / 2
        + Decimal(totals["gp"])
        + Decimal(totals["pp"]) * 10
    )
    return totals


def integer(value: object) -> int:
    return int(value) if isinstance(value, (int, float, str)) else 0


def text(value: object, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default
