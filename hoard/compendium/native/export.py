"""Create RPG Companion-compatible packages for campaign custom content."""

from __future__ import annotations

import gzip
import io
import json
import re
import tarfile
import zipfile
from dataclasses import dataclass

from hoard.campaigns.models import Campaign


@dataclass(frozen=True)
class NativeResourceExport:
    """An in-memory published RPG Companion resource archive."""

    filename: str
    content: bytes
    resource_count: int


@dataclass(frozen=True)
class NativeRepositoryExport:
    """A complete published repository containing Hoard's system overlay."""

    filename: str
    content: bytes
    resource_count: int


def export_campaign_resources(campaign: Campaign) -> NativeResourceExport:
    """Package campaign custom entries like an official resources.rpg.gzip file."""
    entries = (
        campaign.compendium_repositories.all()
        .values_list("sources__entries__source_identifier", "sources__entries__data")
        .order_by("sources__entries__kind", "sources__entries__source_identifier")
    )
    resources = [
        (str(identifier), data)
        for identifier, data in entries
        if identifier and isinstance(data, dict) and data.get("resource_id")
    ]
    archive_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=archive_buffer, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w|") as archive:
            directory = tarfile.TarInfo("resources/")
            directory.type = tarfile.DIRTYPE
            directory.mode = 0o755
            directory.mtime = 0
            archive.addfile(directory)
            for position, (identifier, resource) in enumerate(resources):
                safe_identifier = re.sub(r"[^a-zA-Z0-9_.-]+", "_", identifier)
                inner = gzip.compress(
                    json.dumps(
                        resource,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode(),
                    mtime=0,
                )
                info = tarfile.TarInfo(
                    f"resources/{safe_identifier or f'custom_{position}'}.rpg"
                )
                info.size = len(inner)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(inner))
    system_id = campaign.native_system_id or "5e"
    return NativeResourceExport(
        filename=f"hoard-{campaign.pk}-{system_id}-resources.rpg.gzip",
        content=archive_buffer.getvalue(),
        resource_count=len(resources),
    )


def export_campaign_repository(
    campaign: Campaign,
    definition: dict[str, object],
) -> NativeRepositoryExport:
    """Build a directly importable published repository for one campaign lineage."""
    system_id = campaign.native_system_id or "5e"
    resources = export_campaign_resources(campaign)
    version = str(definition.get("version") or "0.0.0")
    manifest = {
        "systems": [
            {
                "id": system_id,
                "name": str(definition.get("name") or system_id),
                "abbreviation": str(definition.get("abbreviation") or system_id),
                "path": system_id,
                "version": version,
                "min_app_version": str(definition.get("min_app_version") or ""),
            }
        ]
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "systems.rpg",
            gzip.compress(
                json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode(),
                mtime=0,
            ),
        )
        archive.writestr(
            f"{system_id}/system.rpg",
            gzip.compress(
                json.dumps(
                    definition,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode(),
                mtime=0,
            ),
        )
        archive.writestr(
            f"{system_id}/resources.rpg.gzip",
            resources.content,
        )
    return NativeRepositoryExport(
        filename=f"hoard-{campaign.pk}-{system_id}-repository.zip",
        content=buffer.getvalue(),
        resource_count=resources.resource_count,
    )
