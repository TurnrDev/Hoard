from django.contrib import admin

from .models import CompendiumEntry, CompendiumRepository, CompendiumSource


@admin.register(CompendiumSource)
class CompendiumSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "identifier", "repository")


@admin.register(CompendiumRepository)
class CompendiumRepositoryAdmin(admin.ModelAdmin):
    list_display = ("name", "identifier", "campaign", "repository_url")
    search_fields = (
        "name",
        "identifier",
        "description",
        "repository_url",
        "github_repository",
        "campaign__name",
    )


@admin.register(CompendiumEntry)
class CompendiumEntryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "source", "source_book", "rarity")
    list_filter = ("kind", "source", "rarity")
    search_fields = ("name", "source_identifier", "source_book")
