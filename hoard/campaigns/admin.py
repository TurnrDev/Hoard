from __future__ import annotations

from django.contrib import admin
from django import forms
from django.forms.models import BaseModelForm
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


class CampaignAdminForm(forms.ModelForm):
    item_sources = forms.MultipleChoiceField(
        choices=(('5e', 'D&D 5e'), ('5e2024', 'D&D 5e (2024)')),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Imported catalogue sources available to this campaign.',
    )

    class Meta:
        model = Campaign
        fields = '__all__'


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    form = CampaignAdminForm
    list_display = ('name', 'use_shared_exp', 'shared_experience', 'item_sources')
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

    def save_model(self, request: HttpRequest, obj: Character, form: BaseModelForm, change: bool) -> None:
        activate = obj.is_active and (not change or 'is_active' in form.changed_data)
        if activate:
            obj.is_active = False
        super().save_model(request, obj, form, change)
        if activate:
            obj.activate()


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
