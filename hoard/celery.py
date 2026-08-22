"""Celery application for Hoard background jobs."""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hoard.settings")

app = Celery("hoard")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
