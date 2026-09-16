from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import CampaignContext, Character, CharacterCondition, HealthTransaction
from .native import execute_character_event


class CharacterHealthService:
    """Records authoritative character health transactions and balances."""

    def post(
        self,
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
        """Apply one validated health change and return its ledger record."""
        return post_health_transaction(
            character,
            reason=reason,
            current_hp_delta=current_hp_delta,
            temporary_hp_delta=temporary_hp_delta,
            current_hp=current_hp,
            temporary_hp=temporary_hp,
            description=description,
            created_by=created_by,
        )

    def create_baseline(
        self, character: Character, *, created_by=None
    ) -> HealthTransaction:
        """Create the initial health ledger record for a character."""
        return create_health_baseline(character, created_by=created_by)


def stabilize_character(
    character: Character,
    *,
    created_by: CampaignContext,
) -> HealthTransaction:
    """Restore a dying or dead character to one HP and leave them prone."""
    with transaction.atomic():
        locked = Character.objects.select_for_update().get(pk=character.pk)
        if locked.current_hp != 0 and not locked.is_dead:
            raise ValidationError(
                "Only a character making death saves or marked dead can be stabilized."
            )
        if locked.current_hp != 0:
            raise ValidationError("A dead character must be at 0 HP to be stabilized.")

        posted = post_health_transaction(
            locked,
            reason=HealthTransaction.Reason.HEALING,
            current_hp_delta=1,
            description="Stabilized at 1 HP",
            created_by=created_by,
        )

        if not locked.conditions.filter(
            identifier=CharacterCondition.Identifier.PRONE
        ).exists():
            from .combat import set_character_condition

            set_character_condition(
                created_by,
                locked.pk,
                identifier=CharacterCondition.Identifier.PRONE,
                source="Stabilization",
                duration="Until the character stands",
                exhaustion_level=None,
            )

        return posted


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
        execute_character_event(
            locked,
            "set_current_hp",
            {
                "reason": reason,
                "current_hp": after_current,
                "temporary_hp": after_temporary,
            },
            created_by=created_by,
            effects={
                "type": "sequence",
                "effects": [
                    {
                        "type": "setStat",
                        "stat": "current_hp",
                        "new_value": {
                            "type": "stat",
                            "stat": "$event.current_hp",
                        },
                        "aggregation_type": "set",
                    },
                    {
                        "type": "setStat",
                        "stat": "hoard_temporary_hp",
                        "new_value": {
                            "type": "stat",
                            "stat": "$event.temporary_hp",
                        },
                        "aggregation_type": "set",
                    },
                    *(
                        [
                            {
                                "type": "setStat",
                                "stat": f"death_saving_throws_{kind}_{index}",
                                "new_value": {"type": "constant", "value": False},
                                "aggregation_type": "set",
                            }
                            for kind in ("success", "failure")
                            for index in range(1, 4)
                        ]
                        + [
                            {
                                "type": "setStat",
                                "stat": "hoard_is_dead",
                                "new_value": {"type": "constant", "value": False},
                                "aggregation_type": "set",
                            }
                        ]
                        if after_current > 0
                        else []
                    ),
                ],
            },
        )
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
