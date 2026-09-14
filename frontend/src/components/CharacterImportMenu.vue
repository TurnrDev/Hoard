<template>
  <div class="character-import-menu">
    <Button
      outlined
      @click="open = true"
    >
      <span
        class="mdi mdi-import"
        aria-hidden="true"
      />
      Import from 5e Companion
    </Button>
  </div>
  <Dialog
    v-model:visible="open"
    class="character-import-dialog d-flex flex-column overflow-hidden"
    header="Import from 5e Companion"
    modal
    :closable="!busy"
    :close-on-escape="!busy"
    :style="{ width: 'min(69rem, calc(100vw - 2rem))' }"
  >
    <section class="d-grid gap-3">
      <div>
        <label
          class="form-label fw-semibold"
          for="character-import-file"
        >
          5e Companion export
        </label>
        <input
          id="character-import-file"
          ref="fileInput"
          class="form-control"
          type="file"
          accept=".cah"
          :disabled="busy"
          aria-describedby="character-import-file-help"
          @change="selectImportFile"
        />
        <div
          id="character-import-file-help"
          class="form-text"
        >
          Choose a .cah export. Its contents will be previewed before anything is
          imported.
        </div>
        <div
          v-if="busy && !preview"
          class="d-flex align-items-center gap-2 mt-3"
          role="status"
          aria-live="polite"
        >
          <span
            class="spinner-border spinner-border-sm"
            aria-hidden="true"
          />
          Preparing preview…
        </div>
        <Message
          v-if="previewError"
          severity="error"
          class="mt-3"
        >
          {{ previewError }}
        </Message>
        <template v-if="preview">
          <Message
            severity="info"
            class="mt-4"
          >
            Every imported field and sheet section can be included, skipped, or
            overridden below. Clear an equipment match to create a campaign-local item
            from the 5e Companion entry.
          </Message>
          <Message
            v-if="preview.warnings.length"
            severity="warn"
            class="mt-4"
          >
            <div
              v-for="warning in preview.warnings"
              :key="warning"
            >
              {{ warning }}
            </div>
          </Message>
          <section
            v-if="preview.field_changes.length"
            class="mt-5"
          >
            <h3 class="h5 mb-3">Character changes</h3>
            <div class="table-responsive">
              <table class="table table-striped align-middle import-fields-table mb-0">
                <caption class="visually-hidden">
                  Character fields available to import
                </caption>
                <thead>
                  <tr>
                    <th
                      scope="col"
                      class="checkbox-column"
                    >
                      Import
                    </th>
                    <th scope="col">Field</th>
                    <th scope="col">Before</th>
                    <th scope="col">Import value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="change in preview.field_changes"
                    :key="change.field"
                  >
                    <td class="checkbox-column">
                      <Checkbox
                        v-model="change.enabled"
                        binary
                        :aria-label="`Import ${title(change.field)}`"
                      />
                    </td>
                    <th scope="row">{{ title(change.field) }}</th>
                    <td class="text-body-secondary">
                      {{
                        change.field === "skill_proficiencies"
                          ? proficiencySummary(change.before)
                          : formatValue(change.before)
                      }}
                    </td>
                    <td class="py-2">
                      <template v-if="change.enabled">
                        <div
                          v-if="change.field === 'skill_proficiencies'"
                          class="row g-3"
                        >
                          <div
                            v-for="skill in skills"
                            :key="skill"
                            class="col-12 col-sm-6"
                          >
                            <SkillProficiencyPicker
                              :model-value="
                                proficiencyValues(change.after)[skill] ?? 'none'
                              "
                              :input-id="`import-skill-${skill}`"
                              :label="title(skill)"
                              @update:model-value="
                                setSkillProficiency(change, skill, $event)
                              "
                            />
                          </div>
                        </div>
                        <fieldset
                          v-else-if="change.field === 'languages'"
                          class="border-0 p-0 m-0"
                        >
                          <legend class="visually-hidden">Imported languages</legend>
                          <div
                            v-for="(language, index) in stringListValues(change.after)"
                            :key="index"
                            class="input-group mb-2"
                          >
                            <InputText
                              :model-value="language"
                              :aria-label="`Language ${index + 1}`"
                              @update:model-value="
                                setStringListItem(change, index, $event)
                              "
                            />
                            <Button
                              icon="mdi mdi-delete-outline"
                              severity="danger"
                              outlined
                              :aria-label="`Remove language ${language || index + 1}`"
                              @click="removeStringListItem(change, index)"
                            />
                          </div>
                          <Button
                            icon="mdi mdi-plus"
                            label="Add language"
                            size="small"
                            outlined
                            @click="addStringListItem(change)"
                          />
                        </fieldset>
                        <fieldset
                          v-else-if="change.field === 'spell_slot_current'"
                          class="border-0 p-0 m-0"
                        >
                          <legend class="visually-hidden">
                            Current spell slots by spell level
                          </legend>
                          <div class="row row-cols-2 row-cols-md-4 g-2">
                            <div
                              v-for="level in spellSlotLevels"
                              :key="level.key"
                              class="col"
                            >
                              <label
                                class="form-label small fw-semibold"
                                :for="`import-spell-slot-${level.key}`"
                              >
                                {{ level.label }}
                              </label>
                              <InputNumber
                                :input-id="`import-spell-slot-${level.key}`"
                                :model-value="spellSlotValues(change.after)[level.key]"
                                :min="0"
                                :use-grouping="false"
                                show-buttons
                                button-layout="vertical"
                                increment-button-icon="mdi mdi-chevron-up"
                                decrement-button-icon="mdi mdi-chevron-down"
                                fluid
                                @update:model-value="
                                  setSpellSlot(change, level.key, $event)
                                "
                              />
                            </div>
                          </div>
                        </fieldset>
                        <div
                          v-else-if="typeof change.after === 'boolean'"
                          class="d-flex align-items-center gap-2"
                        >
                          <Checkbox
                            :input-id="`import-field-${change.field}`"
                            :model-value="change.after"
                            binary
                            @update:model-value="setBooleanField(change, $event)"
                          />
                          <label :for="`import-field-${change.field}`">
                            {{ change.after ? "Yes" : "No" }}
                          </label>
                        </div>
                        <InputText
                          v-else-if="typeof change.after === 'string'"
                          v-model="change.after"
                          :aria-label="`Imported ${title(change.field)}`"
                          fluid
                        />
                        <InputNumber
                          v-else-if="typeof change.after === 'number'"
                          :model-value="change.after"
                          :aria-label="`Imported ${title(change.field)}`"
                          :min="numberFieldMinimum(change.field)"
                          :use-grouping="false"
                          show-buttons
                          button-layout="horizontal"
                          increment-button-icon="mdi mdi-plus"
                          decrement-button-icon="mdi mdi-minus"
                          fluid
                          @update:model-value="setNumberField(change, $event)"
                        />
                        <Textarea
                          v-else
                          :model-value="
                            jsonFieldValues[change.field] ?? editableJson(change.after)
                          "
                          auto-resize
                          rows="2"
                          :invalid="Boolean(fieldErrors[change.field])"
                          fluid
                          @update:model-value="setJsonField(change, $event)"
                        />
                        <span
                          v-if="fieldErrors[change.field]"
                          class="form-text text-danger"
                        >
                          {{ fieldErrors[change.field] }}
                        </span>
                        <span
                          v-else-if="typeof change.after === 'object'"
                          class="form-text"
                        >
                          JSON override
                        </span>
                      </template>
                      <span
                        v-else
                        class="text-body-secondary"
                      >
                        Skipped
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
          <section
            v-if="preview.collection_changes.length"
            class="mt-5"
          >
            <h3 class="h5 mb-3">Sheet content</h3>
            <Message
              v-if="
                preview.collection_changes.some((change) => change.before_count > 0)
              "
              severity="warn"
              class="mb-3"
            >
              Existing content in these sections will be replaced. Inventory is added
              through the ledger and is not cleared.
            </Message>
            <div class="row g-3">
              <div
                v-for="change in preview.collection_changes"
                :key="change.collection"
                class="col-12 col-sm-6"
              >
                <section class="h-100 border rounded-3 bg-body-tertiary p-3">
                  <header class="h6">
                    {{ title(change.collection) }}
                  </header>
                  <p>
                    {{ change.before_count }} existing →
                    {{ change.after_count }} imported
                  </p>
                  <div>
                    <div class="d-flex align-items-center gap-2 mb-3">
                      <Checkbox
                        v-model="change.enabled"
                        binary
                        :aria-label="`Replace ${title(change.collection)} with imported content`"
                      />
                      <span>Replace this section with imported content</span>
                    </div>
                    <template v-if="change.names.length">
                      {{ change.names.join(", ") }}
                      <span v-if="change.remaining_count">
                        and {{ change.remaining_count }} more
                      </span>
                    </template>
                  </div>
                </section>
              </div>
            </div>
          </section>
          <section class="mt-5">
            <div class="d-flex align-items-center justify-content-between gap-3 mb-3">
              <h3 class="h5 mb-0">Equipment</h3>
              <span class="small text-body-secondary">
                {{ preview.inventory.length }} imported lines
              </span>
            </div>
            <section
              v-for="line in preview.inventory"
              :key="line.line_id"
              class="border rounded-3 p-3 mb-3"
            >
              <header class="d-flex flex-wrap align-items-center gap-2 pb-0">
                <span>{{ line.name }}</span>
                <Tag
                  :severity="matchStatus(line).severity"
                  :value="matchStatus(line).text"
                />
                <Tag
                  v-if="line.equipped"
                  severity="secondary"
                  value="Equipped"
                />
              </header>
              <div>
                <p
                  v-if="line.description"
                  class="small text-body-secondary mb-3"
                >
                  {{ line.description }}
                </p>
                <div class="row g-3">
                  <div class="col-12 col-sm-3">
                    <label
                      class="form-label small fw-semibold"
                      :for="`import-quantity-${line.line_id}`"
                    >
                      Quantity
                    </label>
                    <InputNumber
                      :input-id="`import-quantity-${line.line_id}`"
                      v-model="line.quantity"
                      :min="1"
                      :use-grouping="false"
                      show-buttons
                      button-layout="horizontal"
                      increment-button-icon="mdi mdi-plus"
                      decrement-button-icon="mdi mdi-minus"
                      fluid
                    />
                  </div>
                  <div class="col-12 col-sm-3">
                    <label
                      class="form-label small fw-semibold"
                      :for="`import-action-${line.line_id}`"
                    >
                      Action
                    </label>
                    <Select
                      :input-id="`import-action-${line.line_id}`"
                      v-model="line.action"
                      :options="[
                        { title: 'Add', value: 'add' },
                        { title: 'Leave untouched', value: 'leave' },
                      ]"
                      option-label="title"
                      option-value="value"
                      fluid
                    />
                  </div>
                  <div class="col-12 col-sm-6">
                    <ItemPickerDialog
                      :model-value="line.matched_item_id ?? undefined"
                      :candidates="candidates"
                      label="Compendium match"
                      :title="`Match ${line.name}`"
                      :initial-search="line.name"
                      :initial-category="line.kind"
                      :disabled="line.action === 'leave'"
                      :loading="itemsLoading"
                      compact
                      no-data-text="No enabled Compendium items match these filters. Reset the filters to search the full equipment catalogue."
                      @update:model-value="setMatch(line, $event)"
                    />
                  </div>
                </div>
              </div>
            </section>
          </section>
          <section
            v-if="importChanges.length"
            class="mt-5"
          >
            <h3 class="h5 mb-3">Calculated changes</h3>
            <section
              v-for="group in importChanges"
              :key="group.key"
              class="border rounded-3 p-3 mb-3"
            >
              <header class="h6">{{ group.label }}</header>
              <div>
                <div
                  v-for="row in group.rows"
                  :key="row.key"
                  class="calculation-comparison d-grid align-items-start gap-3 py-3"
                >
                  <div class="fw-medium calculation-label pt-0 pt-md-4">
                    {{ row.label }}
                  </div>
                  <CalculationBreakdown
                    :calculation="row.before"
                    label="Before"
                    expanded
                  />
                  <span
                    class="mdi mdi-arrow-right calculation-arrow align-self-center fs-4 text-body-secondary"
                    aria-hidden="true"
                  />
                  <CalculationBreakdown
                    :calculation="row.after"
                    label="After import"
                    expanded
                  />
                </div>
              </div>
            </section>
          </section>
        </template>
      </div>
    </section>
    <template #footer>
      <div class="d-flex justify-content-end gap-2 w-100">
        <Button
          :disabled="busy"
          @click="cancel"
        >
          Cancel
        </Button>
        <Button
          :disabled="!preview || hasFieldErrors || busy"
          :loading="busy"
          @click="commit"
        >
          Import
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script lang="ts">
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { defineComponent } from "vue";
import {
  cancelCahImport,
  commitCahImport,
  previewCahImport,
  type CahPreview,
  type Calculation,
  type Item,
} from "../api";
import { displayIdentifier } from "../display";
import type { PickerCandidate } from "../itemPicker";
import CalculationBreakdown from "./CalculationBreakdown.vue";
import ItemPickerDialog from "./ItemPickerDialog.vue";
import SkillProficiencyPicker from "./SkillProficiencyPicker.vue";

type CalculationRow = {
  key: string;
  label: string;
  before: Calculation;
  after: Calculation;
};

type CalculationGroup = {
  key: string;
  label: string;
  rows: CalculationRow[];
};

export default defineComponent({
  props: {
    contextId: { type: Number, required: true },
    characterId: { type: Number, required: true },
    items: { type: Array as import("vue").PropType<Item[]>, default: undefined },
    itemsLoading: { type: Boolean, default: false },
  },
  emits: ["completed", "error"],
  components: {
    Button,
    Checkbox,
    Dialog,
    InputNumber,
    InputText,
    Message,
    Select,
    Tag,
    Textarea,
    CalculationBreakdown,
    ItemPickerDialog,
    SkillProficiencyPicker,
  },
  data() {
    return {
      open: false,
      file: undefined as File | undefined,
      preview: undefined as CahPreview | undefined,
      previewError: "",
      busy: false,
      fieldErrors: {} as Record<string, string>,
      jsonFieldValues: {} as Record<string, string>,
      skills: [
        "acrobatics",
        "animal_handling",
        "arcana",
        "athletics",
        "deception",
        "history",
        "insight",
        "intimidation",
        "investigation",
        "medicine",
        "nature",
        "perception",
        "performance",
        "persuasion",
        "religion",
        "sleight_of_hand",
        "stealth",
        "survival",
      ],
      spellSlotLevels: [
        { key: "first", label: "1st" },
        { key: "second", label: "2nd" },
        { key: "third", label: "3rd" },
        { key: "fourth", label: "4th" },
        { key: "fifth", label: "5th" },
        { key: "sixth", label: "6th" },
        { key: "seventh", label: "7th" },
        { key: "eighth", label: "8th" },
        { key: "ninth", label: "9th" },
      ],
    };
  },
  computed: {
    candidates(): PickerCandidate[] {
      return (this.items ?? []).map((item) => ({ item }));
    },
    hasFieldErrors(): boolean {
      return Boolean(
        this.preview?.field_changes.some(
          (change) => change.enabled && Boolean(this.fieldErrors[change.field]),
        ),
      );
    },
    importChanges(): CalculationGroup[] {
      const before = this.preview?.calculated_before;
      const after = this.preview?.calculated_after;
      if (!before || !after) {
        return [];
      }
      const groups: CalculationGroup[] = [];
      for (const [groupKey, afterValue] of Object.entries(after)) {
        const beforeValue = before[groupKey];
        const rows: CalculationRow[] = [];
        if (this.isCalculation(afterValue) && this.isCalculation(beforeValue)) {
          if (JSON.stringify(afterValue) !== JSON.stringify(beforeValue)) {
            rows.push({
              key: groupKey,
              label: this.title(groupKey),
              before: beforeValue,
              after: afterValue,
            });
          }
        } else if (
          typeof afterValue === "object" &&
          afterValue !== null &&
          typeof beforeValue === "object" &&
          beforeValue !== null
        ) {
          for (const [rowKey, nextCalculation] of Object.entries(afterValue)) {
            const previousCalculation = (beforeValue as Record<string, Calculation>)[
              rowKey
            ];
            if (
              this.isCalculation(nextCalculation) &&
              this.isCalculation(previousCalculation) &&
              JSON.stringify(nextCalculation) !== JSON.stringify(previousCalculation)
            ) {
              rows.push({
                key: `${groupKey}-${rowKey}`,
                label: this.title(rowKey),
                before: previousCalculation,
                after: nextCalculation,
              });
            }
          }
        }
        if (rows.length) {
          groups.push({ key: groupKey, label: this.title(groupKey), rows });
        }
      }
      return groups;
    },
  },
  methods: {
    title(value: string): string {
      return displayIdentifier(value);
    },

    isCalculation(value: unknown): value is Calculation {
      return (
        typeof value === "object" &&
        value !== null &&
        typeof (value as Calculation).value === "number" &&
        Array.isArray((value as Calculation).components)
      );
    },

    setMatch(line: CahPreview["inventory"][number], value?: number): void {
      line.matched_item_id = value ?? null;
    },

    matchStatus(line: CahPreview["inventory"][number]): {
      severity: "info" | "success" | "warn";
      text: string;
    } {
      if (line.matched_item_id === null) {
        return { severity: "warn", text: "Will create a campaign item" };
      }
      if (line.matched_item_id === line.suggested_item_id) {
        return { severity: "success", text: "Automatically matched" };
      }
      return { severity: "info", text: "Manually matched" };
    },

    formatValue(value: unknown): string {
      if (value === null || value === undefined || value === "") {
        return "Empty";
      }
      if (Array.isArray(value)) {
        return value.length ? value.join(", ") : "None";
      }
      if (typeof value === "boolean") {
        return value ? "Yes" : "No";
      }
      if (typeof value === "object") {
        const entries = Object.entries(value as Record<string, unknown>);
        return entries.length
          ? entries
              .map(([key, entry]) => `${this.title(key)}: ${String(entry)}`)
              .join(", ")
          : "None";
      }
      return String(value);
    },

    stringListValues(value: unknown): string[] {
      if (!Array.isArray(value)) {
        return [];
      }

      return value.filter((entry): entry is string => typeof entry === "string");
    },

    setStringListItem(
      change: CahPreview["field_changes"][number],
      index: number,
      value: string | undefined,
    ): void {
      const values = [...this.stringListValues(change.after)];
      values[index] = value ?? "";
      change.after = values;
    },

    addStringListItem(change: CahPreview["field_changes"][number]): void {
      change.after = [...this.stringListValues(change.after), ""];
    },

    removeStringListItem(
      change: CahPreview["field_changes"][number],
      index: number,
    ): void {
      change.after = this.stringListValues(change.after).filter(
        (_value, valueIndex) => valueIndex !== index,
      );
    },

    spellSlotValues(value: unknown): Record<string, number> {
      if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return {};
      }

      return Object.fromEntries(
        Object.entries(value).flatMap(([level, amount]) => {
          const numericAmount = Number(amount);

          return Number.isFinite(numericAmount) ? [[level, numericAmount]] : [];
        }),
      );
    },

    setSpellSlot(
      change: CahPreview["field_changes"][number],
      level: string,
      value: string | number | null,
    ): void {
      const amount = Number(value);

      change.after = {
        ...this.spellSlotValues(change.after),
        [level]: Number.isFinite(amount) ? Math.max(0, amount) : 0,
      };
    },

    setBooleanField(
      change: CahPreview["field_changes"][number],
      value: boolean | undefined,
    ): void {
      change.after = Boolean(value);
    },

    proficiencyValues(value: unknown): Record<string, string> {
      return typeof value === "object" && value !== null && !Array.isArray(value)
        ? Object.fromEntries(
            Object.entries(value).map(([skill, proficiency]) => [
              skill,
              String(proficiency),
            ]),
          )
        : {};
    },

    proficiencySummary(value: unknown): string {
      const values = this.proficiencyValues(value);
      const selected = this.skills.filter(
        (skill) => values[skill] && values[skill] !== "none",
      );
      return selected.length
        ? selected.map((skill) => `${this.title(skill)}: ${values[skill]}`).join(" · ")
        : "No skill proficiencies";
    },

    setSkillProficiency(
      change: CahPreview["field_changes"][number],
      skill: string,
      proficiency: string | null,
    ): void {
      change.after = {
        ...this.proficiencyValues(change.after),
        [skill]: proficiency ?? "none",
      };
    },

    editableJson(value: unknown): string {
      return JSON.stringify(value, null, 2);
    },

    setNumberField(
      change: CahPreview["field_changes"][number],
      value: string | number | null,
    ): void {
      const number = Number(value);
      if (Number.isFinite(number)) {
        change.after = number;
      }
    },

    numberFieldMinimum(field: string): number | undefined {
      if (
        [
          "base_hp",
          "base_ac",
          "strength",
          "dexterity",
          "constitution",
          "intelligence",
          "wisdom",
          "charisma",
          "npc_level",
        ].includes(field)
      ) {
        return 1;
      }

      if (field === "temporary_hp") {
        return 0;
      }

      return undefined;
    },

    setJsonField(change: CahPreview["field_changes"][number], value: string): void {
      this.jsonFieldValues[change.field] = value;
      try {
        change.after = JSON.parse(value);
        delete this.fieldErrors[change.field];
      } catch {
        this.fieldErrors[change.field] = "Enter valid JSON to override this value.";
      }
    },

    importFields(): Record<string, unknown> {
      if (!this.preview) {
        return {};
      }
      return Object.fromEntries(
        this.preview.field_changes
          .filter((change) => change.enabled)
          .map((change) => [change.field, change.after]),
      );
    },

    excludedFields(): string[] {
      return (this.preview?.field_changes ?? [])
        .filter((change) => !change.enabled)
        .map((change) => change.field);
    },

    collectionChoices(): Record<string, boolean> {
      return Object.fromEntries(
        (this.preview?.collection_changes ?? []).map((change) => [
          change.collection,
          Boolean(change.enabled),
        ]),
      );
    },

    async selectImportFile(event: Event): Promise<void> {
      const input = event.target as HTMLInputElement;
      const selectedFile = input.files?.item(0);

      if (!selectedFile) {
        return;
      }

      this.file = selectedFile;

      await this.loadPreview();
    },

    async loadPreview(): Promise<void> {
      if (!this.file) {
        return;
      }

      this.busy = true;
      this.previewError = "";

      const previousPreview = this.preview;
      this.preview = undefined;

      try {
        if (previousPreview) {
          await cancelCahImport(this.contextId, previousPreview.token);
        }

        const nextPreview = await previewCahImport(
          this.contextId,
          this.characterId,
          this.file,
        );
        nextPreview.field_changes.forEach((change) => (change.enabled = true));
        nextPreview.collection_changes.forEach((change) => (change.enabled = true));
        this.fieldErrors = {};
        this.jsonFieldValues = Object.fromEntries(
          nextPreview.field_changes
            .filter((change) => typeof change.after === "object")
            .map((change) => [change.field, this.editableJson(change.after)]),
        );
        this.preview = nextPreview;
      } catch (exception) {
        this.previewError =
          exception instanceof Error ? exception.message : "Unable to preview import.";
        this.file = undefined;
        this.resetFileInput();
        this.$emit("error", this.previewError);
      } finally {
        this.busy = false;
      }
    },

    async commit(): Promise<void> {
      if (!this.preview) {
        return;
      }
      this.busy = true;
      try {
        await commitCahImport(
          this.contextId,
          this.preview.token,
          this.characterId,
          this.preview.inventory.map((line) => ({
            line_id: line.line_id,
            action: line.action,
            quantity: line.quantity,
            ...(line.matched_item_id ? { item_id: line.matched_item_id } : {}),
          })),
          this.importFields(),
          this.excludedFields(),
          this.collectionChoices(),
        );
        this.open = false;
        this.preview = undefined;
        this.file = undefined;
        this.resetFileInput();
        this.$emit("completed");
      } catch (exception) {
        this.$emit(
          "error",
          exception instanceof Error ? exception.message : "Unable to import.",
        );
      } finally {
        this.busy = false;
      }
    },

    async cancel(): Promise<void> {
      if (this.preview) {
        try {
          await cancelCahImport(this.contextId, this.preview.token);
        } catch {
          // The short-lived server record will expire even if cancellation cannot connect.
        }
      }
      this.preview = undefined;
      this.file = undefined;
      this.previewError = "";
      this.resetFileInput();
      this.open = false;
    },

    resetFileInput(): void {
      const input = this.$refs.fileInput as HTMLInputElement | undefined;

      if (input) {
        input.value = "";
      }
    },
  },
});
</script>

<style scoped>
:deep(.character-import-dialog) {
  max-height: calc(100dvh - 2rem);
}

:deep(.character-import-dialog .p-dialog-content) {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

:deep(.character-import-dialog .p-dialog-footer) {
  flex: 0 0 auto;
  border-top: var(--bs-border-width) var(--bs-border-style) var(--bs-border-color);
}

.checkbox-column {
  width: 56px;
}

.import-fields-table {
  table-layout: fixed;
  width: 100%;
}

.import-fields-table th:nth-child(2) {
  width: 14%;
}

.import-fields-table td:nth-child(3) {
  width: 28%;
  overflow-wrap: anywhere;
}

.import-fields-table td:nth-child(4) {
  width: 52%;
}

.calculation-comparison {
  grid-template-columns: minmax(110px, 0.6fr) minmax(180px, 1fr) auto minmax(
      180px,
      1fr
    );
}

.calculation-comparison + .calculation-comparison {
  border-top: 1px solid var(--hoard-border);
}

@media (max-width: 700px) {
  .calculation-comparison {
    grid-template-columns: 1fr;
  }

  .calculation-arrow {
    transform: rotate(90deg);
  }
}
</style>
