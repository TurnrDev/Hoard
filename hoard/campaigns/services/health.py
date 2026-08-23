from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Character, HealthTransaction


def post_health_transaction(
    character: Character,
    *,
    reason: str,
    current_hp_delta: int = 0,
    temporary_hp_delta: int = 0,
    current_hp: int | None = None,
    temporary_hp: int | None = None,
    description: str = "",
    created_by=None,
) -> HealthTransaction:
    if reason not in HealthTransaction.Reason.values:
        raise ValidationError("Unknown health transaction reason.")
    with transaction.atomic():
        locked = (
            Character.objects.select_for_update()
            .select_related("campaign")
            .get(pk=character.pk)
        )
        before_current = locked.current_hp
        before_temporary = locked.temporary_hp
        if reason == HealthTransaction.Reason.CORRECTION:
            after_current = before_current if current_hp is None else current_hp
            after_temporary = before_temporary if temporary_hp is None else temporary_hp
        elif (
            reason == HealthTransaction.Reason.DAMAGE
            and current_hp_delta < 0
            and temporary_hp_delta == 0
        ):
            damage = -current_hp_delta
            absorbed = min(before_temporary, damage)
            after_temporary = before_temporary - absorbed
            after_current = max(0, before_current - (damage - absorbed))
        else:
            if current_hp is not None or temporary_hp is not None:
                raise ValidationError("Only corrections may set an absolute HP value.")
            after_current = before_current + current_hp_delta
            after_temporary = before_temporary + temporary_hp_delta
        if after_current < 0 or after_temporary < 0:
            raise ValidationError("Current and temporary HP cannot be negative.")
        if reason == HealthTransaction.Reason.HEALING:
            after_current = min(after_current, locked.max_hp)
        if after_current == before_current and after_temporary == before_temporary:
            raise ValidationError("A health transaction must change HP.")
        posted = HealthTransaction.objects.create(
            campaign=locked.campaign,
            character=locked,
            created_by=created_by,
            reason=reason,
            current_hp_delta=after_current - before_current,
            temporary_hp_delta=after_temporary - before_temporary,
            current_hp_before=before_current,
            current_hp_after=after_current,
            temporary_hp_before=before_temporary,
            temporary_hp_after=after_temporary,
            description=description,
        )
        locked.current_hp = after_current
        locked.temporary_hp = after_temporary
        locked.save(update_fields=("current_hp", "temporary_hp"))
        return posted


def create_health_baseline(
    character: Character, *, created_by=None
) -> HealthTransaction:
    return HealthTransaction.objects.create(
        campaign=character.campaign,
        character=character,
        created_by=created_by,
        reason=HealthTransaction.Reason.BASELINE,
        current_hp_delta=character.current_hp,
        temporary_hp_delta=character.temporary_hp,
        current_hp_before=0,
        current_hp_after=character.current_hp,
        temporary_hp_before=0,
        temporary_hp_after=character.temporary_hp,
        description="Opening health balance",
    )
