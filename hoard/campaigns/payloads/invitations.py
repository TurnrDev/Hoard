"""Campaign membership and invitation contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class MemberDeactivationCommand(BaseModel):
    """Validated input for deactivating a campaign member."""

    member_id: int = Field(gt=0)


class InvitationCreateCommand(BaseModel):
    """Validated input for creating a campaign invitation."""

    email: str = Field(default="", max_length=254)


class InvitationIdentifierCommand(BaseModel):
    """Validated input for commands that address one invitation."""

    invitation_id: int = Field(gt=0)


class CampaignMemberData(BaseModel):
    """The public membership fields required by campaign management clients."""

    id: int
    username: str
    first_name: str
    last_name: str
    is_game_master: bool
    is_active: bool
    connected: bool = False
    last_seen_at: str | None = None


class CampaignPresenceChangedEvent(BaseModel):
    """Authoritative connectivity state for one acting context."""

    type: Literal["campaign.presence_changed"] = "campaign.presence_changed"
    context_id: int
    connected: bool
    last_seen_at: str | None = None


class CampaignInvitationData(BaseModel):
    """The non-secret state of a campaign invitation."""

    id: int
    email: str
    created_at: str
    expires_at: str
    accepted_at: str | None
    status: Literal["pending", "accepted", "expired", "revoked"]


class CampaignMembershipChangedEvent(BaseModel):
    """Authoritative member state after a membership command."""

    type: Literal["campaign.membership_changed"] = "campaign.membership_changed"
    member: CampaignMemberData
    request_id: str | None = None


class CampaignInvitationChangedEvent(BaseModel):
    """Authoritative non-secret invitation state after an invitation command."""

    type: Literal["campaign.invitation_changed"] = "campaign.invitation_changed"
    invitation: CampaignInvitationData
    request_id: str | None = None
