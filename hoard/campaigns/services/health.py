from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Character, Encounter, HealthTransaction


def adjust_health(
    character: Character,
    *,
    reason: str,
    amount: int = 0,
    current_hp: int | None = None,
    temporary_hp: int | None = None,
    description: str = "",
    created_by=None,
) -> Character:
    """Apply one authoritative character health change."""
    with transaction.atomic():
        locked = Character.objects.select_for_update().get(pk=character.pk)
        before_current = locked.current_hp
        before_temporary = locked.temporary_hp

        if reason == "damage":
            if amount <= 0:
                raise ValidationError("Damage must be greater than zero.")
            absorbed = min(locked.temporary_hp, amount)
            locked.temporary_hp -= absorbed
            locked.current_hp = max(0, locked.current_hp - (amount - absorbed))
        elif reason == "healing":
            if amount <= 0:
                raise ValidationError("Healing must be greater than zero.")
            locked.current_hp = min(locked.max_hp, locked.current_hp + amount)
        elif reason == "temporary":
            if amount == 0:
                raise ValidationError("Temporary HP must change.")
            locked.temporary_hp = max(0, locked.temporary_hp + amount)
        elif reason == "correction":
            if current_hp is None and temporary_hp is None:
                raise ValidationError("A correction must set current or temporary HP.")
            if current_hp is not None:
                locked.current_hp = current_hp
            if temporary_hp is not None:
                locked.temporary_hp = temporary_hp
        else:
            raise ValidationError("Unknown health change.")

        HealthTransaction.objects.create(
            campaign=locked.campaign,
            character=locked,
            created_by=created_by,
            reason=reason,
            current_hp_before=before_current,
            current_hp_after=locked.current_hp,
            temporary_hp_before=before_temporary,
            temporary_hp_after=locked.temporary_hp,
            description=description,
        )
        locked.save(update_fields=("current_hp", "temporary_hp"))
        return locked


def take_rest(
    character: Character,
    *,
    kind: str,
    regained_hp: int = 0,
    created_by=None,
) -> Character:
    """Apply the agreed short- and long-rest health rules."""
    with transaction.atomic():
        locked = Character.objects.select_for_update().get(pk=character.pk)
        if Encounter.objects.filter(
            campaign_id=locked.campaign_id,
            is_active=True,
        ).exists():
            raise ValidationError("You cannot rest during combat.")

        before_current = locked.current_hp
        before_temporary = locked.temporary_hp

        if kind == "long":
            locked.current_hp = locked.max_hp
            reason = HealthTransaction.Reason.LONG_REST
        elif kind == "short":
            if regained_hp < 0:
                raise ValidationError("Short-rest recovery cannot be negative.")
            locked.current_hp = min(locked.max_hp, locked.current_hp + regained_hp)
            reason = HealthTransaction.Reason.SHORT_REST
        else:
            raise ValidationError("Unknown rest type.")

        locked.temporary_hp = 0
        HealthTransaction.objects.create(
            campaign=locked.campaign,
            character=locked,
            created_by=created_by,
            reason=reason,
            current_hp_before=before_current,
            current_hp_after=locked.current_hp,
            temporary_hp_before=before_temporary,
            temporary_hp_after=0,
        )
        locked.save(update_fields=("current_hp", "temporary_hp"))
        return locked
