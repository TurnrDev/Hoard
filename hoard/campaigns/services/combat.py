from __future__ import annotations

from collections import Counter
from secrets import choice

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Campaign, CampaignContext, Character, Encounter, EncounterCombatant


def require_game_master(context: CampaignContext) -> None:
    if context.kind != CampaignContext.Kind.GM:
        raise PermissionError("Only a game master may manage combat.")


def player_character(context: CampaignContext) -> Character:
    if context.kind != CampaignContext.Kind.PC:
        raise PermissionError("Only a player may perform this action.")

    character = Character.objects.filter(context=context, is_active=True).first()
    if character is None:
        raise ValidationError("This context has no active character.")

    return character


def active_encounter(context: CampaignContext) -> Encounter:
    encounter = Encounter.objects.filter(
        campaign_id=context.campaign_id,
        is_active=True,
    ).first()
    if encounter is None:
        raise ValidationError("There is no active encounter.")

    return encounter


@transaction.atomic
def start_encounter(context: CampaignContext) -> Encounter:
    require_game_master(context)
    campaign = Campaign.objects.select_for_update().get(pk=context.campaign_id)
    existing = Encounter.objects.filter(campaign=campaign, is_active=True).first()
    if existing is not None:
        return existing

    encounter = Encounter.objects.create(campaign=campaign, started_by=context)
    characters = campaign.characters.filter(
        context__isnull=False,
        is_active=True,
    ).order_by("name", "pk")
    EncounterCombatant.objects.bulk_create(
        [
            EncounterCombatant(
                encounter=encounter,
                character=character,
                name=character.name,
                initiative=0,
                initiative_modifier=character.initiative_bonus,
                show_hp_numbers=True,
            )
            for character in characters
        ]
    )

    return encounter


def finish_encounter(context: CampaignContext) -> Encounter:
    require_game_master(context)
    encounter = active_encounter(context)
    encounter.finish()

    return encounter


def add_character_combatant(
    context: CampaignContext,
    character_id: int,
    initiative: int,
) -> EncounterCombatant:
    require_game_master(context)
    encounter = active_encounter(context)
    character = Character.objects.filter(
        pk=character_id,
        campaign_id=context.campaign_id,
        is_active=True,
    ).first()
    if character is None:
        raise ValidationError("Character not found in this campaign.")

    return EncounterCombatant.objects.create(
        encounter=encounter,
        character=character,
        name=character.name,
        initiative=initiative,
        initiative_modifier=character.initiative_bonus,
        show_hp_numbers=character.is_player_character,
    )


def add_encounter_combatant(
    context: CampaignContext,
    *,
    name: str,
    initiative: int,
    current_hp: int | None,
    max_hp: int | None,
) -> EncounterCombatant:
    require_game_master(context)

    return EncounterCombatant.objects.create(
        encounter=active_encounter(context),
        name=name.strip(),
        initiative=initiative,
        current_hp=current_hp,
        max_hp=max_hp,
        show_hp_numbers=False,
    )


def encounter_combatant(
    context: CampaignContext,
    combatant_id: int,
) -> EncounterCombatant:
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
    require_game_master(context)
    combatant = encounter_combatant(context, combatant_id)
    allowed = {"name", "initiative", "current_hp", "max_hp"}
    updates = {key: value for key, value in fields.items() if key in allowed}

    if combatant.character_id and {"name", "current_hp", "max_hp"} & updates.keys():
        raise ValidationError(
            "Linked character identity and health must be changed on the character sheet."
        )
    for field, value in updates.items():
        setattr(combatant, field, value)
    if updates:
        combatant.save(update_fields=tuple(updates))

    return combatant


def set_current_combatant(
    context: CampaignContext,
    combatant_id: int | None,
) -> Encounter:
    require_game_master(context)
    encounter = active_encounter(context)
    encounter.current_combatant = (
        None if combatant_id is None else encounter_combatant(context, combatant_id)
    )
    encounter.save(update_fields=("current_combatant",))

    return encounter


def initiative_tie_group(
    combatant: EncounterCombatant,
    combatants: list[EncounterCombatant],
) -> list[EncounterCombatant]:
    if not combatant.character_id or combatant.initiative_roll is None:
        return []

    return [
        candidate
        for candidate in combatants
        if candidate.character_id
        and candidate.initiative_roll is not None
        and candidate.initiative == combatant.initiative
        and candidate.initiative_modifier == combatant.initiative_modifier
        and candidate.character.context_id
    ]


def agreed_tie_winner(
    group: list[EncounterCombatant],
    choices: dict[str, object],
) -> int | None:
    voters = {entry.character.context_id for entry in group}
    votes = {choices.get(str(voter)) for voter in voters}
    valid_targets = {entry.pk for entry in group}
    if len(votes) == 1 and None not in votes:
        winner = next(iter(votes))
        if isinstance(winner, int) and winner in valid_targets:
            return winner

    return None


def tie_group_key(group: list[EncounterCombatant]) -> str:
    return ",".join(str(entry.pk) for entry in sorted(group, key=lambda entry: entry.pk))


def valid_tie_votes(
    group: list[EncounterCombatant],
    choices: dict[str, object],
) -> list[int]:
    voters = {entry.character.context_id for entry in group}
    valid_targets = {entry.pk for entry in group}

    return [
        vote
        for voter in voters
        if isinstance(vote := choices.get(str(voter)), int) and vote in valid_targets
    ]


def resolved_tie_winner(
    group: list[EncounterCombatant],
    encounter: Encounter,
) -> tuple[int | None, str | None]:
    agreed_winner = agreed_tie_winner(group, encounter.initiative_tie_choices)
    if agreed_winner is not None:
        return agreed_winner, "agreement"

    voters = {entry.character.context_id for entry in group}
    valid_votes = valid_tie_votes(group, encounter.initiative_tie_choices)
    if len(valid_votes) < len(voters):
        return None, None

    valid_targets = {entry.pk for entry in group}
    random_winner = encounter.initiative_tie_breaks.get(tie_group_key(group))
    if isinstance(random_winner, int) and random_winner in valid_targets:
        return random_winner, "random"

    return None, None


def ordered_combatants(encounter: Encounter) -> list[EncounterCombatant]:
    combatants = list(encounter.combatants.select_related("character__context").all())
    winners: dict[int, int | None] = {}
    for combatant in combatants:
        group = initiative_tie_group(combatant, combatants)
        winners[combatant.pk] = resolved_tie_winner(group, encounter)[0]

    return sorted(
        combatants,
        key=lambda combatant: (
            bool(combatant.character_id and combatant.initiative_roll is None),
            -(combatant.initiative_roll == 20),
            -combatant.initiative,
            -combatant.initiative_modifier,
            combatant.pk != winners[combatant.pk],
            combatant.pk,
        ),
    )


@transaction.atomic
def roll_player_initiative(
    context: CampaignContext,
    roll: int,
) -> EncounterCombatant:
    if not 1 <= roll <= 20:
        raise ValidationError("Initiative roll must be between 1 and 20.")

    character = player_character(context)
    encounter = active_encounter(context)
    pending = (
        encounter.combatants.select_for_update()
        .filter(character=character, initiative_roll__isnull=True)
        .order_by("pk")
        .first()
    )
    if pending is None:
        raise ValidationError("You have already completed your initiative rolls.")

    modifier = character.initiative_bonus
    pending.initiative_roll = roll
    pending.initiative_modifier = modifier
    pending.initiative = roll + modifier
    pending.save(update_fields=("initiative_roll", "initiative_modifier", "initiative"))

    character_entries = encounter.combatants.filter(character=character).count()
    if roll == 20 and character_entries < 2:
        EncounterCombatant.objects.create(
            encounter=encounter,
            character=character,
            name=character.name,
            initiative=0,
            initiative_modifier=modifier,
            show_hp_numbers=True,
        )

    encounter.initiative_tie_choices = {}
    encounter.initiative_tie_breaks = {}
    encounter.save(update_fields=("initiative_tie_choices", "initiative_tie_breaks"))

    return pending


@transaction.atomic
def choose_initiative_tie(
    context: CampaignContext,
    combatant_id: int,
) -> Encounter:
    character = player_character(context)
    encounter = Encounter.objects.select_for_update().get(
        campaign_id=context.campaign_id,
        is_active=True,
    )
    combatants = list(encounter.combatants.select_related("character__context"))
    preferred = next((entry for entry in combatants if entry.pk == combatant_id), None)
    if preferred is None:
        raise ValidationError("That initiative choice is not available.")

    group = initiative_tie_group(preferred, combatants)
    owns_tied_entry = any(entry.character_id == character.pk for entry in group)
    tied_contexts = {entry.character.context_id for entry in group}
    if not owns_tied_entry or len(tied_contexts) < 2:
        raise ValidationError("That combatant is not in your initiative tie.")

    choices = dict(encounter.initiative_tie_choices)
    choices[str(context.pk)] = preferred.pk
    tie_breaks = dict(encounter.initiative_tie_breaks)
    group_key = tie_group_key(group)
    agreed_winner = agreed_tie_winner(group, choices)
    all_players_voted = len(valid_tie_votes(group, choices)) == len(tied_contexts)
    if agreed_winner is not None:
        tie_breaks.pop(group_key, None)
    elif all_players_voted and group_key not in tie_breaks:
        tie_breaks[group_key] = choice([entry.pk for entry in group])

    encounter.initiative_tie_choices = choices
    encounter.initiative_tie_breaks = tie_breaks
    encounter.save(update_fields=("initiative_tie_choices", "initiative_tie_breaks"))

    return encounter


@transaction.atomic
def end_player_turn(context: CampaignContext) -> Encounter:
    character = player_character(context)
    encounter = active_encounter(context)
    current = encounter.current_combatant
    if current is None or current.character_id != character.pk:
        raise PermissionError("Only the current player may end this turn.")

    ordered = [
        entry
        for entry in ordered_combatants(encounter)
        if not (entry.character_id and entry.initiative_roll is None)
    ]
    current_index = next(
        index for index, entry in enumerate(ordered) if entry.pk == current.pk
    )
    encounter.current_combatant = ordered[(current_index + 1) % len(ordered)]
    encounter.save(update_fields=("current_combatant",))

    return encounter


@transaction.atomic
def reorder_combatants(
    context: CampaignContext,
    combatant_ids: list[int],
) -> list[EncounterCombatant]:
    require_game_master(context)
    encounter = active_encounter(context)
    combatants = list(encounter.combatants.select_for_update().filter(pk__in=combatant_ids))
    combatants_by_id = {combatant.pk: combatant for combatant in combatants}
    existing_ids = set(encounter.combatants.values_list("pk", flat=True))
    if set(combatant_ids) != existing_ids:
        raise ValidationError("Combatant order must include every initiative entry.")

    initiatives = sorted((combatant.initiative for combatant in combatants), reverse=True)
    if len(initiatives) != len(set(initiatives)):
        highest = min(100, max(max(initiatives), -100 + len(initiatives) - 1))
        initiatives = [highest - index for index in range(len(initiatives))]

    reordered = [combatants_by_id[combatant_id] for combatant_id in combatant_ids]
    changed = []
    for combatant, initiative in zip(reordered, initiatives, strict=True):
        if combatant.initiative == initiative:
            continue

        combatant.initiative = initiative
        changed.append(combatant)
    if changed:
        EncounterCombatant.objects.bulk_update(changed, ("initiative",))

    return reordered


@transaction.atomic
def remove_combatant(context: CampaignContext, combatant_id: int) -> None:
    require_game_master(context)
    encounter_combatant(context, combatant_id).delete()


def encounter_data(context: CampaignContext) -> dict[str, object] | None:
    encounter = Encounter.objects.filter(
        campaign_id=context.campaign_id,
        is_active=True,
    ).first()
    if encounter is None:
        return None

    combatants = ordered_combatants(encounter)

    return {
        "id": encounter.pk,
        "started_at": encounter.started_at.isoformat(),
        "current_combatant_id": encounter.current_combatant_id,
        "combatants": [
            combatant_data(
                combatant,
                context=context,
                combatants=combatants,
                initiative_position=initiative_position,
            )
            for initiative_position, combatant in enumerate(combatants)
        ],
    }


def combatant_data(
    combatant: EncounterCombatant,
    *,
    context: CampaignContext,
    combatants: list[EncounterCombatant],
    initiative_position: int,
) -> dict[str, object]:
    current_hp, max_hp = combatant.health
    is_player_character = bool(
        combatant.character_id and combatant.character.is_player_character
    )
    can_read_actual_health = (
        context.kind == CampaignContext.Kind.GM or is_player_character
    )
    health_percentage = None
    if current_hp is not None and max_hp:
        rounded_percentage = (current_hp * 100 + max_hp // 2) // max_hp
        health_percentage = max(0, min(100, rounded_percentage))

    if can_read_actual_health:
        displayed_current_hp = current_hp
        displayed_max_hp = max_hp
    elif health_percentage is not None:
        displayed_current_hp = health_percentage
        displayed_max_hp = 100
    else:
        displayed_current_hp = None
        displayed_max_hp = None

    is_owner = bool(
        combatant.character_id
        and combatant.character.context_id
        and combatant.character.context.user_id == context.user_id
    )
    tie_group = initiative_tie_group(combatant, combatants)
    tied_contexts = {entry.character.context_id for entry in tie_group}
    valid_votes = valid_tie_votes(tie_group, combatant.encounter.initiative_tie_choices)
    vote_counts = Counter(valid_votes)
    tie_winner_id, tie_resolution = resolved_tie_winner(tie_group, combatant.encounter)
    tie_options = []
    if is_owner and len(tied_contexts) > 1:
        tie_options = [
            {
                "combatant_id": entry.pk,
                "name": entry.display_name,
                "vote_count": vote_counts[entry.pk],
            }
            for entry in tie_group
        ]
    tie_choice = combatant.encounter.initiative_tie_choices.get(str(context.pk))
    if not isinstance(tie_choice, int):
        tie_choice = None

    return {
        "id": combatant.pk,
        "character_id": combatant.character_id,
        "is_player_character": is_player_character,
        "name": combatant.display_name,
        "portrait_url": (
            combatant.character.portrait.url
            if combatant.character_id and combatant.character.portrait
            else None
        ),
        "initiative": combatant.initiative,
        "initiative_position": initiative_position,
        "initiative_roll": combatant.initiative_roll,
        "initiative_modifier": combatant.initiative_modifier,
        "can_roll_initiative": is_owner and combatant.initiative_roll is None,
        "can_end_turn": is_owner
        and combatant.encounter.current_combatant_id == combatant.pk,
        "tie_options": tie_options,
        "tie_choice_id": tie_choice,
        "tie_votes_cast": len(valid_votes) if tie_options else 0,
        "tie_votes_required": len(tied_contexts) if tie_options else 0,
        "tie_winner_id": tie_winner_id if tie_options else None,
        "tie_resolution": tie_resolution if tie_options else None,
        "current_hp": displayed_current_hp,
        "max_hp": displayed_max_hp,
        "health_percentage": health_percentage,
        "show_hp_numbers": is_player_character,
    }
