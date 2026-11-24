"""
ASGI config for hoard project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hoard.settings")

django_asgi_app = get_asgi_application()

from hoard.routing import websocket_urlpatterns  # noqa: E402
from hoard.staticfiles import serve_static_files  # noqa: E402

http_application = django_asgi_app
if not settings.DEBUG:
    http_application = serve_static_files(django_asgi_app, settings.STATIC_ROOT)

application = ProtocolTypeRouter(
    {
        "http": http_application,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
