from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    Campaign,
    CampaignContext,
    Character,
    CharacterCondition,
    CombatantCondition,
    CompendiumEntry,
    ConditionEvent,
    Encounter,
    EncounterCombatant,
)


def require_game_master(context: CampaignContext) -> None:
    """Reject encounter mutations from player contexts."""
    if context.kind != CampaignContext.Kind.GM:
        raise PermissionError("Only a game master may manage combat.")


def active_encounter(context: CampaignContext) -> Encounter:
    """Return the active encounter for the context's campaign."""
    encounter = Encounter.objects.filter(
        campaign_id=context.campaign_id,
        is_active=True,
    ).first()
    if encounter is None:
        raise ValidationError("There is no active encounter.")

    return encounter


@transaction.atomic
def start_encounter(context: CampaignContext) -> Encounter:
    """Start combat and enrol every active player character at initiative zero."""
    require_game_master(context)
    campaign = Campaign.objects.select_for_update().get(pk=context.campaign_id)
    existing = Encounter.objects.filter(campaign=campaign, is_active=True).first()
    if existing is not None:
        return existing

    encounter = Encounter.objects.create(campaign=campaign, started_by=context)
    player_characters = campaign.characters.filter(
        context__isnull=False,
        is_active=True,
        is_archived=False,
    ).order_by("name", "pk")
    EncounterCombatant.objects.bulk_create(
        [
            EncounterCombatant(
                encounter=encounter,
                character=character,
                name=character.name,
                initiative=0,
                show_hp_bar=True,
                show_hp_numbers=True,
            )
            for character in player_characters
        ]
    )

    return encounter


def finish_encounter(context: CampaignContext) -> Encounter:
    """Finish the active encounter while retaining it as campaign history."""
    require_game_master(context)
    encounter = active_encounter(context)
    encounter.finish()

    return encounter


def add_character_combatant(
    context: CampaignContext,
    character_id: int,
    initiative: int,
    show_hp_bar: bool = False,
    show_hp_numbers: bool = False,
) -> EncounterCombatant:
    """Add an existing campaign character to the active encounter."""
    require_game_master(context)
    encounter = active_encounter(context)
    character = Character.objects.filter(
        pk=character_id,
        campaign_id=context.campaign_id,
        is_active=True,
        is_archived=False,
    ).first()
    if character is None:
        raise ValidationError("Character not found in this campaign.")

    combatant = EncounterCombatant.objects.create(
        encounter=encounter,
        character=character,
        name=character.name,
        initiative=initiative,
        show_hp_bar=character.is_player_character or show_hp_bar,
        show_hp_numbers=character.is_player_character or show_hp_numbers,
    )

    return combatant


def add_encounter_combatant(
    context: CampaignContext,
    *,
    name: str,
    creature_entry_id: int | None,
    initiative: int,
    current_hp: int | None,
    max_hp: int | None,
    show_hp_bar: bool,
    show_hp_numbers: bool,
) -> EncounterCombatant:
    """Add a Compendium-backed or encounter-only combatant."""
    require_game_master(context)
    encounter = active_encounter(context)
    creature_entry = None
    if creature_entry_id is not None:
        creature_entry = (
            CompendiumEntry.objects.select_related("source__repository")
            .filter(
                pk=creature_entry_id,
                kind=CompendiumEntry.Kind.MONSTER,
            )
            .filter(source__repository__campaign_id__in=(None, context.campaign_id))
            .first()
        )
        if creature_entry is None:
            raise ValidationError("Creature not found in this campaign's Compendium.")

    return EncounterCombatant.objects.create(
        encounter=encounter,
        name=name.strip(),
        creature_entry=creature_entry,
        initiative=initiative,
        current_hp=current_hp,
        max_hp=max_hp,
        show_hp_bar=show_hp_bar,
        show_hp_numbers=show_hp_numbers,
    )


def encounter_combatant(
    context: CampaignContext,
    combatant_id: int,
) -> EncounterCombatant:
    """Return a combatant from the active encounter."""
    combatant = (
        EncounterCombatant.objects.select_related("character", "encounter")
        .filter(
            pk=combatant_id,
            encounter__campaign_id=context.campaign_id,
            encounter__is_active=True,
        )
        .first()
    )
    if combatant is None:
        raise ValidationError("Combatant not found in the active encounter.")

    return combatant


def update_combatant(
    context: CampaignContext,
    combatant_id: int,
    fields: dict[str, object],
) -> EncounterCombatant:
    """Update initiative, generic health, or player-facing health visibility."""
    require_game_master(context)
    combatant = encounter_combatant(context, combatant_id)
    allowed = {
        "name",
        "initiative",
        "current_hp",
        "max_hp",
        "show_hp_bar",
        "show_hp_numbers",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}

    if combatant.character_id and {"name", "current_hp", "max_hp"} & updates.keys():
        raise ValidationError(
            "Linked character identity and health must be changed on the character sheet."
        )
    if (
        combatant.character_id
        and combatant.character.is_player_character
        and {
            "show_hp_bar",
            "show_hp_numbers",
        }
        & updates.keys()
    ):
        raise ValidationError("Player character health is always visible in combat.")

    for field, value in updates.items():
        setattr(combatant, field, value)
    if updates:
        combatant.save(update_fields=tuple(updates))

    return combatant


def set_current_combatant(
    context: CampaignContext,
    combatant_id: int | None,
) -> Encounter:
    """Set the active encounter's current initiative entry, or clear it."""
    require_game_master(context)
    encounter = active_encounter(context)

    if combatant_id is None:
        encounter.current_combatant = None
    else:
        combatant = encounter_combatant(context, combatant_id)
        encounter.current_combatant = combatant

    encounter.save(update_fields=("current_combatant",))

    return encounter


@transaction.atomic
def reorder_combatants(
    context: CampaignContext,
    combatant_ids: list[int],
) -> list[EncounterCombatant]:
    """Reassign initiative values to persist the supplied combatant order."""
    require_game_master(context)
    encounter = active_encounter(context)
    combatants = list(
        encounter.combatants.select_for_update().filter(pk__in=combatant_ids)
    )
    combatants_by_id = {combatant.pk: combatant for combatant in combatants}
    existing_ids = set(encounter.combatants.values_list("pk", flat=True))

    if set(combatant_ids) != existing_ids:
        raise ValidationError("Combatant order must include every initiative entry.")

    initiatives = sorted(
        (combatant.initiative for combatant in combatants),
        reverse=True,
    )
    initiatives_are_unique = len(initiatives) == len(set(initiatives))
    if not initiatives_are_unique:
        highest = min(100, max(max(initiatives), -100 + len(initiatives) - 1))
        initiatives = [highest - index for index in range(len(initiatives))]

    ordered_combatants = [combatants_by_id[combatant_id] for combatant_id in combatant_ids]
    changed_combatants = []
    for combatant, initiative in zip(ordered_combatants, initiatives, strict=True):
        if combatant.initiative == initiative:
            continue

        combatant.initiative = initiative
        changed_combatants.append(combatant)

    if changed_combatants:
        EncounterCombatant.objects.bulk_update(changed_combatants, ("initiative",))

    return ordered_combatants


@transaction.atomic
def remove_combatant(context: CampaignContext, combatant_id: int) -> None:
    """Remove a combatant from the active encounter."""
    require_game_master(context)
    combatant = encounter_combatant(context, combatant_id)
    if not combatant.character_id:
        for condition in combatant.conditions.all():
            post_condition_event(
                context,
                condition,
                ConditionEvent.Action.REMOVED,
                before=condition_snapshot(condition),
                after=None,
                combatant=combatant,
            )
    combatant.delete()


def condition_character(
    context: CampaignContext,
    character_id: int,
) -> Character:
    """Return a condition-editable character for a GM or its owning player."""
    character = (
        Character.objects.select_for_update(of=("self",))
        .select_related("context")
        .filter(
            pk=character_id,
            campaign_id=context.campaign_id,
            is_archived=False,
        )
        .first()
    )
    if character is None:
        raise ValidationError("Character not found in this campaign.")

    is_owner = bool(
        character.context_id and character.context.user_id == context.user_id
    )
    if context.kind != CampaignContext.Kind.GM and not is_owner:
        raise PermissionError("You cannot change conditions on that character.")

    return character


def condition_snapshot(
    condition: CharacterCondition | CombatantCondition,
) -> dict[str, object]:
    """Return the rule-relevant state of one condition cause."""
    return {
        "source": condition.source,
        "duration": condition.duration,
        "exhaustion_level": condition.exhaustion_level,
    }


def post_condition_event(
    context: CampaignContext,
    condition: CharacterCondition | CombatantCondition,
    action: str,
    *,
    before: dict[str, object] | None,
    after: dict[str, object] | None,
    character: Character | None = None,
    combatant: EncounterCombatant | None = None,
) -> ConditionEvent:
    """Record an immutable condition change with a stable target snapshot."""
    target_character = character
    if target_character is None and isinstance(condition, CharacterCondition):
        target_character = condition.character

    target_combatant = combatant
    if target_combatant is None and isinstance(condition, CombatantCondition):
        target_combatant = condition.combatant

    target_name = (
        target_character.name
        if target_character is not None
        else target_combatant.display_name
    )
    encounter = target_combatant.encounter if target_combatant is not None else None

    return ConditionEvent.objects.create(
        campaign=context.campaign,
        created_by=context,
        character=target_character,
        encounter=encounter,
        combatant=target_combatant,
        condition_instance_id=condition.pk,
        target_name=target_name,
        identifier=condition.identifier,
        action=action,
        before=before,
        after=after,
    )


@transaction.atomic
def set_character_condition(
    context: CampaignContext,
    character_id: int,
    *,
    condition_id: int | None = None,
    identifier: str,
    source: str,
    duration: str,
    exhaustion_level: int | None,
    combatant: EncounterCombatant | None = None,
) -> CharacterCondition:
    """Apply a condition cause or update one existing cause on a character."""
    character = condition_character(context, character_id)
    condition = None
    if condition_id is not None:
        condition = character.conditions.filter(pk=condition_id).first()
        if condition is None:
            raise ValidationError("Condition cause not found on this character.")
        if condition.identifier != identifier:
            raise ValidationError("A condition cause cannot change condition type.")
    elif identifier == CharacterCondition.Identifier.EXHAUSTION:
        condition = character.conditions.filter(identifier=identifier).first()

    before = condition_snapshot(condition) if condition is not None else None
    action = ConditionEvent.Action.UPDATED
    if condition is None:
        condition = CharacterCondition(character=character, identifier=identifier)
        action = ConditionEvent.Action.APPLIED

    condition.source = source.strip()
    condition.duration = duration.strip()
    condition.exhaustion_level = exhaustion_level
    condition.save()
    after = condition_snapshot(condition)

    if before != after:
        post_condition_event(
            context,
            condition,
            action,
            before=before,
            after=after,
            character=character,
            combatant=combatant,
        )

    return condition


@transaction.atomic
def remove_character_condition(
    context: CampaignContext,
    character_id: int,
    *,
    condition_id: int | None = None,
    identifier: str | None = None,
    combatant: EncounterCombatant | None = None,
) -> None:
    """Remove one or every cause of a persistent character condition."""
    if (condition_id is None) == (identifier is None):
        raise ValidationError("Supply either condition_id or identifier.")

    character = condition_character(context, character_id)
    conditions = character.conditions.all()
    if condition_id is not None:
        conditions = conditions.filter(pk=condition_id)
    elif identifier is not None:
        conditions = conditions.filter(identifier=identifier)

    removed = list(conditions)
    if not removed:
        raise ValidationError("Condition not found on this character.")

    for condition in removed:
        post_condition_event(
            context,
            condition,
            ConditionEvent.Action.REMOVED,
            before=condition_snapshot(condition),
            after=None,
            character=character,
            combatant=combatant,
        )
    conditions.delete()


@transaction.atomic
def set_combatant_condition(
    context: CampaignContext,
    combatant_id: int,
    *,
    condition_id: int | None = None,
    identifier: str,
    source: str,
    duration: str,
    exhaustion_level: int | None,
) -> CharacterCondition | CombatantCondition:
    """Apply or update a condition cause through an initiative entry."""
    require_game_master(context)
    combatant = encounter_combatant(context, combatant_id)
    if combatant.character_id:
        return set_character_condition(
            context,
            combatant.character_id,
            condition_id=condition_id,
            identifier=identifier,
            source=source,
            duration=duration,
            exhaustion_level=exhaustion_level,
            combatant=combatant,
        )

    condition = None
    if condition_id is not None:
        condition = combatant.conditions.filter(pk=condition_id).first()
        if condition is None:
            raise ValidationError("Condition cause not found on this combatant.")
        if condition.identifier != identifier:
            raise ValidationError("A condition cause cannot change condition type.")
    elif identifier == CombatantCondition.Identifier.EXHAUSTION:
        condition = combatant.conditions.filter(identifier=identifier).first()

    before = condition_snapshot(condition) if condition is not None else None
    action = ConditionEvent.Action.UPDATED
    if condition is None:
        condition = CombatantCondition(combatant=combatant, identifier=identifier)
        action = ConditionEvent.Action.APPLIED

    condition.source = source.strip()
    condition.duration = duration.strip()
    condition.exhaustion_level = exhaustion_level
    condition.save()
    after = condition_snapshot(condition)

    if before != after:
        post_condition_event(
            context,
            condition,
            action,
            before=before,
            after=after,
            combatant=combatant,
        )

    return condition


@transaction.atomic
def remove_combatant_condition(
    context: CampaignContext,
    combatant_id: int,
    *,
    condition_id: int | None = None,
    identifier: str | None = None,
) -> None:
    """Remove one or every cause of a condition through an initiative entry."""
    if (condition_id is None) == (identifier is None):
        raise ValidationError("Supply either condition_id or identifier.")

    require_game_master(context)
    combatant = encounter_combatant(context, combatant_id)
    if combatant.character_id:
        remove_character_condition(
            context,
            combatant.character_id,
            condition_id=condition_id,
            identifier=identifier,
            combatant=combatant,
        )
        return

    conditions = combatant.conditions.all()
    if condition_id is not None:
        conditions = conditions.filter(pk=condition_id)
    elif identifier is not None:
        conditions = conditions.filter(identifier=identifier)

    removed = list(conditions)
    if not removed:
        raise ValidationError("Condition not found on this combatant.")

    for condition in removed:
        post_condition_event(
            context,
            condition,
            ConditionEvent.Action.REMOVED,
            before=condition_snapshot(condition),
            after=None,
            combatant=combatant,
        )
    conditions.delete()


def condition_list_data(
    conditions: list[CharacterCondition] | list[CombatantCondition],
) -> list[dict[str, object]]:
    """Deduplicate condition effects while retaining every independent cause."""
    grouped: dict[str, list[CharacterCondition | CombatantCondition]] = {}
    for condition in conditions:
        grouped.setdefault(condition.identifier, []).append(condition)

    result = []
    for identifier, instances in grouped.items():
        first = instances[0]
        result.append(
            {
                "id": identifier,
                "label": first.get_identifier_display(),
                "exhaustion_level": first.exhaustion_level,
                "source": first.source if len(instances) == 1 else "",
                "duration": first.duration if len(instances) == 1 else "",
                "instances": [
                    {
                        "id": instance.pk,
                        "source": instance.source,
                        "duration": instance.duration,
                    }
                    for instance in instances
                ],
            }
        )

    return result


def encounter_data(context: CampaignContext) -> dict[str, object] | None:
    """Return the active encounter with health filtered for the acting context."""
    encounter = Encounter.objects.filter(
        campaign_id=context.campaign_id,
        is_active=True,
    ).first()
    if encounter is None:
        return None

    is_game_master = context.kind == CampaignContext.Kind.GM
    combatants = encounter.combatants.select_related(
        "character",
        "creature_entry",
    ).prefetch_related("conditions", "character__conditions")

    return {
        "id": encounter.pk,
        "started_at": encounter.started_at.isoformat(),
        "current_combatant_id": encounter.current_combatant_id,
        "combatants": [
            combatant_data(combatant, is_game_master=is_game_master)
            for combatant in combatants
        ],
    }


def combatant_data(
    combatant: EncounterCombatant,
    *,
    is_game_master: bool,
) -> dict[str, object]:
    """Serialize a combatant without leaking hidden NPC or monster HP numbers."""
    current_hp, max_hp = combatant.health
    is_player_character = bool(
        combatant.character_id and combatant.character.is_player_character
    )
    show_numbers = is_player_character or combatant.show_hp_numbers
    show_bar = is_player_character or combatant.show_hp_bar
    can_read_numbers = is_game_master or show_numbers
    can_read_bar = is_game_master or show_bar
    health_percentage = None
    if can_read_bar and current_hp is not None and max_hp:
        rounded_percentage = (current_hp * 100 + max_hp // 2) // max_hp
        health_percentage = max(0, min(100, rounded_percentage))

    return {
        "id": combatant.pk,
        "character_id": combatant.character_id,
        "creature_entry_id": combatant.creature_entry_id,
        "is_player_character": is_player_character,
        "name": combatant.display_name,
        "portrait_url": (
            combatant.character.portrait.url
            if combatant.character_id and combatant.character.portrait
            else None
        ),
        "initiative": combatant.initiative,
        "current_hp": current_hp if can_read_numbers else None,
        "max_hp": max_hp if can_read_numbers else None,
        "health_percentage": health_percentage,
        "show_hp_bar": show_bar,
        "show_hp_numbers": show_numbers,
        "conditions": condition_list_data(
            list(
                combatant.character.conditions.all()
                if combatant.character_id
                else combatant.conditions.all()
            )
        ),
    }
