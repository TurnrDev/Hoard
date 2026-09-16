"""Pydantic contracts shared by WebSocket and REST compatibility transports."""

from .calendar import (
    CalendarAdjustmentCommand,
    CampaignCalendarChangedEvent,
    CampaignCalendarData,
)
from .campaign import CampaignStateChangedEvent
from .characters import (
    CharacterCreateCommand,
    CharacterHealthChangedEvent,
    CharacterHealthCommand,
    CharacterIdentifierCommand,
    CharacterLifecycleData,
    CharacterLifecycleEvent,
    CharacterRestCommand,
    CharacterUpdateCommand,
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
    "CampaignMemberData",
    "CampaignMembershipChangedEvent",
    "CampaignPresenceChangedEvent",
    "CampaignStateChangedEvent",
    "CharacterCreateCommand",
    "CharacterHealthChangedEvent",
    "CharacterHealthCommand",
    "CharacterIdentifierCommand",
    "CharacterLifecycleData",
    "CharacterLifecycleEvent",
    "CharacterRestCommand",
    "CharacterUpdateCommand",
    "InvitationCreateCommand",
    "InvitationIdentifierCommand",
    "MemberDeactivationCommand",
]
