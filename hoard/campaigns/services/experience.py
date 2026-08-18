from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from ..models import (
    Campaign,
    Character,
    ExperienceAccount,
    ExperienceEntry,
    ExperienceTransaction,
)
from .ledger import _validate_account_campaign, character_account, system_account


def _post_experience_transaction(campaign, entries, *, reason, description='', requested_amount=0, discarded_amount=0, reversal_of=None):
    if not entries or any(not amount for _, amount in entries) or sum(amount for _, amount in entries) != 0:
        raise ValidationError('Experience transactions must contain non-zero entries that balance to zero.')
    for account, _ in entries:
        _validate_account_campaign(account, campaign)
    posted = ExperienceTransaction.objects.create(
        campaign=campaign,
        reason=reason,
        description=description,
        requested_amount=requested_amount,
        discarded_amount=discarded_amount,
        reversal_of=reversal_of,
    )
    ExperienceEntry.objects.bulk_create([
        ExperienceEntry(transaction=posted, account=account, amount=amount) for account, amount in entries
    ])
    return posted


def award_shared_experience(campaign, amount, description='', dry_run=False) -> int:
    """Award group XP and return the XP each eligible character would receive."""
    if amount <= 0:
        raise ValidationError('XP awards must be positive.')

    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        if not campaign.use_shared_exp:
            raise ValidationError('Individual XP awards are not implemented.')
        recipients = list(
            Character.objects.select_for_update()
            .filter(campaign=campaign, is_active=True, player__isnull=False)
            .order_by('pk')
        )
        if not recipients:
            raise ValidationError('Shared XP requires at least one active player character.')
        per_character, remainder = divmod(amount, len(recipients))
        if not per_character:
            raise ValidationError('This award would grant zero XP to every character.')
        if dry_run:
            return per_character

        system = system_account(ExperienceAccount, campaign)
        entries = [(system, -(per_character * len(recipients)))]
        entries.extend((character_account(ExperienceAccount, character), per_character) for character in recipients)
        _post_experience_transaction(
            campaign,
            entries,
            reason=ExperienceTransaction.Reason.SHARED_AWARD,
            description=description,
            requested_amount=amount,
            discarded_amount=remainder,
        )
        campaign.shared_experience += per_character
        campaign.save(update_fields=('shared_experience',))
        return per_character


def activate_character(character):
    """Activate a character and align its XP to the campaign's shared XP baseline."""
    with transaction.atomic():
        character = Character.objects.select_for_update().get(pk=character.pk)
        campaign = Campaign.objects.select_for_update().get(pk=character.campaign_id)
        if character.is_active:
            return character
        if character.player_id:
            existing = Character.objects.filter(
                campaign=campaign,
                player=character.player,
                is_active=True,
            ).exclude(pk=character.pk)
            if existing.exists():
                raise ValidationError('A player can have only one active character in a campaign.')
            account = character_account(ExperienceAccount, character)
            current_experience = ExperienceEntry.objects.filter(account=account).aggregate(total=Sum('amount'))['total'] or 0
            adjustment = campaign.shared_experience - current_experience
            if adjustment:
                system = system_account(ExperienceAccount, campaign)
                _post_experience_transaction(
                    campaign,
                    [(system, -adjustment), (account, adjustment)],
                    reason=ExperienceTransaction.Reason.BASELINE,
                    description='Activated character baseline',
                )
        character.is_active = True
        character.save(update_fields=('is_active',))
        return character


def reverse_experience_transaction(transaction_to_reverse, *, description=''):
    with transaction.atomic():
        original = ExperienceTransaction.objects.select_for_update().get(pk=transaction_to_reverse.pk)
        if hasattr(original, 'reversal'):
            raise ValidationError('This transaction has already been reversed.')
        reversed_transaction = _post_experience_transaction(
            original.campaign,
            [(entry.account, -entry.amount) for entry in original.entries.all()],
            reason=ExperienceTransaction.Reason.REVERSAL,
            description=description or f'Reversal of transaction {original.pk}',
            reversal_of=original,
        )
        if original.reason == ExperienceTransaction.Reason.SHARED_AWARD:
            per_character = original.entries.filter(account__is_system=False).first().amount
            campaign = Campaign.objects.select_for_update().get(pk=original.campaign_id)
            campaign.shared_experience -= per_character
            campaign.save(update_fields=('shared_experience',))
        return reversed_transaction
