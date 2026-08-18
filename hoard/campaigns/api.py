from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Campaign,
    Character,
    ExperienceEntry,
    ExperienceTransaction,
    InventoryEntry,
    InventoryItem,
    InventoryTransaction,
    MoneyEntry,
    MoneyTransaction,
    Player,
)
from .services import exchange_coins, grant_coins, grant_loot, reverse_transaction, spend_coins, take_loot, transfer_item


def _validation_error(error: DjangoValidationError) -> ValidationError:
    if hasattr(error, 'message_dict'):
        return ValidationError(error.message_dict)
    return ValidationError(error.messages)


def _transaction_data(transaction: InventoryTransaction | MoneyTransaction | ExperienceTransaction) -> dict[str, object]:
    return {
        'id': transaction.pk,
        'ledger': transaction._meta.model_name.removesuffix('transaction'),
        'description': transaction.description,
        'created_at': transaction.created_at,
    }


def _character_data(character: Character) -> dict[str, object]:
    return {
        'id': character.pk,
        'name': character.name,
        'is_active': character.is_active,
        'race': character.race,
        'class': character.character_class,
        'experience': character.experience,
        'money': {
            'cp': character.money.copper, 'sp': character.money.silver, 'ep': character.money.electrum,
            'gp': character.money.gold, 'pp': character.money.platinum, 'gold_value': str(character.money.gold_value),
        },
        'inventory': [
            {'item_id': item.pk, 'name': item.name, 'quantity': quantity}
            for item, quantity in character.inventory.items()
        ],
    }


def _item_data(item: InventoryItem) -> dict[str, object]:
    return {
        'id': item.pk, 'name': item.name, 'description': item.description, 'campaign_id': item.campaign_id,
        'created_by_id': item.created_by_id,
        'created_by_username': item.created_by.user.get_username() if item.created_by_id else None,
        'source_system': item.source_system or None,
        'source_identifier': item.source_identifier or None, 'source_repository': item.source_repository or None,
        'equipment': {
            'category': item.equipment_category or None,
            'source_book': item.source_book or None,
            'item_type': item.item_type or None,
            'cost_amount': str(item.cost_amount) if item.cost_amount is not None else None,
            'cost_currency': item.cost_currency or None,
            'weight_amount': str(item.weight_amount) if item.weight_amount is not None else None,
            'weight_unit': item.weight_unit or None,
            'rarity': item.rarity or None,
            'is_magic': item.is_magic,
            'requires_attunement': item.requires_attunement,
        },
        'is_imported': item.is_imported,
    }


def _metadata_from_request(data: object, *, defaults: InventoryItem | None = None) -> dict[str, object]:
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValidationError({'metadata': 'Metadata must be an object.'})

    def text(name: str, default: str = '') -> str:
        value = data.get(name, default)
        if value is None:
            return ''
        if not isinstance(value, str):
            raise ValidationError({f'metadata.{name}': 'Must be a string.'})
        return value.strip()

    def number(name: str, default: Decimal | None = None) -> Decimal | None:
        value = data.get(name, default)
        if value in (None, ''):
            return None
        if isinstance(value, bool):
            raise ValidationError({f'metadata.{name}': 'Must be a number or null.'})
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ValidationError({f'metadata.{name}': 'Must be a number or null.'}) from error

    def boolean(name: str, default: bool | None = None) -> bool | None:
        value = data.get(name, default)
        if value is None or isinstance(value, bool):
            return value
        raise ValidationError({f'metadata.{name}': 'Must be true, false, or null.'})

    values = {
        'equipment_category': text('category', defaults.equipment_category if defaults else ''),
        'source_book': text('source_book', defaults.source_book if defaults else ''),
        'item_type': text('item_type', defaults.item_type if defaults else ''),
        'cost_amount': number('cost_amount', defaults.cost_amount if defaults else None),
        'cost_currency': text('cost_currency', defaults.cost_currency if defaults else ''),
        'weight_amount': number('weight_amount', defaults.weight_amount if defaults else None),
        'weight_unit': text('weight_unit', defaults.weight_unit if defaults else ''),
        'rarity': text('rarity', defaults.rarity if defaults else ''),
        'is_magic': boolean('is_magic', defaults.is_magic if defaults else None),
        'requires_attunement': boolean('requires_attunement', defaults.requires_attunement if defaults else None),
    }
    if values['cost_currency'] and values['cost_currency'] not in {'cp', 'sp', 'ep', 'gp', 'pp'}:
        raise ValidationError({'metadata.cost_currency': 'Must be cp, sp, ep, gp, or pp.'})
    if (values['cost_amount'] is None) == bool(values['cost_currency']):
        raise ValidationError({'metadata.cost_amount': 'Cost amount and currency must be supplied together.'})
    if (values['weight_amount'] is None) == bool(values['weight_unit']):
        raise ValidationError({'metadata.weight_amount': 'Weight amount and unit must be supplied together.'})
    return values


class CampaignAccessView(APIView):
    campaign: Campaign
    player: Player

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        self.campaign = get_object_or_404(Campaign, pk=kwargs['campaign_id'])
        self.player = get_object_or_404(Player, campaign=self.campaign, user=request.user)

    def require_game_master(self) -> None:
        if not self.player.is_game_master:
            raise PermissionDenied('This action requires a campaign game master.')

    def character(self, character_id: object) -> Character:
        return get_object_or_404(Character, pk=character_id, campaign=self.campaign)

    def item(self, item_id: object, *, include_disabled_sources: bool = False) -> InventoryItem:
        items = self.all_campaign_items() if include_disabled_sources else self.items()
        return get_object_or_404(items, pk=item_id)

    def all_campaign_items(self) -> QuerySet[InventoryItem]:
        """Return campaign items plus every global item, including disabled sources.

        This is only used when removing an item already held by a character.
        Changing a campaign's catalogue must not strand existing inventory.
        """
        return InventoryItem.objects.filter(
            Q(campaign=self.campaign) | Q(campaign__isnull=True)
        ).select_related('created_by__user')

    def items(self) -> QuerySet[InventoryItem]:
        source_query = Q(campaign__isnull=True, source_system__in=self.campaign.item_sources)
        return self.all_campaign_items().filter(Q(campaign=self.campaign) | source_query)


class CampaignListView(APIView):
    def get(self, request: Request) -> Response:
        memberships = Player.objects.filter(user=request.user).select_related('campaign').order_by('campaign__name')
        return Response([
            {
                'id': membership.campaign_id,
                'name': membership.campaign.name,
                'is_game_master': membership.is_game_master,
            }
            for membership in memberships
        ])


class CampaignDetailView(CampaignAccessView):
    def get(self, request: Request, campaign_id: int) -> Response:
        characters = self.campaign.characters.all()
        if not self.player.is_game_master:
            characters = characters.filter(player=self.player)
        return Response({
            'id': self.campaign.pk, 'name': self.campaign.name, 'use_shared_exp': self.campaign.use_shared_exp,
            'shared_experience': self.campaign.shared_experience, 'is_game_master': self.player.is_game_master,
            'item_sources': self.campaign.item_sources,
            'characters': [_character_data(character) for character in characters],
        })


class ItemListCreateView(CampaignAccessView):
    def get(self, request: Request, campaign_id: int) -> Response:
        items = self.items().order_by('name')
        return Response([_item_data(item) for item in items])

    def post(self, request: Request, campaign_id: int) -> Response:
        name = request.data.get('name')
        description = request.data.get('description', '')
        if not isinstance(name, str) or not name.strip():
            raise ValidationError({'name': 'A non-empty item name is required.'})
        if not isinstance(description, str):
            raise ValidationError({'description': 'Description must be a string.'})
        item = InventoryItem(
            campaign=self.campaign,
            created_by=self.player,
            name=name.strip(),
            description=description,
            **_metadata_from_request(request.data.get('metadata')),
        )
        try:
            item.full_clean()
        except DjangoValidationError as error:
            raise _validation_error(error) from error
        item.save()
        return Response(_item_data(item), status=status.HTTP_201_CREATED)


class ItemCopyView(CampaignAccessView):
    def post(self, request: Request, campaign_id: int, item_id: int) -> Response:
        self.require_game_master()
        source = self.item(item_id)
        name = request.data.get('name', source.name)
        description = request.data.get('description', source.description)
        if not isinstance(name, str) or not name.strip() or not isinstance(description, str):
            raise ValidationError('Name and description must be strings, and name cannot be blank.')
        item = InventoryItem(
            campaign=self.campaign, created_by=self.player, name=name.strip(), description=description,
            source_data={'copied_from_item_id': source.pk}, **_metadata_from_request(request.data.get('metadata'), defaults=source),
        )
        try:
            item.full_clean()
        except DjangoValidationError as error:
            raise _validation_error(error) from error
        item.save()
        return Response(_item_data(item), status=status.HTTP_201_CREATED)


class CampaignActionView(CampaignAccessView):
    def post(self, request: Request, campaign_id: int, action: str) -> Response:
        self.require_game_master()
        try:
            if action == 'grant-loot':
                posted = grant_loot(recipient=self.character(request.data.get('recipient_id')), item=self.item(request.data.get('item_id')), quantity=request.data.get('quantity'), description=request.data.get('description', ''))
            elif action == 'take-loot':
                posted = take_loot(source=self.character(request.data.get('source_id')), item=self.item(request.data.get('item_id'), include_disabled_sources=True), quantity=request.data.get('quantity'), description=request.data.get('description', ''))
            elif action == 'transfer-item':
                posted = transfer_item(source=self.character(request.data.get('source_id')), recipient=self.character(request.data.get('recipient_id')), item=self.item(request.data.get('item_id')), quantity=request.data.get('quantity'), description=request.data.get('description', ''))
            elif action == 'grant-coins':
                posted = grant_coins(recipient=self.character(request.data.get('character_id')), coins=request.data.get('coins', {}), description=request.data.get('description', ''))
            elif action == 'spend-coins':
                posted = spend_coins(spender=self.character(request.data.get('character_id')), coins=request.data.get('coins', {}), description=request.data.get('description', ''))
            elif action == 'exchange-coins':
                posted = exchange_coins(character=self.character(request.data.get('character_id')), given=request.data.get('given', {}), received=request.data.get('received', {}), description=request.data.get('description', ''))
            elif action in {'preview-shared-xp', 'award-shared-xp'}:
                amount = request.data.get('amount')
                if not isinstance(amount, int) or isinstance(amount, bool):
                    raise ValidationError({'amount': 'XP amount must be an integer.'})
                per_character = self.campaign.award_shared_experience(amount, description=request.data.get('description', ''), dry_run=action == 'preview-shared-xp')
                return Response({'per_character': per_character, 'dry_run': action == 'preview-shared-xp'})
            else:
                raise ValidationError({'action': 'Unknown campaign action.'})
        except DjangoValidationError as error:
            raise _validation_error(error) from error
        return Response(_transaction_data(posted), status=status.HTTP_201_CREATED)


class TransactionReverseView(CampaignAccessView):
    transaction_models = {'inventory': InventoryTransaction, 'money': MoneyTransaction, 'experience': ExperienceTransaction}

    def post(self, request: Request, campaign_id: int, ledger: str, transaction_id: int) -> Response:
        self.require_game_master()
        model = self.transaction_models.get(ledger)
        if model is None:
            raise ValidationError({'ledger': 'Unknown ledger.'})
        original = get_object_or_404(model, pk=transaction_id, campaign=self.campaign)
        try:
            reversed_transaction = reverse_transaction(cast(InventoryTransaction | MoneyTransaction | ExperienceTransaction, original), description=request.data.get('description', ''))
        except DjangoValidationError as error:
            raise _validation_error(error) from error
        return Response(_transaction_data(reversed_transaction), status=status.HTTP_201_CREATED)


def _entry_data(entry: InventoryEntry | MoneyEntry | ExperienceEntry) -> dict[str, object]:
    ledger_name = entry.transaction._meta.model_name.removesuffix('transaction')
    account_name = (
        f'Campaign {ledger_name} system'
        if entry.account.is_system
        else entry.account.character.name
    )
    data: dict[str, object] = {
        'account_id': entry.account_id,
        'account_name': account_name,
        'is_system_account': entry.account.is_system,
        'amount': entry.amount,
    }
    if isinstance(entry, InventoryEntry):
        data['item_id'] = entry.item_id
        data['item_name'] = entry.item.name
    elif isinstance(entry, MoneyEntry):
        data['denomination'] = entry.denomination
    return data


def _history_data(transaction: InventoryTransaction | MoneyTransaction | ExperienceTransaction) -> dict[str, object]:
    data = _transaction_data(transaction)
    data['entries'] = [_entry_data(entry) for entry in transaction.entries.all()]
    data['reversal_of_id'] = transaction.reversal_of_id
    data['is_reversed'] = type(transaction).objects.filter(reversal_of=transaction).exists()
    if isinstance(transaction, ExperienceTransaction):
        data['reason'] = transaction.reason
        data['requested_amount'] = transaction.requested_amount
        data['discarded_amount'] = transaction.discarded_amount
    return data


class TransactionHistoryView(CampaignAccessView):
    transaction_models = {
        'inventory': InventoryTransaction,
        'money': MoneyTransaction,
        'experience': ExperienceTransaction,
    }

    def get(self, request: Request, campaign_id: int) -> Response:
        ledger = request.query_params.get('ledger', 'all')
        if ledger != 'all' and ledger not in self.transaction_models:
            raise ValidationError({'ledger': 'Unknown ledger.'})
        try:
            page = max(int(request.query_params.get('page', '1')), 1)
            page_size = min(max(int(request.query_params.get('page_size', '25')), 1), 100)
        except ValueError as error:
            raise ValidationError({'page': 'Page and page_size must be integers.'}) from error
        models = self.transaction_models.items() if ledger == 'all' else ((ledger, self.transaction_models[ledger]),)
        transactions: list[InventoryTransaction | MoneyTransaction | ExperienceTransaction] = []
        for _, model in models:
            entry_model = model._meta.get_field('entries').related_model
            queryset = model.objects.filter(campaign=self.campaign).prefetch_related(
                Prefetch('entries', queryset=entry_model.objects.select_related('account__character', 'item'))
                if model is InventoryTransaction
                else Prefetch('entries', queryset=entry_model.objects.select_related('account__character'))
            )
            if not self.player.is_game_master:
                queryset = queryset.filter(entries__account__character__player=self.player).distinct()
            transactions.extend(queryset)
        transactions.sort(key=lambda transaction: transaction.created_at, reverse=True)
        start = (page - 1) * page_size
        results = transactions[start:start + page_size]
        return Response({
            'count': len(transactions),
            'page': page,
            'page_size': page_size,
            'results': [_history_data(transaction) for transaction in results],
        })
