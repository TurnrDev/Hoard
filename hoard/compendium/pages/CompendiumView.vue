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
          Browse every enabled native resource and campaign-custom entry.
        </p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <Button
          icon="mdi mdi-plus"
          label="New item"
          @click="openEditor()"
        />
        <Button
          v-if="campaign?.is_game_master"
          icon="mdi mdi-bookshelf"
          label="Sources"
          outlined
          @click="openPacks"
        />
        <Button
          v-if="campaign?.is_game_master"
          icon="mdi mdi-download"
          label="Export custom content"
          outlined
          :loading="exporting"
          @click="exportCustomContent"
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
      <div class="col-12 col-md-4 col-lg-3">
        <label
          class="d-grid gap-2"
          for="compendium-kind"
        >
          <span class="fw-semibold">Resource type</span>
          <Select
            id="compendium-kind"
            v-model="kind"
            :options="kindOptions"
            option-label="label"
            option-value="value"
            fluid
          />
        </label>
      </div>
      <div class="col-12 col-md-8 col-lg-6">
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
        {{ filtered.length }} matching resources
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
        v-for="entry in filtered"
        :key="entry.id"
        class="col-12 col-md-6 col-xl-4"
      >
        <article class="border rounded-3 p-3 h-100 d-flex flex-column">
          <header>
            <h2 class="h4">{{ entry.name }}</h2>
          </header>
          <p class="small text-body-secondary">
            {{ displayIdentifier(entry.kind) }} · {{ entry.source }}
          </p>
          <div class="flex-grow-1">
            <dl
              v-if="entry.kind === 'spell'"
              class="row g-2 small"
            >
              <div
                v-for="fact in spellFacts(entry)"
                :key="fact.label"
                class="col-6"
              >
                <dt class="text-body-secondary">{{ fact.label }}</dt>
                <dd class="mb-0">{{ fact.value }}</dd>
              </div>
            </dl>
            <p>{{ entry.description || "No description." }}</p>
            <Chip
              v-if="entry.is_custom"
              size="small"
              class="me-1"
            >
              Campaign custom
            </Chip>
            <Chip
              v-if="spellLevel(entry)"
              size="small"
            >
              {{ spellLevel(entry) }}
            </Chip>
          </div>
          <footer
            v-if="campaign?.is_game_master && customItem(entry)"
            class="d-flex gap-2 mt-3"
          >
            <Button
              label="Edit"
              outlined
              @click="editEntry(entry)"
            />
            <Button
              severity="danger"
              label="Delete"
              @click="removeEntry(entry)"
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
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { defineComponent } from "vue";
import {
  createItem,
  deleteItem,
  disableCompendiumSource,
  enableCompendiumSource,
  exportCompendiumCustomContent,
  getCampaign,
  getItems,
  getCompendiumRepositories,
  getCompendiumSources,
  searchCompendiumEntries,
  updateItem,
  type Campaign,
  type Item,
  type CompendiumRepository,
  type CompendiumSource,
  type CompendiumSearchEntry,
} from "@/api";
import { displayIdentifier } from "@/campaigns/display";
import {
  startRepositoryImport,
  subscribeRepositoryImport,
  campaignRefreshRevision,
  type RepositoryImportEvent,
} from "@/realtime";
import { itemSummary } from "@/campaigns/itemPicker";

export default defineComponent({
  components: {
    Button,
    Chip,
    Dialog,
    InputText,
    Message,
    ProgressBar,
    ProgressSpinner,
    Select,
    Textarea,
    ToggleSwitch,
  },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      items: [] as Item[],
      entries: [] as CompendiumSearchEntry[],
      query: "",
      kind: "all",
      kindOptions: [
        { label: "All resources", value: "all" },
        { label: "Spells", value: "spell" },
        { label: "Classes", value: "class" },
        { label: "Species and races", value: "race" },
        { label: "Backgrounds", value: "background" },
        { label: "Feats", value: "feat" },
        { label: "Equipment", value: "item" },
        { label: "Weapons", value: "weapon" },
        { label: "Armour", value: "armor" },
        { label: "Creatures", value: "monster" },
      ],
      exporting: false,
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
    filtered(): CompendiumSearchEntry[] {
      const needle = this.query.trim().toLowerCase();
      return this.entries.filter(
        (entry) =>
          (this.kind === "all" || entry.kind === this.kind) &&
          [entry.name, entry.description, entry.source, entry.kind]
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

    displayIdentifier,

    customItem(entry: CompendiumSearchEntry): Item | undefined {
      return entry.is_custom
        ? this.items.find((item) => item.id === entry.id && !item.is_imported)
        : undefined;
    },

    editEntry(entry: CompendiumSearchEntry): void {
      const item = this.customItem(entry);

      if (item) {
        this.openEditor(item);
      }
    },

    async removeEntry(entry: CompendiumSearchEntry): Promise<void> {
      const item = this.customItem(entry);

      if (item) {
        await this.remove(item);
      }
    },

    spellLevel(entry: CompendiumSearchEntry): string {
      if (entry.kind !== "spell") {
        return "";
      }
      const level = Number(entry.details.level ?? 0);

      return level === 0 ? "Cantrip" : `Level ${level}`;
    },

    spellFacts(entry: CompendiumSearchEntry): Array<{
      label: string;
      value: string;
    }> {
      return [
        ["Casting time", entry.details.casting_time],
        ["Range", entry.details.range],
        ["Target", entry.details.target],
        ["Components", entry.details.components],
        ["Materials", entry.details.materials],
        ["Duration", entry.details.duration],
        ["School", entry.details.school],
        ["Classes", entry.details.classes],
      ].flatMap(([label, value]) => {
        if (value === undefined || value === null || value === "") {
          return [];
        }

        return [
          {
            label: String(label),
            value: Array.isArray(value) ? value.join(", ") : String(value),
          },
        ];
      });
    },

    async exportCustomContent(): Promise<void> {
      if (!this.campaign?.is_game_master) {
        return;
      }

      this.exporting = true;
      try {
        const result = await exportCompendiumCustomContent(this.campaignId);
        const bytes = Uint8Array.from(atob(result.content_base64), (value) =>
          value.charCodeAt(0),
        );
        const url = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }));
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = result.filename;
        anchor.click();
        URL.revokeObjectURL(url);
        this.showSuccess(`Exported ${result.resource_count} custom resources.`);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to export custom content.";
      } finally {
        this.exporting = false;
      }
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
        [this.campaign, this.items, this.packs, this.entries] = await Promise.all([
          getCampaign(this.campaignId),
          getItems(this.campaignId),
          getCompendiumSources(this.campaignId),
          searchCompendiumEntries(this.campaignId, "all"),
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
      if (!this.campaign?.is_game_master) {
        return;
      }

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
