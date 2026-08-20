from django.urls import path

from hoard.campaigns.consumers import CampaignConsumer

websocket_urlpatterns = [
    path("ws/campaigns/<int:campaign_id>/", CampaignConsumer.as_asgi()),
]
