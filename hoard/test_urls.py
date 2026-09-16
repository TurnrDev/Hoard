from django.conf import settings
from django.urls import Resolver404, resolve


def test_production_static_files_are_served_before_spa_fallback():
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
    assert settings.STATIC_URL == "/static/"

    try:
        resolve("/static/missing-asset.js")
    except Resolver404:
        pass
    else:
        raise AssertionError("The SPA fallback captured a static asset URL")
