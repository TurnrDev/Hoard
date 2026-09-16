from __future__ import annotations

import tomllib

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def spa(request: HttpRequest) -> HttpResponse:
    """Serve the Vite SPA entry point in production."""
    return render(request, "hoard/index.html", {"vite_dev_mode": settings.DEBUG})


def project_version() -> str:
    """Return the canonical release version from project metadata."""
    metadata = tomllib.loads((settings.BASE_DIR / "pyproject.toml").read_text())

    return str(metadata["project"]["version"])


def release_manifest(request: HttpRequest) -> JsonResponse:
    """Expose the deployed release version without allowing intermediary caching."""
    response = JsonResponse({"version": project_version()})
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"

    return response
