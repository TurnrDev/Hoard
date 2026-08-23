from django.urls import path

from hoard.campaigns.consumers import ContextConsumer, InviteConsumer, UserConsumer

websocket_urlpatterns = [
    path("ws/user/", UserConsumer.as_asgi()),
    path("ws/contexts/<int:context_id>/", ContextConsumer.as_asgi()),
    path("ws/invites/<str:token>/", InviteConsumer.as_asgi()),
]
