"""Pydantic contracts shared by WebSocket and REST compatibility transports."""

from .calendar import (
    CalendarAdjustmentCommand,
    CampaignCalendarChangedEvent,
    CampaignCalendarData,
)
from .campaign import CampaignLevelChangedEvent, CampaignStateChangedEvent
from .characters import (
    CharacterCreateCommand,
    CharacterHealthChangedEvent,
    CharacterHealthCommand,
    CharacterIdentifierCommand,
    CharacterLifecycleData,
    CharacterLifecycleEvent,
    CharacterUpdateCommand,
)
from .combat import (
    CharacterConditionCommand,
    CharacterConditionIdentifierCommand,
    CombatantConditionCommand,
    CombatantConditionIdentifierCommand,
    EncounterCharacterAddCommand,
    EncounterCombatantAddCommand,
    EncounterCombatantIdentifierCommand,
    EncounterCombatantUpdateCommand,
)
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
    "CampaignLevelChangedEvent",
    "CampaignMemberData",
    "CampaignMembershipChangedEvent",
    "CampaignPresenceChangedEvent",
    "CampaignStateChangedEvent",
    "CharacterConditionCommand",
    "CharacterConditionIdentifierCommand",
    "CombatantConditionCommand",
    "CombatantConditionIdentifierCommand",
    "CharacterHealthChangedEvent",
    "CharacterHealthCommand",
    "CharacterCreateCommand",
    "CharacterIdentifierCommand",
    "CharacterLifecycleData",
    "CharacterLifecycleEvent",
    "CharacterUpdateCommand",
    "EncounterCharacterAddCommand",
    "EncounterCombatantAddCommand",
    "EncounterCombatantIdentifierCommand",
    "EncounterCombatantUpdateCommand",
    "InvitationCreateCommand",
    "InvitationIdentifierCommand",
    "MemberDeactivationCommand",
]
