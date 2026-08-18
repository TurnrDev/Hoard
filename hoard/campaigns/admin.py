from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    Campaign,
    Character,
    ExperienceAccount,
    ExperienceEntry,
    ExperienceTransaction,
    InventoryAccount,
    InventoryEntry,
    InventoryItem,
    InventoryTransaction,
    MoneyAccount,
    MoneyEntry,
    MoneyTransaction,
    Player,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'use_shared_exp', 'shared_experience')
    search_fields = ('name',)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'is_game_master')
    list_filter = ('is_game_master', 'campaign')
    search_fields = ('user__username', 'campaign__name')


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', 'player', 'is_active', 'race', 'character_class')
    list_filter = ('campaign', 'is_active')
    search_fields = ('name', 'player__user__username')


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', 'created_by', 'source_system', 'source_identifier')
    list_filter = ('campaign', 'source_system')
    search_fields = ('name', 'source_identifier')
    readonly_fields = ('source_repository', 'source_system', 'source_identifier', 'source_data')

    def has_change_permission(self, request: HttpRequest, obj: InventoryItem | None = None) -> bool:
        if obj is not None and obj.is_imported:
            return False
        return super().has_change_permission(request, obj)


class ReadOnlyLedgerAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'description', 'created_at')
    readonly_fields = ('id', 'campaign', 'description', 'created_at')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


class ReadOnlyAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'character', 'is_system')
    readonly_fields = ('id', 'campaign', 'character', 'is_system')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


class ReadOnlyEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'account', 'amount')
    readonly_fields = ('id', 'transaction', 'account', 'amount')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


admin.site.register(InventoryAccount, ReadOnlyAccountAdmin)
admin.site.register(MoneyAccount, ReadOnlyAccountAdmin)
admin.site.register(ExperienceAccount, ReadOnlyAccountAdmin)
admin.site.register(InventoryTransaction, ReadOnlyLedgerAdmin)
admin.site.register(MoneyTransaction, ReadOnlyLedgerAdmin)
admin.site.register(ExperienceTransaction, ReadOnlyLedgerAdmin)
admin.site.register(InventoryEntry, ReadOnlyEntryAdmin)
admin.site.register(MoneyEntry, ReadOnlyEntryAdmin)
admin.site.register(ExperienceEntry, ReadOnlyEntryAdmin)
