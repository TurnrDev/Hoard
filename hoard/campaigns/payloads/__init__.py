"""Pydantic contracts shared by WebSocket and REST compatibility transports."""

from .calendar import (
    CalendarAdjustmentCommand,
    CampaignCalendarChangedEvent,
    CampaignCalendarData,
)
from .campaign import CampaignStateChangedEvent, ExperienceRecipientCountCommand
from .characters import CharacterIdentifierCommand
from .combat import (
    EncounterCharacterAddCommand,
    EncounterCombatantAddCommand,
    EncounterCombatantIdentifierCommand,
    EncounterCombatantReorderCommand,
    EncounterCombatantUpdateCommand,
    EncounterCurrentCombatantCommand,
    InitiativeTieChoiceCommand,
    PlayerInitiativeRollCommand,
)
from .dicecloud import CharacterActiveCommand, DiceCloudLinkCommand
from .invitations import (
    CampaignInvitationChangedEvent,
    CampaignInvitationData,
    CampaignMemberData,
    CampaignMembershipChangedEvent,
    CampaignPresenceChangedEvent,
    InvitationCreateCommand,
    InvitationIdentifierCommand,
    MemberDeactivationCommand,
)

__all__ = [
    "CalendarAdjustmentCommand",
    "CampaignCalendarChangedEvent",
    "CampaignCalendarData",
    "CampaignInvitationChangedEvent",
    "CampaignInvitationData",
    "CampaignMemberData",
    "CampaignMembershipChangedEvent",
    "CampaignPresenceChangedEvent",
    "CampaignStateChangedEvent",
    "ExperienceRecipientCountCommand",
    "CharacterIdentifierCommand",
    "CharacterActiveCommand",
    "DiceCloudLinkCommand",
    "EncounterCharacterAddCommand",
    "EncounterCombatantAddCommand",
    "EncounterCombatantIdentifierCommand",
    "EncounterCombatantReorderCommand",
    "EncounterCombatantUpdateCommand",
    "EncounterCurrentCombatantCommand",
    "InitiativeTieChoiceCommand",
    "InvitationCreateCommand",
    "InvitationIdentifierCommand",
    "MemberDeactivationCommand",
    "PlayerInitiativeRollCommand",
]
