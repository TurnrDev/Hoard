<template>
  <section aria-labelledby="compendium-title">
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-5"
    >
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Campaign library
        </p>
        <h1
          id="compendium-title"
          class="display-5 mb-2"
        >
          Compendium
        </h1>
        <p class="mb-0 text-body-secondary">
          Browse imported references and campaign-local equipment.
        </p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <Button
          icon="mdi mdi-plus"
          label="New item"
          @click="openEditor()"
        />
        <Button
          icon="mdi mdi-bookshelf"
          label="Sources"
          outlined
          @click="openPacks"
        />
      </div>
    </header>
    <Message
      v-if="error"
      severity="error"
      closable
      @close="dismissError(false)"
    >
      {{ error }}
    </Message>
    <div class="row justify-content-between align-items-end g-2 mb-4">
      <div class="col-12 col-lg-7">
        <label
          class="d-grid gap-2"
          for="compendium-search"
        >
          <span class="fw-semibold">Search the compendium</span>
          <InputText
            id="compendium-search"
            v-model="query"
            fluid
          />
        </label>
      </div>
      <p class="col-12 col-lg-auto mb-0 small text-body-secondary">
        {{ filtered.length }} matching items
      </p>
    </div>
    <ProgressBar
      v-if="itemsLoading"
      indeterminate
      class="mb-3"
    />
    <div
      v-if="itemsLoading"
      class="d-grid py-5 justify-content-center"
    >
      <ProgressSpinner
        indeterminate
        aria-label="Loading Compendium items"
      />
    </div>
    <ul
      v-else
      class="list-unstyled row g-3"
    >
      <li
        v-for="item in filtered"
        :key="item.id"
        class="col-12 col-md-6 col-xl-4"
      >
        <article class="border rounded-3 p-3 h-100 d-flex flex-column">
          <header>
            <h2 class="h4">{{ item.name }}</h2>
          </header>
          <p class="small text-body-secondary">{{ summary(item) }}</p>
          <div class="flex-grow-1">
            <p>{{ item.description || "No description." }}</p>
            <Chip
              v-if="item.equipment.category"
              size="small"
              class="me-1"
            >
              {{ item.equipment.category }}
            </Chip>
            <Chip
              v-if="item.equipment.item_type"
              size="small"
              class="compendium-item__fact"
            >
              {{ item.equipment.item_type }}
            </Chip>
            <Chip
              v-if="item.equipment.rarity"
              size="small"
            >
              {{ item.equipment.rarity }}
            </Chip>
          </div>
          <footer
            v-if="campaign?.is_game_master && !item.is_imported"
            class="d-flex gap-2 mt-3"
          >
            <Button
              label="Edit"
              outlined
              @click="openEditor(item)"
            />
            <Button
              severity="danger"
              label="Delete"
              @click="remove(item)"
            />
          </footer>
        </article>
      </li>
    </ul>
    <Dialog
      v-model:visible="editorOpen"
      modal
      :style="{ width: 'min(40rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="compendium-editor-heading"
      >
        <h2
          id="compendium-editor-heading"
          class="h3"
        >
          {{ editing ? "Edit campaign item" : "Create campaign item" }}
        </h2>
        <form
          class="d-grid gap-3"
          @submit.prevent="save"
        >
          <label for="compendium-item-name">Name</label>
          <InputText
            id="compendium-item-name"
            v-model="name"
            fluid
          />
          <label for="compendium-item-description">Description</label>
          <Textarea
            id="compendium-item-description"
            v-model="description"
            rows="6"
            fluid
          />
        </form>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="editorOpen = false"
          />
          <Button
            label="Save"
            @click="save"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="packsOpen"
      modal
      :style="{ width: 'min(56rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="compendium-sources-heading"
      >
        <h2
          id="compendium-sources-heading"
          class="h3"
        >
          Compendium sources
        </h2>
        <div class="d-grid gap-3">
          <ul class="list-group">
            <li
              v-for="pack in packs"
              :key="pack.id"
            >
              <div
                class="list-group-item d-flex align-items-center justify-content-between gap-3"
              >
                <div>
                  <h3 class="h5 mb-1">{{ pack.name }}</h3>
                  <p class="mb-0 text-body-secondary">
                    {{ pack.repository }} · {{ pack.entry_count }} entries
                  </p>
                </div>
                <template v-if="campaign?.is_game_master">
                  <ToggleSwitch
                    :model-value="pack.enabled"
                    :aria-label="`Enable ${pack.name}`"
                    @update:model-value="togglePack(pack)"
                  />
                </template>
              </div>
            </li>
          </ul>
          <Message
            v-if="importing"
            severity="info"
          >
            <div>{{ importProgress }}</div>
            <ProgressBar
              v-if="importProgressTotal"
              :value="((importProgressCurrent ?? 0) / importProgressTotal) * 100"
              class="compendium-import-progress"
            />
            <ProgressBar
              v-else
              indeterminate
              class="compendium-import-progress"
            />
          </Message>
          <div class="border-top pt-3">
            <h2 class="h4">RPG Companion community registry</h2>
            <label
              class="d-grid gap-2"
              for="repository-search"
            >
              <span class="fw-semibold">Search repositories</span>
              <InputText
                id="repository-search"
                v-model="repositoryQuery"
                fluid
              />
            </label>
          </div>
          <div
            v-if="repositoriesLoading"
            class="d-grid py-5 justify-content-center"
          >
            <ProgressSpinner
              indeterminate
              aria-label="Loading community repositories"
            />
          </div>
          <ul
            v-else
            class="list-group"
          >
            <li
              v-for="pack in filteredRepositories"
              :key="pack.id"
            >
              <div
                class="list-group-item d-flex align-items-center justify-content-between gap-3"
              >
                <div>
                  <h3 class="h5 mb-1">{{ pack.name }}</h3>
                  <p class="mb-0 text-body-secondary">{{ pack.description }}</p>
                </div>
                <Button
                  size="small"
                  :loading="importing"
                  :disabled="pack.installed"
                  :label="pack.installed ? 'Installed' : 'Import'"
                  @click="importRegistryPack(pack)"
                />
              </div>
            </li>
            <li
              v-if="!filteredRepositories.length"
              class="list-group-item text-body-secondary"
            >
              No matching repositories.
            </li>
          </ul>
        </div>
        <footer class="d-flex justify-content-end">
          <Button
            label="Close"
            @click="packsOpen = false"
          />
        </footer>
      </section>
    </Dialog>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Chip from "primevue/chip";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import ProgressSpinner from "primevue/progressspinner";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { defineComponent } from "vue";
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
  campaignRefreshRevision,
  type RepositoryImportEvent,
} from "../realtime";
import { itemSummary } from "../itemPicker";

export default defineComponent({
  components: {
    Button,
    Chip,
    Dialog,
    InputText,
    Message,
    ProgressBar,
    ProgressSpinner,
    Textarea,
    ToggleSwitch,
  },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      items: [] as Item[],
      query: "",
      editorOpen: false,
      editing: undefined as Item | undefined,
      name: "",
      description: "",
      error: "",
      packs: [] as CompendiumSource[],
      registry: [] as CompendiumRepository[],
      packsOpen: false,
      importing: false,
      itemsLoading: false,
      repositoriesLoading: false,
      importProgress: "",
      importProgressCurrent: undefined as number | undefined,
      importProgressTotal: undefined as number | undefined,
      repositoryQuery: "",
      unsubscribeRepositoryImport: undefined as (() => void) | undefined,
    };
  },
  computed: {
    campaignId(): number {
      return Number(this.$route.params.id);
    },
    filtered(): Item[] {
      const needle = this.query.trim().toLowerCase();
      if (!needle) {
        return this.items;
      }
      return this.items.filter((item) =>
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
    },
    filteredRepositories(): CompendiumRepository[] {
      const words = this.repositoryQuery
        .toLowerCase()
        .trim()
        .split(/\s+/)
        .filter(Boolean);
      if (!words.length) {
        return this.registry;
      }
      return this.registry.filter((repository) => {
        const name = repository.name.toLowerCase();
        const description = repository.description.toLowerCase();
        return words.every((word) => name.includes(word) || description.includes(word));
      });
    },
    campaignRefresh(): number {
      return campaignRefreshRevision.value;
    },
  },
  watch: {
    campaignRefresh(): void {
      void this.load();
    },
  },
  methods: {
    summary(item: Item): string {
      return (
        itemSummary(item) ||
        (item.is_imported ? "Imported item" : "Campaign custom item")
      );
    },

    dismissError(open: boolean): void {
      if (!open) {
        this.error = "";
      }
    },

    showSuccess(message: string): void {
      this.$toast.add({
        severity: "success",
        summary: message,
        life: 4_000,
      });
    },

    async load(): Promise<void> {
      this.itemsLoading = true;
      try {
        [this.campaign, this.items, this.packs] = await Promise.all([
          getCampaign(this.campaignId),
          getItems(this.campaignId),
          getCompendiumSources(this.campaignId),
        ]);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load the compendium.";
      } finally {
        this.itemsLoading = false;
      }
    },

    async openPacks(): Promise<void> {
      this.packsOpen = true;
      if (this.registry.length || this.repositoriesLoading) {
        return;
      }
      this.repositoriesLoading = true;
      try {
        this.registry = await getCompendiumRepositories(this.campaignId);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to load registry.";
      } finally {
        this.repositoriesLoading = false;
      }
    },

    async togglePack(pack: CompendiumSource): Promise<void> {
      try {
        if (pack.enabled) {
          await disableCompendiumSource(this.campaignId, pack.id);
        } else {
          await enableCompendiumSource(this.campaignId, pack.id);
        }
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update source.";
      }
    },

    async importRegistryPack(pack: CompendiumRepository): Promise<void> {
      this.importing = true;
      this.importProgress = "Starting import";
      try {
        await startRepositoryImport({
          repositoryId: pack.id,
        });
      } catch (exception) {
        this.importing = false;
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to import repository.";
      }
    },

    repositoryImportEvent(event: RepositoryImportEvent): void {
      if (event.type === "repository.import.started") {
        return;
      }
      if (event.type === "repository.import.progress") {
        this.importProgress = event.message ?? "Importing repository";
        this.importProgressCurrent = event.current ?? undefined;
        this.importProgressTotal = event.total ?? undefined;
        return;
      }
      this.finishRepositoryImport();
      if (event.type === "repository.import.error") {
        this.error = event.detail ?? "Unable to import repository.";
        return;
      }
      this.showSuccess("Repository imported and its sources enabled.");
      void this.load();
    },

    finishRepositoryImport(): void {
      this.importing = false;
      this.importProgressCurrent = undefined;
      this.importProgressTotal = undefined;
    },

    openEditor(item?: Item): void {
      this.editing = item;
      this.name = item?.name ?? "";
      this.description = item?.description ?? "";
      this.editorOpen = true;
    },

    async save(): Promise<void> {
      if (!this.name.trim()) {
        return;
      }
      try {
        if (this.editing) {
          await updateItem(this.campaignId, this.editing.id, {
            name: this.name.trim(),
            description: this.description,
          });
        } else {
          await createItem(this.campaignId, this.name.trim(), this.description);
        }
        this.showSuccess(this.editing ? "Item updated." : "Item created.");
        this.editorOpen = false;
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to save item.";
      }
    },

    async remove(item: Item): Promise<void> {
      try {
        await deleteItem(this.campaignId, item.id);
        this.showSuccess("Item deleted.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to delete item.";
      }
    },
  },
  mounted() {
    this.unsubscribeRepositoryImport = subscribeRepositoryImport(
      this.repositoryImportEvent,
    );
    void this.load();
  },
  beforeUnmount() {
    this.unsubscribeRepositoryImport?.();
  },
});
</script>
