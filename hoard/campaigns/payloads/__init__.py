"""Pydantic contracts shared by WebSocket and REST compatibility transports."""

from .calendar import (
    CalendarAdjustmentCommand,
    CampaignCalendarChangedEvent,
    CampaignCalendarData,
)
from .campaign import CampaignLevelChangedEvent, CampaignStateChangedEvent
from .invitations import (
    CampaignInvitationChangedEvent,
    CampaignInvitationData,
    CampaignMemberData,
    CampaignMembershipChangedEvent,
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
    "CampaignStateChangedEvent",
    "InvitationCreateCommand",
    "InvitationIdentifierCommand",
    "MemberDeactivationCommand",
]
