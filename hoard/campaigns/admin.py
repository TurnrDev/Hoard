from __future__ import annotations

from django.contrib import admin
from django.forms.models import BaseModelForm
from django.http import HttpRequest

from .models import (
    Campaign,
    CampaignContext,
    Character,
    ExperienceAccount,
    ExperienceEntry,
    ExperienceTransaction,
    InventoryAccount,
    InventoryEntry,
    InventoryTransaction,
    MoneyAccount,
    MoneyEntry,
    MoneyTransaction,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "calendar_era_abbreviation",
        "calendar_year",
        "calendar_day",
        "use_shared_exp",
        "shared_experience",
    )
    search_fields = ("name",)


@admin.register(CampaignContext)
class CampaignContextAdmin(admin.ModelAdmin):
    list_display = ("user", "campaign", "kind", "is_active")
    list_filter = ("kind", "is_active", "campaign")
    search_fields = ("user__username", "campaign__name")


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "campaign",
        "context",
        "is_active",
        "race",
        "character_class",
    )
    list_filter = ("campaign", "is_active")
    search_fields = ("name", "context__user__username")

    def save_model(
        self, request: HttpRequest, obj: Character, form: BaseModelForm, change: bool
    ) -> None:
        activate = obj.is_active and (not change or "is_active" in form.changed_data)
        if activate:
            obj.is_active = False
        super().save_model(request, obj, form, change)
        if activate:
            obj.activate()


class ReadOnlyLedgerAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "description", "created_at")
    readonly_fields = ("id", "campaign", "description", "created_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


class ReadOnlyAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "character", "is_system")
    readonly_fields = ("id", "campaign", "character", "is_system")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


class ReadOnlyEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "account", "amount")
    readonly_fields = ("id", "transaction", "account", "amount")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
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
