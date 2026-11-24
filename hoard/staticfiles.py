from __future__ import annotations

import re
from pathlib import Path

from asgiref.typing import ASGIApplication
from blacknoise import BlackNoise


def is_immutable_asset(path: str) -> bool:
    """Cache Vite's content-hashed assets permanently, but not stable filenames."""
    return bool(re.search(r"/assets/[^/]+-[A-Za-z0-9_-]{8,}\.[^/]+$", path))


def serve_static_files(application: ASGIApplication, directory: Path) -> BlackNoise:
    """Serve collected production assets without changing the WebSocket app."""
    wrapped = BlackNoise(application, immutable_file_test=is_immutable_asset)
    wrapped.add(directory, "/static/")
    return wrapped
