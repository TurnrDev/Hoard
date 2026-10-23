from django.contrib import admin

from .models import (
    Campaign,
    CampaignContext,
    Character,
    Encounter,
    EncounterCombatant,
    PartyExperienceAward,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "calendar_era_abbreviation",
        "calendar_year",
        "calendar_day",
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
    list_display = ("context", "campaign", "dicecloud_creature_id", "is_active")
    list_filter = ("campaign", "is_active")
    search_fields = ("context__user__username", "dicecloud_creature_id")


admin.site.register(Encounter)
admin.site.register(EncounterCombatant)
admin.site.register(PartyExperienceAward)
