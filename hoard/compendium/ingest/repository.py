"""Retrieve and import an RPG Companion repository."""

from __future__ import annotations

import gzip
import hashlib
import io
import ipaddress
import json
import socket
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from django.core.exceptions import ValidationError

from hoard.compendium.ingest.sources import import_resources, import_source_directory
from hoard.compendium.models import CompendiumRepository, CompendiumSource

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
SUPPORTED_SOURCE_IDENTIFIERS = frozenset({"5e", "5e2024"})
ProgressCallback = Callable[[str, str, int | None, int | None], None]


def import_repository(
    repository: CompendiumRepository,
    *,
    ref: str = "",
    source_identifiers: set[str] | None = None,
    progress: ProgressCallback | None = None,
) -> tuple[int, int, int]:
    """Fetch and import *repository*, preferring its GitHub repository."""
    errors: list[ValidationError] = []
    for url in _archive_urls(repository, ref, errors):
        try:
            with TemporaryDirectory(prefix="hoard-compendium-") as temporary:
                archive = Path(temporary) / "repository.zip"
                _report(progress, "downloading", "Downloading repository archive")
                final_url, checksum = _download(url, archive, progress)
                _report(progress, "extracting", "Extracting repository archive")
                root = _extract(archive, Path(temporary) / "extracted")
                counts = import_directory(
                    root, repository, source_identifiers, progress
                )
                repository.data = {
                    **repository.data,
                    "archive_url": final_url,
                    "archive_sha256": checksum,
                    "archive_ref": ref,
                }
                repository.save(update_fields=("data",))
                return counts
        except ValidationError as error:
            errors.append(error)
    raise errors[-1] if errors else ValidationError("Repository has no import URL.")


def import_directory(
    directory: Path,
    repository: CompendiumRepository,
    source_identifiers: set[str] | None = None,
    progress: ProgressCallback | None = None,
) -> tuple[int, int, int]:
    """Import Hoard-supported sources from either RPG Companion package layout."""
    source_identifiers = _supported_source_identifiers(source_identifiers)
    systems = directory / "systems"
    if systems.is_dir():
        return _import_development_sources(
            systems, repository, source_identifiers, progress
        )
    manifest = directory / "systems.rpg"
    if manifest.is_file():
        return _import_published_sources(
            directory, manifest, repository, source_identifiers, progress
        )
    raise ValidationError(
        "Repository does not contain an RPG Companion systems manifest."
    )


def _import_development_sources(
    systems: Path,
    repository: CompendiumRepository,
    source_identifiers: set[str] | None,
    progress: ProgressCallback | None,
) -> tuple[int, int, int]:
    created = updated = skipped = 0
    imported_identifiers: set[str] = set()
    source_directories = sorted(
        path
        for path in systems.iterdir()
        if path.is_dir() and path.name in source_identifiers
    )
    if not source_directories:
        raise ValidationError(
            "Repository does not provide a supported 5e or 5e2024 source."
        )
    for index, system_directory in enumerate(source_directories, start=1):
        identifier = system_directory.name
        source, _ = CompendiumSource.objects.update_or_create(
            repository=repository,
            identifier=identifier,
            defaults={"name": identifier, "data": {}},
        )
        imported_identifiers.add(identifier)
        _report(
            progress,
            "importing",
            f"Importing {identifier}",
            index,
            len(source_directories),
        )
        counts = import_source_directory(system_directory, source)
        created += counts[0]
        updated += counts[1]
        skipped += counts[2]
    _remove_missing_supported_sources(repository, imported_identifiers)
    return created, updated, skipped


def _import_published_sources(
    directory: Path,
    manifest_path: Path,
    repository: CompendiumRepository,
    source_identifiers: set[str] | None,
    progress: ProgressCallback | None,
) -> tuple[int, int, int]:
    manifest = _read_rpg_json(manifest_path)
    systems = manifest.get("systems") if isinstance(manifest, dict) else None
    if not isinstance(systems, list):
        raise ValidationError("RPG Companion systems manifest is invalid.")

    created = updated = skipped = 0
    imported_identifiers: set[str] = set()
    supported_systems = [
        system
        for system in systems
        if isinstance(system, dict)
        and isinstance(system.get("id"), str)
        and system["id"] in source_identifiers
    ]
    if not supported_systems:
        raise ValidationError(
            "Repository does not provide a supported 5e or 5e2024 source."
        )
    for index, system in enumerate(supported_systems, start=1):
        if not isinstance(system, dict):
            continue
        identifier = system.get("id")
        relative_path = system.get("path")
        if (
            not isinstance(identifier, str)
            or not identifier
            or not isinstance(relative_path, str)
        ):
            continue
        system_directory = _safe_relative_directory(directory, relative_path)
        source, _ = CompendiumSource.objects.update_or_create(
            repository=repository,
            identifier=identifier,
            defaults={
                "name": _system_name(system, identifier),
                "data": {"manifest": system},
            },
        )
        imported_identifiers.add(identifier)
        _report(
            progress,
            "importing",
            f"Importing {identifier}",
            index,
            len(supported_systems),
        )
        resources = _read_published_resources(system_directory / "resources.rpg.gzip")
        counts = import_resources(resources, source)
        created += counts[0]
        updated += counts[1]
        skipped += counts[2]
    _remove_missing_supported_sources(repository, imported_identifiers)
    return created, updated, skipped


def _supported_source_identifiers(
    requested_identifiers: set[str] | None,
) -> frozenset[str]:
    if requested_identifiers is None:
        return SUPPORTED_SOURCE_IDENTIFIERS
    return SUPPORTED_SOURCE_IDENTIFIERS.intersection(requested_identifiers)


def _remove_missing_supported_sources(
    repository: CompendiumRepository, imported_identifiers: set[str]
) -> None:
    repository.sources.filter(identifier__in=SUPPORTED_SOURCE_IDENTIFIERS).exclude(
        identifier__in=imported_identifiers
    ).delete()


def _system_name(system: dict[str, object], fallback: str) -> str:
    name = system.get("name")
    return name if isinstance(name, str) and name else fallback


def _safe_relative_directory(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_dir():
        raise ValidationError("RPG Companion system path is invalid.")
    return candidate


def _read_published_resources(path: Path) -> list[tuple[dict[str, object], str]]:
    if not path.is_file():
        raise ValidationError(
            "RPG Companion system does not include a resource bundle."
        )
    payload = _read_gzip(path.read_bytes(), "RPG Companion resource bundle")
    try:
        archive = tarfile.open(fileobj=io.BytesIO(payload), mode="r:")
    except tarfile.TarError as error:
        raise ValidationError("RPG Companion resource bundle is invalid.") from error
    with archive:
        members = archive.getmembers()
        if (
            len(members) > MAX_ARCHIVE_ENTRIES
            or sum(member.size for member in members) > MAX_UNCOMPRESSED_BYTES
        ):
            raise ValidationError(
                "RPG Companion resource bundle exceeds extraction limits."
            )
        resources: list[tuple[dict[str, object], str]] = []
        for member in members:
            if member.issym() or member.islnk() or not _safe_member_name(member.name):
                raise ValidationError(
                    "RPG Companion resource bundle contains an unsafe path."
                )
            if not member.isfile():
                continue
            content = archive.extractfile(member)
            if content is None:
                continue
            try:
                resource = json.loads(
                    _read_gzip(content.read(), "RPG Companion resource")
                )
            except json.JSONDecodeError as error:
                raise ValidationError("RPG Companion resource is invalid.") from error
            if isinstance(resource, dict):
                resources.append((resource, Path(member.name).stem))
    return resources


def _safe_member_name(name: str) -> bool:
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts


def _read_rpg_json(path: Path) -> object:
    try:
        return json.loads(_read_gzip(path.read_bytes(), "RPG Companion manifest"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError("RPG Companion systems manifest is invalid.") from error


def _read_gzip(payload: bytes, label: str) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed:
            data = compressed.read(MAX_UNCOMPRESSED_BYTES + 1)
    except OSError as error:
        raise ValidationError(f"{label} is not valid gzip data.") from error
    if len(data) > MAX_UNCOMPRESSED_BYTES:
        raise ValidationError(f"{label} exceeds extraction limits.")
    return data


def _archive_urls(
    repository: CompendiumRepository, ref: str, errors: list[ValidationError]
) -> list[str]:
    urls: list[str] = []
    if repository.github_repository:
        try:
            urls.append(_github_archive_url(repository.github_repository, ref))
        except ValidationError as error:
            errors.append(error)
    if repository.repository_url and repository.repository_url not in urls:
        urls.append(repository.repository_url)
    return urls


def _github_archive_url(repository: str, ref: str) -> str:
    """Resolve a GitHub repository's archive through GitHub's API."""
    parts = repository.strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise ValidationError("GitHub repository must be in owner/repository form.")
    owner, name = parts
    api_url = f"https://api.github.com/repos/{owner}/{name}"
    _validate_public_https(api_url)
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Hoard Compendium importer",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError("Could not resolve the GitHub repository.") from error
    if not isinstance(payload, dict):
        raise ValidationError("GitHub returned an invalid repository response.")
    branch = ref or payload.get("default_branch")
    if not isinstance(branch, str) or not branch:
        raise ValidationError("GitHub did not provide a default branch.")
    return f"https://api.github.com/repos/{owner}/{name}/zipball/{branch}"


def _download(
    url: str, destination: Path, progress: ProgressCallback | None
) -> tuple[str, str]:
    _validate_public_https(url)
    request = Request(url, headers={"User-Agent": "Hoard Compendium importer"})
    try:
        with urlopen(request, timeout=20) as response:
            _validate_public_https(response.url)
            checksum = hashlib.sha256()
            size = 0
            content_length = response.headers.get("Content-Length")
            total = (
                int(content_length)
                if content_length and content_length.isdigit()
                else None
            )
            with destination.open("wb") as output:
                while chunk := response.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_ARCHIVE_BYTES:
                        raise ValidationError(
                            "Repository archive exceeds the 50 MiB limit."
                        )
                    checksum.update(chunk)
                    output.write(chunk)
                    _report(
                        progress,
                        "downloading",
                        "Downloading repository archive",
                        size,
                        total,
                    )
    except OSError as error:
        raise ValidationError("Could not download repository archive.") from error
    return response.url, checksum.hexdigest()


def _extract(archive: Path, destination: Path) -> Path:
    destination.mkdir()
    try:
        with ZipFile(archive) as bundle:
            members = bundle.infolist()
            if (
                len(members) > MAX_ARCHIVE_ENTRIES
                or sum(member.file_size for member in members) > MAX_UNCOMPRESSED_BYTES
            ):
                raise ValidationError("Repository archive exceeds extraction limits.")
            root = destination.resolve()
            for member in members:
                target = (root / member.filename).resolve()
                is_symlink = member.external_attr >> 16 & 0o170000 == 0o120000
                if not target.is_relative_to(root) or is_symlink:
                    raise ValidationError("Repository archive contains an unsafe path.")
            bundle.extractall(destination)
    except BadZipFile as error:
        raise ValidationError("Repository must provide a ZIP archive.") from error
    roots = [path for path in destination.iterdir() if path.is_dir()]
    return roots[0] if len(roots) == 1 else destination


def _validate_public_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValidationError("Repository URLs must use public HTTPS.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ValidationError("Repository host could not be resolved.") from error
    if any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValidationError("Repository host must resolve to public addresses.")


def _report(
    progress: ProgressCallback | None,
    stage: str,
    message: str,
    current: int | None = None,
    total: int | None = None,
) -> None:
    if progress is not None:
        progress(stage, message, current, total)
