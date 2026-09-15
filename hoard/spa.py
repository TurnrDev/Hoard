from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def spa(request: HttpRequest) -> HttpResponse:
    """Serve the Vite SPA entry point in production."""
    return render(request, "hoard/index.html", {"vite_dev_mode": settings.DEBUG})
