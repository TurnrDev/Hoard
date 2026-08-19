from __future__ import annotations

from django.conf import settings
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse


def frontend(request: HttpRequest) -> HttpResponse:
    """Serve the Vite SPA entry point in production."""
    return render(request, "frontend/index.html", {"vite_dev_mode": settings.DEBUG})
