<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  createItem,
  deleteItem,
  disableCompendiumSource,
  enableCompendiumSource,
  getCampaign,
  getItems,
  getCompendiumRepositories,
  getCompendiumSources,
  updateItem,
  type Campaign,
  type Item,
  type CompendiumRepository,
  type CompendiumSource,
} from "../api";
import {
  startRepositoryImport,
  subscribeRepositoryImport,
  useCampaignRefresh,
  type RepositoryImportEvent,
} from "../realtime";
import { itemSummary } from "../itemPicker";

const campaignId = Number(useRoute().params.id);
const campaign = ref<Campaign>();
const items = ref<Item[]>([]);
const query = ref("");
const editorOpen = ref(false);
const editing = ref<Item>();
const name = ref("");
const description = ref("");
const error = ref("");
const notice = ref("");
const packs = ref<CompendiumSource[]>([]);
const registry = ref<CompendiumRepository[]>([]);
const packsOpen = ref(false);
const importing = ref(false);
const itemsLoading = ref(false);
const repositoriesLoading = ref(false);
const importProgress = ref("");
const importProgressCurrent = ref<number>();
const importProgressTotal = ref<number>();
let unsubscribeRepositoryImport: (() => void) | undefined;
const repositoryQuery = ref("");
const filtered = computed(() => {
  const needle = query.value.trim().toLowerCase();
  if (!needle) return items.value;
  return items.value.filter((item) =>
    [
      item.name,
      item.description,
      item.source_system,
      item.equipment.category,
      item.equipment.item_type,
      item.equipment.source_book,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(needle),
  );
});
const filteredRepositories = computed(() => {
  const words = repositoryQuery.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if (!words.length) return registry.value;
  return registry.value.filter((repository) => {
    const name = repository.name.toLowerCase();
    const description = repository.description.toLowerCase();
    return words.every((word) => name.includes(word) || description.includes(word));
  });
});

function summary(item: Item): string {
  return (
    itemSummary(item) || (item.is_imported ? "Imported item" : "Campaign custom item")
  );
}

function dismissError(open: boolean): void {
  if (!open) error.value = "";
}

function dismissNotice(open: boolean): void {
  if (!open) notice.value = "";
}

async function load(): Promise<void> {
  itemsLoading.value = true;
  try {
    [campaign.value, items.value, packs.value] = await Promise.all([
      getCampaign(campaignId),
      getItems(campaignId),
      getCompendiumSources(campaignId),
    ]);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to load the compendium.";
  } finally {
    itemsLoading.value = false;
  }
}

async function openPacks(): Promise<void> {
  packsOpen.value = true;
  if (registry.value.length || repositoriesLoading.value) return;
  repositoriesLoading.value = true;
  try {
    registry.value = await getCompendiumRepositories(campaignId);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to load registry.";
  } finally {
    repositoriesLoading.value = false;
  }
}

async function togglePack(pack: CompendiumSource): Promise<void> {
  try {
    if (pack.enabled) await disableCompendiumSource(campaignId, pack.id);
    else await enableCompendiumSource(campaignId, pack.id);
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update source.";
  }
}

async function importRegistryPack(pack: CompendiumRepository): Promise<void> {
  importing.value = true;
  importProgress.value = "Starting import";
  try {
    await startRepositoryImport({
      repositoryId: pack.id,
    });
  } catch (exception) {
    importing.value = false;
    error.value =
      exception instanceof Error ? exception.message : "Unable to import repository.";
  }
}

function repositoryImportEvent(event: RepositoryImportEvent): void {
  if (event.type === "repository.import.started") return;
  if (event.type === "repository.import.progress") {
    importProgress.value = event.message ?? "Importing repository";
    importProgressCurrent.value = event.current ?? undefined;
    importProgressTotal.value = event.total ?? undefined;
    return;
  }
  finishRepositoryImport();
  if (event.type === "repository.import.error") {
    error.value = event.detail ?? "Unable to import repository.";
    return;
  }
  notice.value = "Repository imported and its sources enabled.";
  void load();
}

function finishRepositoryImport(): void {
  importing.value = false;
  importProgressCurrent.value = undefined;
  importProgressTotal.value = undefined;
}

function openEditor(item?: Item): void {
  editing.value = item;
  name.value = item?.name ?? "";
  description.value = item?.description ?? "";
  editorOpen.value = true;
}

async function save(): Promise<void> {
  if (!name.value.trim()) return;
  try {
    if (editing.value)
      await updateItem(campaignId, editing.value.id, {
        name: name.value.trim(),
        description: description.value,
      });
    else await createItem(campaignId, name.value.trim(), description.value);
    notice.value = editing.value ? "Item updated." : "Item created.";
    editorOpen.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to save item.";
  }
}

async function remove(item: Item): Promise<void> {
  try {
    await deleteItem(campaignId, item.id);
    notice.value = "Item deleted.";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to delete item.";
  }
}

onMounted(() => {
  unsubscribeRepositoryImport = subscribeRepositoryImport(repositoryImportEvent);
  void load();
});
onBeforeUnmount(() => {
  unsubscribeRepositoryImport?.();
});
useCampaignRefresh(load);
</script>

<template>
  <v-container class="page-shell">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Campaign library</div>
        <h1>Compendium</h1>
        <p>Browse imported references and campaign-local equipment.</p>
      </div>
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openEditor()"
      >
        New item
      </v-btn>
      <v-btn
        variant="tonal"
        prepend-icon="mdi-bookshelf"
        @click="openPacks"
      >
        Sources
      </v-btn>
    </header>
    <v-snackbar
      :model-value="Boolean(error)"
      color="error"
      location="top end"
      :timeout="10_000"
      @update:model-value="dismissError"
    >
      {{ error }}
      <template #actions>
        <v-btn
          icon="mdi-close"
          variant="text"
          aria-label="Dismiss error message"
          @click="error = ''"
        />
      </template>
    </v-snackbar>
    <v-snackbar
      :model-value="Boolean(notice)"
      color="success"
      location="top end"
      :timeout="5_000"
      @update:model-value="dismissNotice"
    >
      {{ notice }}
    </v-snackbar>
    <v-text-field
      v-model="query"
      prepend-inner-icon="mdi-magnify"
      label="Search the compendium"
      clearable
    />
    <div class="text-caption mb-3">{{ filtered.length }} matching items</div>
    <v-progress-linear
      v-if="itemsLoading"
      indeterminate
      color="primary"
      class="mb-4"
    />
    <div
      v-if="itemsLoading"
      class="d-flex justify-center py-12"
    >
      <v-progress-circular
        indeterminate
        color="primary"
        aria-label="Loading Compendium items"
      />
    </div>
    <v-row v-else>
      <v-col
        v-for="item in filtered"
        :key="item.id"
        cols="12"
        sm="6"
        lg="4"
      >
        <v-card class="h-100">
          <v-card-title>{{ item.name }}</v-card-title>
          <v-card-subtitle>
            {{ summary(item) }}
          </v-card-subtitle>
          <v-card-text>
            <p class="item-description">
              {{ item.description || "No description." }}
            </p>
            <v-chip
              v-if="item.equipment.category"
              size="small"
              class="mr-1"
            >
              {{ item.equipment.category }}
            </v-chip>
            <v-chip
              v-if="item.equipment.item_type"
              size="small"
              class="mr-1"
            >
              {{ item.equipment.item_type }}
            </v-chip>
            <v-chip
              v-if="item.equipment.rarity"
              size="small"
            >
              {{ item.equipment.rarity }}
            </v-chip>
          </v-card-text>
          <v-card-actions v-if="campaign?.is_game_master && !item.is_imported">
            <v-btn @click="openEditor(item)">Edit</v-btn>
            <v-btn
              color="error"
              @click="remove(item)"
            >
              Delete
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-dialog
      v-model="editorOpen"
      max-width="640"
    >
      <v-card :title="editing ? 'Edit campaign item' : 'Create campaign item'">
        <v-card-text>
          <v-text-field
            v-model="name"
            label="Name"
          />
          <v-textarea
            v-model="description"
            label="Description"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="editorOpen = false">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="save"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="packsOpen"
      max-width="900"
    >
      <v-card title="Compendium sources">
        <v-card-text>
          <v-list>
            <v-list-item
              v-for="pack in packs"
              :key="pack.id"
              :title="pack.name"
              :subtitle="`${pack.repository} · ${pack.entry_count} entries`"
            >
              <template
                #append
                v-if="campaign?.is_game_master"
              >
                <v-switch
                  :model-value="pack.enabled"
                  color="primary"
                  hide-details
                  @update:model-value="togglePack(pack)"
                />
              </template>
            </v-list-item>
          </v-list>
          <v-alert
            v-if="importing"
            type="info"
            variant="tonal"
            class="mb-4"
          >
            <div>{{ importProgress }}</div>
            <v-progress-linear
              v-if="importProgressTotal"
              :model-value="((importProgressCurrent ?? 0) / importProgressTotal) * 100"
              class="mt-2"
            />
            <v-progress-linear
              v-else
              indeterminate
              class="mt-2"
            />
          </v-alert>
          <v-divider class="my-4" />
          <h2 class="text-h6 mb-2">RPG Companion community registry</h2>
          <v-text-field
            v-model="repositoryQuery"
            prepend-inner-icon="mdi-magnify"
            label="Search repositories"
            clearable
          />
          <div
            v-if="repositoriesLoading"
            class="d-flex justify-center py-6"
          >
            <v-progress-circular
              indeterminate
              color="primary"
              aria-label="Loading community repositories"
            />
          </div>
          <v-list
            v-else
            density="compact"
          >
            <v-list-item
              v-for="pack in filteredRepositories"
              :key="pack.id"
              :title="pack.name"
              :subtitle="pack.description"
            >
              <template #append>
                <v-btn
                  size="small"
                  :loading="importing"
                  :disabled="pack.installed"
                  @click="importRegistryPack(pack)"
                >
                  {{ pack.installed ? "Installed" : "Import" }}
                </v-btn>
              </template>
            </v-list-item>
            <v-list-item
              v-if="!filteredRepositories.length"
              title="No matching repositories"
            />
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="packsOpen = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style scoped>
.item-description {
  min-height: 3.2em;
}
</style>
