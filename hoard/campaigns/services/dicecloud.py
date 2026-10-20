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
LIVE_SYNC_FAILURE_BASE_SECONDS = 10
LIVE_SYNC_FAILURE_MAX_SECONDS = int(timedelta(minutes=5).total_seconds())
CACHE_KEY_VERSION = "v8"
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
    result = cache.get(projection_cache_key(creature_id))
    return result if isinstance(result, dict) else None


def projection_cache_key(creature_id: str) -> str:
    """Keep projections from incompatible normalizers out of the fallback cache."""
    return f"dicecloud:creature:{CACHE_KEY_VERSION}:{creature_id}"


def refresh_failure_cache_key(creature_id: str) -> str:
    """Return the cache key that limits retries after an upstream failure."""
    return f"dicecloud:refresh-failure:{CACHE_KEY_VERSION}:{creature_id}"


def load_creature(creature_id: str) -> dict[str, object]:
    """Return a cached projection, fetching only when no projection is available."""
    cached = cached_projection(creature_id)
    if cached is not None:
        return cached

    return refresh_creature(creature_id)


def refresh_creature(creature_id: str) -> dict[str, object]:
    """Fetch and cache a current projection, regardless of any cached value."""
    with in_flight_lock:
        future = in_flight.get(creature_id)
        if future is None:
            future = executor.submit(fetch_and_normalize, creature_id)
            in_flight[creature_id] = future

    try:
        return future.result()
    finally:
        if future.done():
            with in_flight_lock:
                if in_flight.get(creature_id) is future:
                    del in_flight[creature_id]


def refresh_is_allowed(creature_id: str) -> bool:
    """Return whether live sync may retry this creature after a recent failure."""
    state = cache.get(refresh_failure_cache_key(creature_id))
    if not isinstance(state, dict):
        return True

    retry_after = state.get("retry_after")
    return not isinstance(retry_after, (int, float)) or retry_after <= timezone.now().timestamp()


def record_refresh_failure(creature_id: str) -> int:
    """Back off repeated live-sync failures and return the delay in seconds."""
    key = refresh_failure_cache_key(creature_id)
    state = cache.get(key)
    attempts = state.get("attempts", 0) if isinstance(state, dict) else 0
    if not isinstance(attempts, int):
        attempts = 0

    attempts += 1
    delay = min(
        LIVE_SYNC_FAILURE_BASE_SECONDS * (2 ** (attempts - 1)),
        LIVE_SYNC_FAILURE_MAX_SECONDS,
    )
    cache.set(
        key,
        {
            "attempts": attempts,
            "retry_after": timezone.now().timestamp() + delay,
        },
        LIVE_SYNC_FAILURE_MAX_SECONDS,
    )
    return delay


def clear_refresh_failure(creature_id: str) -> None:
    """Allow the next failure to start again at the shortest retry delay."""
    cache.delete(refresh_failure_cache_key(creature_id))


def projections_differ(
    previous: dict[str, object] | None, current: dict[str, object]
) -> bool:
    """Compare projections while ignoring metadata that changes on every fetch."""
    if previous is None:
        return True

    ignored_keys = {"fetched_at", "stale"}
    previous_content = {
        key: value for key, value in previous.items() if key not in ignored_keys
    }
    current_content = {
        key: value for key, value in current.items() if key not in ignored_keys
    }
    return previous_content != current_content


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
    cache.set(projection_cache_key(creature_id), projection, CACHE_TTL_SECONDS)
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
    metadata = variable_metadata(payload.get("creatureVariables"))
    properties = payload.get("creatureProperties")
    details = character_details(creature, variables, properties)
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
            **details,
        },
        "stats": canonical_stats(variables, metadata),
        "abilities": statistic_group(variables, ABILITY_NAMES),
        "saves": saving_throws(variables, metadata),
        "skills": skill_entries(payload.get("creatureVariables")),
        "resources": resources(variables, properties),
        "equipment": collection_entries(payload, properties, "item", "equipment"),
        "spells": collection_entries(payload, properties, "spell"),
        "features": collection_entries(payload, properties, "feature", "action"),
        "currency": currency(variables, payload, properties),
    }


def character_details(
    creature: Mapping[str, object],
    variables: Mapping[str, object],
    properties: object,
) -> dict[str, str]:
    """Find identity details that DiceCloud stores as properties rather than fields."""
    return {
        "race": identity_detail(
            creature,
            variables,
            properties,
            field_names=("race", "raceName", "species", "ancestry", "lineage"),
            property_types=("race", "species", "ancestry", "lineage", "subrace"),
        ),
        "class": class_details(creature, variables, properties),
    }


def class_details(
    creature: Mapping[str, object],
    variables: Mapping[str, object],
    properties: object,
) -> str:
    """Format DiceCloud class containers as class, subclass, and total level."""
    property_values = direct_properties(properties)
    classes = [
        property_value
        for property_value in property_values
        if text(property_value.get("type"), "").lower() == "class"
    ]
    if not classes:
        return identity_detail(
            creature,
            variables,
            properties,
            field_names=("class", "className", "characterClass"),
            property_types=("class", "character class", "subclass"),
        )

    class_entries = []
    for class_property in classes:
        name = clean_class_name(text(class_property.get("name"), ""))
        if not name:
            continue
        level = class_level(class_property, property_values, variables)
        subclass = class_subclass(class_property, property_values)
        label = f"{name} ({subclass})" if subclass else name
        class_entries.append((level, label))

    class_entries.sort(key=lambda entry: (-entry[0], entry[1]))
    return " / ".join(
        f"{label} {level}" if level else label for level, label in class_entries
    )


def clean_class_name(value: str) -> str:
    return value.replace("[Multiclass]", "").strip()


def class_level(
    class_property: Mapping[str, object],
    properties: list[Mapping[str, object]],
    variables: Mapping[str, object],
) -> int:
    for key in ("level", "levels", "classLevel"):
        level = integer(class_property.get(key))
        if level:
            return level

    class_id = class_property.get("_id")
    if isinstance(class_id, str):
        level_properties = [
            property_value
            for property_value in properties
            if text(property_value.get("type"), "") == "classLevel"
            and property_is_descended_from(property_value, class_id, properties)
        ]
        if level_properties:
            maximum_level = max(
                integer(property_value.get("level"))
                for property_value in level_properties
            )
            return maximum_level or len(level_properties)

    name = clean_class_name(text(class_property.get("name"), ""))
    variable_name = "".join(character for character in name if character.isalnum())
    return integer(variables.get(f"{variable_name[:1].lower()}{variable_name[1:]}Level"))


def class_subclass(
    class_property: Mapping[str, object], properties: list[Mapping[str, object]]
) -> str:
    for key in ("subclass", "subclassName", "archetype", "archetypeName"):
        value = text(class_property.get(key), "")
        if value:
            return value

    class_id = class_property.get("_id")
    if not isinstance(class_id, str):
        return ""

    for property_value in properties:
        if not property_is_descended_from(property_value, class_id, properties):
            continue
        tags = property_tags(property_value)
        if "subclass" not in tags and "archetype" not in tags:
            continue
        value = text(property_value.get("name"), "")
        if value:
            return value

    return ""


def property_is_descended_from(
    property_value: Mapping[str, object], ancestor_id: str, properties: list[Mapping[str, object]]
) -> bool:
    properties_by_id = {
        value.get("_id"): value
        for value in properties
        if isinstance(value.get("_id"), str)
    }
    parent_id = property_parent_id(property_value)
    while parent_id is not None:
        if parent_id == ancestor_id:
            return True
        parent = properties_by_id.get(parent_id)
        if parent is None:
            return False
        parent_id = property_parent_id(parent)
    return False


def identity_detail(
    creature: Mapping[str, object],
    variables: Mapping[str, object],
    properties: object,
    *,
    field_names: tuple[str, ...],
    property_types: tuple[str, ...],
) -> str:
    for source in (creature, variables):
        for field_name in field_names:
            value = text(source.get(field_name), "")
            if value:
                return value

    values = []
    property_values = direct_properties(properties)
    for property_value in property_values:
        property_type = text(property_value.get("type"), "").lower().replace("_", " ")
        tags = property_tags(property_value)
        if property_type not in property_types and not any(
            tag in property_types for tag in tags
        ):
            continue
        value = text(property_value.get("name"), "")
        if value and value not in values:
            values.append(value)

    if values:
        return " / ".join(values)

    return identity_from_property_parent(property_values, property_types)


def direct_properties(properties: object) -> list[Mapping[str, object]]:
    if not isinstance(properties, list):
        return []
    return [value for value in properties if isinstance(value, Mapping)]


def property_tags(property_value: Mapping[str, object]) -> tuple[str, ...]:
    tags = property_value.get("tags")
    if not isinstance(tags, list):
        return ()
    return tuple(
        tag.strip().lower().replace("_", " ")
        for tag in tags
        if isinstance(tag, str) and tag.strip()
    )


def identity_from_property_parent(
    properties: list[Mapping[str, object]], property_types: tuple[str, ...]
) -> str:
    """Resolve identity content nested under a Race or Ancestry folder/slot."""
    properties_by_id = {
        property_value.get("_id"): property_value
        for property_value in properties
        if isinstance(property_value.get("_id"), str)
    }

    for property_value in properties:
        parent = properties_by_id.get(property_parent_id(property_value))
        if parent is None or not property_matches_identity(parent, property_types):
            continue

        value = text(property_value.get("name"), "")
        if value and value.lower() not in property_types:
            return value

    return ""


def property_parent_id(property_value: Mapping[str, object]) -> str | None:
    parent_id = property_value.get("parentId")
    if isinstance(parent_id, str):
        return parent_id

    parent = property_value.get("parent")
    if isinstance(parent, Mapping):
        parent_id = parent.get("id")
        if isinstance(parent_id, str):
            return parent_id

    return None


def property_matches_identity(
    property_value: Mapping[str, object], property_types: tuple[str, ...]
) -> bool:
    property_type = text(property_value.get("type"), "").lower().replace("_", " ")
    if property_type in property_types:
        return True

    if any(tag in property_types for tag in property_tags(property_value)):
        return True

    name = text(property_value.get("name"), "").lower()
    return name in property_types


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


def variable_metadata(values: object) -> dict[str, Mapping[str, object]]:
    """Index DiceCloud variable metadata without retaining the raw response."""
    if not isinstance(values, list):
        return {}

    result = {}
    for group in values:
        if not isinstance(group, Mapping):
            continue
        for fallback_name, variable in group.items():
            if not isinstance(variable, Mapping):
                continue
            name = variable.get("variableName", fallback_name)
            if isinstance(name, str) and name:
                result[name] = variable

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


def canonical_stats(
    variables: Mapping[str, object], metadata: Mapping[str, Mapping[str, object]]
) -> dict[str, object]:
    names = (
        "level",
        "hitPoints",
        "maxHitPoints",
        "tempHP",
        "armor",
        "initiative",
        "proficiencyBonus",
        "speed",
        "movementSpeed",
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
    result = {name: variables.get(name) for name in names if name in variables}
    initiative = metadata.get("initiative")
    if initiative is not None:
        result["initiativeProficiency"] = decimal_value(initiative.get("proficiency"))
    return result


def statistic_group(
    variables: Mapping[str, object], names: tuple[str, ...]
) -> dict[str, int | str | None]:
    return {name: display_value(variables.get(name)) for name in names if name in variables}


def skill_entries(values: object) -> list[dict[str, int | float | str | None]]:
    """Project each DiceCloud skill with its declared ability and display metadata."""
    if not isinstance(values, list):
        return []

    entries = []
    seen = set()
    for group in values:
        if not isinstance(group, Mapping):
            continue
        for fallback_name, variable in group.items():
            if not isinstance(variable, Mapping):
                continue
            if text(variable.get("skillType"), "") != "skill" and text(
                variable.get("type"), ""
            ) != "skill":
                continue

            key = text(variable.get("variableName"), text(fallback_name, ""))
            name = text(variable.get("name"), key)
            ability = text(variable.get("ability"), "")
            if (
                not key
                or key in seen
                or key.lower().endswith("save")
                or name.lower().endswith(" save")
                or not ability
            ):
                continue
            seen.add(key)
            value = variable.get("value", variable.get("total"))
            entries.append(
                {
                    "key": key,
                    "name": name,
                    "ability": ability,
                    "value": display_value(value),
                    "proficiency": decimal_value(variable.get("proficiency")),
                    "order": integer(variable.get("order")),
                }
            )

    return entries


def saving_throws(
    variables: Mapping[str, object], metadata: Mapping[str, Mapping[str, object]]
) -> dict[str, dict[str, int | float | str | None]]:
    result = {}
    for ability in ABILITY_NAMES:
        variable_name = f"{ability}Save"
        if variable_name in variables:
            variable = metadata.get(variable_name, {})
            result[ability] = {
                "value": display_value(variables[variable_name]),
                "proficiency": decimal_value(variable.get("proficiency")),
            }
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


def currency(
    variables: Mapping[str, object], payload: Mapping[str, object], properties: object
) -> dict[str, int | str]:
    aliases = {
        "cp": ("cp", "copper", "copperPiece", "copperPieces", "copperCoin", "copperCoins"),
        "sp": ("sp", "silver", "silverPiece", "silverPieces", "silverCoin", "silverCoins"),
        "ep": (
            "ep",
            "electrum",
            "electrumPiece",
            "electrumPieces",
            "electrumCoin",
            "electrumCoins",
        ),
        "gp": ("gp", "gold", "goldPiece", "goldPieces", "goldCoin", "goldCoins"),
        "pp": (
            "pp",
            "platinum",
            "platinumPiece",
            "platinumPieces",
            "platinumCoin",
            "platinumCoins",
        ),
    }
    variable_totals = {
        denomination: integer(next((variables.get(key) for key in keys if key in variables), 0))
        for denomination, keys in aliases.items()
    }
    inventory_totals = inventory_currency(payload, properties)
    totals = {
        denomination: inventory_totals[denomination]
        if inventory_totals[denomination] > 0
        else variable_totals[denomination]
        for denomination in aliases
    }
    totals["gold_value"] = str(
        Decimal(totals["cp"]) / 100
        + Decimal(totals["sp"]) / 10
        + Decimal(totals["ep"]) / 2
        + Decimal(totals["gp"])
        + Decimal(totals["pp"]) * 10
    )
    return totals


def inventory_currency(
    payload: Mapping[str, object], properties: object
) -> dict[str, int]:
    """Sum coin items from the character inventory, including container contents."""
    totals = {denomination: 0 for denomination in ("cp", "sp", "ep", "gp", "pp")}
    roots = [properties]
    inventory_keys = (
        "items",
        "creatureItems",
        "inventory",
        "creatureInventory",
        "containers",
        "creatureContainers",
    )
    roots.extend(payload.get(key) for key in inventory_keys)

    seen_item_ids = set()
    for root in roots:
        for item in nested_mappings(root):
            denomination = currency_denomination(item)
            if denomination is None:
                continue

            item_id = item.get("_id", item.get("id"))
            if item_id is not None:
                if item_id in seen_item_ids:
                    continue
                seen_item_ids.add(item_id)

            totals[denomination] += currency_quantity(item)

    return totals


def nested_mappings(value: object) -> list[Mapping[str, object]]:
    """Return every mapping reachable through a JSON-style DiceCloud value."""
    result = []
    values = [value]
    while values:
        current = values.pop()
        if isinstance(current, Mapping):
            result.append(current)
            values.extend(current.values())
        elif isinstance(current, list):
            values.extend(current)
    return result


def currency_denomination(item: Mapping[str, object]) -> str | None:
    denominations = {
        "cp": ("cp", "copper", "copper coin", "copper coins", "copper piece", "copper pieces"),
        "sp": ("sp", "silver", "silver coin", "silver coins", "silver piece", "silver pieces"),
        "ep": (
            "ep",
            "electrum",
            "electrum coin",
            "electrum coins",
            "electrum piece",
            "electrum pieces",
        ),
        "gp": ("gp", "gold", "gold coin", "gold coins", "gold piece", "gold pieces"),
        "pp": (
            "pp",
            "platinum",
            "platinum coin",
            "platinum coins",
            "platinum piece",
            "platinum pieces",
        ),
    }
    candidates = (item.get("denomination"), item.get("name"), item.get("title"))
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        normalized = candidate.strip().lower()
        for denomination, names in denominations.items():
            if normalized in names:
                return denomination
    return None


def currency_quantity(item: Mapping[str, object]) -> int:
    quantity_keys = ("quantity", "amount", "count", "number", "total")
    for key in quantity_keys:
        if key in item:
            return nested_integer(item[key])

    for key in ("data", "attributes", "system"):
        nested_value = item.get(key)
        if isinstance(nested_value, Mapping):
            nested_quantity = currency_quantity(nested_value)
            if nested_quantity:
                return nested_quantity

    if text(item.get("type"), "").lower() in {"coin", "coins", "currency"}:
        return nested_integer(item.get("value", 0))

    return 0


def nested_integer(value: object) -> int:
    if isinstance(value, Mapping):
        for key in ("value", "total", "amount"):
            if key in value:
                return integer(value[key])
        return 0
    return integer(value)


def integer(value: object) -> int:
    if not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def decimal_value(value: object) -> int | float | None:
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def text(value: object, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default
