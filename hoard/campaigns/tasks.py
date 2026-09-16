"""Background work for authoritative native character effects."""

from celery import shared_task
from django.core.exceptions import ValidationError

from .realtime import notify_campaign_changed
from .services.native import execute_due_delayed_effect


@shared_task(bind=True, max_retries=3)
def run_native_delayed_effect(self, character_id: int, delayed_id: str) -> bool:
    """Run one persisted delayed effect, retrying when a worker wakes early."""
    try:
        result = execute_due_delayed_effect(character_id, delayed_id)
    except ValidationError as error:
        if "not due yet" not in str(error):
            raise
        raise self.retry(countdown=1) from error
    if result is None:
        return False
    notify_campaign_changed(result.character.campaign_id)
    return True
