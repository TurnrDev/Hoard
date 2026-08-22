"""Read the RPG Companion community repository directory."""

from __future__ import annotations

import json
from urllib.request import urlopen

from django.core.exceptions import ValidationError
from django.utils.text import slugify

from hoard.compendium.models import CompendiumRepository

REGISTRY_URL = (
    "https://raw.githubusercontent.com/blastervla/"
    "rpg-companion-community-registry/master/registry.json"
)
SUPPORTED_TAGS = frozenset({"5e", "5e2024"})


def sync_registry() -> dict[str, CompendiumRepository]:
    """Fetch the community directory and upsert its repository records."""
    try:
        with urlopen(REGISTRY_URL, timeout=20) as response:
            rows = json.load(response)
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(
            "The RPG Companion community registry is unavailable."
        ) from error
    if not isinstance(rows, list):
        raise ValidationError("The RPG Companion community registry is malformed.")

    repositories: dict[str, CompendiumRepository] = {}
    for row in rows:
        repository = _upsert_record(row)
        if repository is not None:
            repositories[repository.identifier] = repository
    return repositories


def _upsert_record(row: object) -> CompendiumRepository | None:
    if not isinstance(row, dict):
        return None
    name = row.get("name")
    if not isinstance(name, str):
        return None
    tags = [tag for tag in row.get("tags", []) if isinstance(tag, str)]
    if not SUPPORTED_TAGS.intersection(tags):
        return None
    identifier = _identifier(row, name)
    if not identifier:
        return None
    repository, _ = CompendiumRepository.objects.update_or_create(
        identifier=identifier,
        defaults={
            "name": name,
            "description": _text(row, "description"),
            "tags": tags,
            "repository_url": _text(row, "repo_url"),
            "github_repository": _text(row, "github_repo"),
            "data": row,
        },
    )
    return repository


def _text(row: dict[str, object], name: str) -> str:
    value = row.get(name)
    return value if isinstance(value, str) else ""


def _identifier(row: dict[str, object], name: str) -> str:
    """Use the registry ID when present, otherwise a stable repository identity."""
    identifier = _text(row, "id")
    if identifier:
        return identifier
    github_repository = _text(row, "github_repo")
    if github_repository:
        return f"github:{github_repository.lower()}"
    repository_url = _text(row, "repo_url")
    if repository_url:
        return f"url:{repository_url.rstrip('/').lower()}"
    return f"name:{slugify(name)}" if slugify(name) else ""
