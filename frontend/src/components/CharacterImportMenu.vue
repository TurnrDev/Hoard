<script setup lang="ts">
import { computed, ref } from "vue";
import {
  commitCahImport,
  cancelCahImport,
  previewCahImport,
  type CahPreview,
  type Calculation,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";
import CalculationBreakdown from "./CalculationBreakdown.vue";
import ItemPickerDialog from "./ItemPickerDialog.vue";

const props = defineProps<{
  contextId: number;
  characterId: number;
  items?: Item[];
  itemsLoading?: boolean;
}>();
const emit = defineEmits<{ completed: []; error: [message: string] }>();
const open = ref(false);
const file = ref<File>();
const preview = ref<CahPreview>();
const busy = ref(false);
const fieldErrors = ref<Record<string, string>>({});
const jsonFieldValues = ref<Record<string, string>>({});
const hasFieldErrors = computed(() =>
  preview.value?.field_changes.some(
    (change) => change.enabled && Boolean(fieldErrors.value[change.field]),
  ),
);
const skills = [
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
];
const proficiencyChoices = [
  { title: "None", value: "none" },
  { title: "Half proficiency", value: "half" },
  { title: "Proficient", value: "proficient" },
  { title: "Expertise", value: "expertise" },
];
const candidates = computed<PickerCandidate[]>(() =>
  (props.items ?? []).map((item) => ({ item })),
);

type CalculationRow = {
  key: string;
  label: string;
  before: Calculation;
  after: Calculation;
};
type CalculationGroup = { key: string; label: string; rows: CalculationRow[] };

function title(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isCalculation(value: unknown): value is Calculation {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Calculation).value === "number" &&
    Array.isArray((value as Calculation).components)
  );
}

const importChanges = computed(() => {
  const before = preview.value?.calculated_before;
  const after = preview.value?.calculated_after;
  if (!before || !after) return [];
  const groups: CalculationGroup[] = [];
  for (const [groupKey, afterValue] of Object.entries(after)) {
    const beforeValue = before[groupKey];
    const rows: CalculationRow[] = [];
    if (isCalculation(afterValue) && isCalculation(beforeValue)) {
      if (JSON.stringify(afterValue) !== JSON.stringify(beforeValue)) {
        rows.push({
          key: groupKey,
          label: title(groupKey),
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
          isCalculation(nextCalculation) &&
          isCalculation(previousCalculation) &&
          JSON.stringify(nextCalculation) !== JSON.stringify(previousCalculation)
        ) {
          rows.push({
            key: `${groupKey}-${rowKey}`,
            label: title(rowKey),
            before: previousCalculation,
            after: nextCalculation,
          });
        }
      }
    }
    if (rows.length) groups.push({ key: groupKey, label: title(groupKey), rows });
  }
  return groups;
});

function setMatch(line: CahPreview["inventory"][number], value?: number): void {
  line.matched_item_id = value ?? null;
}

function matchStatus(line: CahPreview["inventory"][number]): {
  color: string;
  text: string;
} {
  if (line.matched_item_id === null) {
    return { color: "warning", text: "Will create a campaign item" };
  }
  if (line.matched_item_id === line.suggested_item_id) {
    return { color: "success", text: "Automatically matched" };
  }
  return { color: "info", text: "Manually matched" };
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Empty";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return entries.length
      ? entries.map(([key, entry]) => `${title(key)}: ${String(entry)}`).join(", ")
      : "None";
  }
  return String(value);
}

function proficiencyValues(value: unknown): Record<string, string> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? Object.fromEntries(
        Object.entries(value).map(([skill, proficiency]) => [
          skill,
          String(proficiency),
        ]),
      )
    : {};
}

function proficiencySummary(value: unknown): string {
  const values = proficiencyValues(value);
  const selected = skills.filter((skill) => values[skill] && values[skill] !== "none");
  return selected.length
    ? selected.map((skill) => `${title(skill)}: ${values[skill]}`).join(" · ")
    : "No skill proficiencies";
}

function setSkillProficiency(
  change: CahPreview["field_changes"][number],
  skill: string,
  proficiency: string | null,
): void {
  change.after = {
    ...proficiencyValues(change.after),
    [skill]: proficiency ?? "none",
  };
}

function editableJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function setNumberField(
  change: CahPreview["field_changes"][number],
  value: string | number | null,
): void {
  const number = Number(value);
  if (Number.isFinite(number)) change.after = number;
}

function setJsonField(
  change: CahPreview["field_changes"][number],
  value: string,
): void {
  jsonFieldValues.value[change.field] = value;
  try {
    change.after = JSON.parse(value);
    delete fieldErrors.value[change.field];
  } catch {
    fieldErrors.value[change.field] = "Enter valid JSON to override this value.";
  }
}

function importFields(): Record<string, unknown> {
  if (!preview.value) return {};
  return Object.fromEntries(
    preview.value.field_changes
      .filter((change) => change.enabled)
      .map((change) => [change.field, change.after]),
  );
}

function excludedFields(): string[] {
  return (preview.value?.field_changes ?? [])
    .filter((change) => !change.enabled)
    .map((change) => change.field);
}

function collectionChoices(): Record<string, boolean> {
  return Object.fromEntries(
    (preview.value?.collection_changes ?? []).map((change) => [
      change.collection,
      Boolean(change.enabled),
    ]),
  );
}

async function loadPreview(): Promise<void> {
  if (!file.value) return;
  busy.value = true;
  try {
    const nextPreview = await previewCahImport(
      props.contextId,
      props.characterId,
      file.value,
    );
    nextPreview.field_changes.forEach((change) => (change.enabled = true));
    nextPreview.collection_changes.forEach((change) => (change.enabled = true));
    fieldErrors.value = {};
    jsonFieldValues.value = Object.fromEntries(
      nextPreview.field_changes
        .filter((change) => typeof change.after === "object")
        .map((change) => [change.field, editableJson(change.after)]),
    );
    preview.value = nextPreview;
  } catch (exception) {
    emit(
      "error",
      exception instanceof Error ? exception.message : "Unable to preview import.",
    );
  } finally {
    busy.value = false;
  }
}

async function commit(): Promise<void> {
  if (!preview.value) return;
  busy.value = true;
  try {
    await commitCahImport(
      props.contextId,
      preview.value.token,
      props.characterId,
      preview.value.inventory.map((line) => ({
        line_id: line.line_id,
        action: line.action,
        quantity: line.quantity,
        ...(line.matched_item_id ? { item_id: line.matched_item_id } : {}),
      })),
      importFields(),
      excludedFields(),
      collectionChoices(),
    );
    open.value = false;
    preview.value = undefined;
    file.value = undefined;
    emit("completed");
  } catch (exception) {
    emit("error", exception instanceof Error ? exception.message : "Unable to import.");
  } finally {
    busy.value = false;
  }
}

async function cancel(): Promise<void> {
  if (preview.value) {
    try {
      await cancelCahImport(props.contextId, preview.value.token);
    } catch {
      // The short-lived server record will expire even if cancellation cannot connect.
    }
  }
  preview.value = undefined;
  file.value = undefined;
  open.value = false;
}
</script>

<template>
  <v-menu>
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        variant="tonal"
        append-icon="mdi-menu-down"
      >
        Import from …
      </v-btn>
    </template>
    <v-list>
      <v-list-item @click="open = true">
        <template #prepend>
          <v-avatar
            size="28"
            image="/static/import-icons/5e-companion.png"
          />
        </template>
        <v-list-item-title>5e Companion</v-list-item-title>
      </v-list-item>
      <v-list-item disabled>
        <template #prepend>
          <v-avatar
            size="28"
            image="/static/import-icons/rpg-companion.png"
          />
        </template>
        <v-list-item-title>RPG Companion</v-list-item-title>
        <v-list-item-subtitle>Coming soon</v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-menu>
  <v-dialog
    v-model="open"
    max-width="1100"
    scrollable
  >
    <v-card title="Import from 5e Companion">
      <v-card-text>
        <v-file-input
          v-model="file"
          accept=".cah"
          label="CAH export"
        />
        <v-btn
          :disabled="!file"
          :loading="busy"
          @click="loadPreview"
        >
          Preview import
        </v-btn>
        <template v-if="preview">
          <v-alert
            type="info"
            variant="tonal"
            class="mt-4"
          >
            Every imported field and sheet section can be included, skipped, or
            overridden below. Clear an equipment match to create a campaign-local item
            from the 5e Companion entry.
          </v-alert>
          <v-alert
            v-if="preview.warnings.length"
            type="warning"
            class="mt-4"
          >
            <div
              v-for="warning in preview.warnings"
              :key="warning"
            >
              {{ warning }}
            </div>
          </v-alert>
          <section
            v-if="preview.field_changes.length"
            class="mt-6"
          >
            <h3 class="text-h6 mb-3">Character changes</h3>
            <v-table
              density="compact"
              class="import-fields-table"
            >
              <thead>
                <tr>
                  <th class="checkbox-column">Import</th>
                  <th>Field</th>
                  <th>Before</th>
                  <th>Import value</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="change in preview.field_changes"
                  :key="change.field"
                >
                  <td class="checkbox-column">
                    <v-checkbox-btn
                      v-model="change.enabled"
                      color="primary"
                      :aria-label="`Import ${title(change.field)}`"
                    />
                  </td>
                  <th>{{ title(change.field) }}</th>
                  <td class="text-medium-emphasis">
                    {{
                      change.field === "skill_proficiencies"
                        ? proficiencySummary(change.before)
                        : formatValue(change.before)
                    }}
                  </td>
                  <td class="py-2">
                    <template v-if="change.enabled">
                      <v-text-field
                        v-if="typeof change.after === 'string'"
                        v-model="change.after"
                        density="compact"
                        hide-details
                      />
                      <v-text-field
                        v-else-if="typeof change.after === 'number'"
                        :model-value="change.after"
                        type="number"
                        density="compact"
                        hide-details
                        @update:model-value="setNumberField(change, $event)"
                      />
                      <v-row
                        v-else-if="change.field === 'skill_proficiencies'"
                        dense
                      >
                        <v-col
                          v-for="skill in skills"
                          :key="skill"
                          cols="12"
                          sm="6"
                        >
                          <v-select
                            :model-value="
                              proficiencyValues(change.after)[skill] ?? 'none'
                            "
                            :items="proficiencyChoices"
                            :label="title(skill)"
                            density="compact"
                            hide-details
                            @update:model-value="
                              setSkillProficiency(change, skill, $event)
                            "
                          />
                        </v-col>
                      </v-row>
                      <v-textarea
                        v-else
                        :model-value="
                          jsonFieldValues[change.field] ?? editableJson(change.after)
                        "
                        density="compact"
                        auto-grow
                        rows="2"
                        :error-messages="fieldErrors[change.field]"
                        hint="JSON override"
                        persistent-hint
                        @update:model-value="setJsonField(change, $event)"
                      />
                    </template>
                    <span
                      v-else
                      class="text-medium-emphasis"
                    >
                      Skipped
                    </span>
                  </td>
                </tr>
              </tbody>
            </v-table>
          </section>
          <section
            v-if="preview.collection_changes.length"
            class="mt-6"
          >
            <h3 class="text-h6 mb-3">Sheet content</h3>
            <v-alert
              v-if="
                preview.collection_changes.some((change) => change.before_count > 0)
              "
              type="warning"
              variant="tonal"
              class="mb-3"
            >
              Existing content in these sections will be replaced. Inventory is added
              through the ledger and is not cleared.
            </v-alert>
            <v-row dense>
              <v-col
                v-for="change in preview.collection_changes"
                :key="change.collection"
                cols="12"
                sm="6"
              >
                <v-card
                  variant="tonal"
                  class="h-100"
                >
                  <v-card-title class="text-subtitle-1">
                    {{ title(change.collection) }}
                  </v-card-title>
                  <v-card-subtitle>
                    {{ change.before_count }} existing →
                    {{ change.after_count }} imported
                  </v-card-subtitle>
                  <v-card-text>
                    <div class="d-flex align-center mb-3">
                      <v-checkbox-btn
                        v-model="change.enabled"
                        color="primary"
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
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </section>
          <section class="mt-6">
            <div class="d-flex align-center mb-3">
              <h3 class="text-h6">Equipment</h3>
              <v-spacer />
              <span class="text-caption text-medium-emphasis">
                {{ preview.inventory.length }} imported lines
              </span>
            </div>
            <v-card
              v-for="line in preview.inventory"
              :key="line.line_id"
              variant="outlined"
              class="mb-3"
            >
              <v-card-title class="d-flex flex-wrap align-center ga-2 pb-0">
                <span>{{ line.name }}</span>
                <v-chip
                  size="small"
                  :color="matchStatus(line).color"
                  variant="tonal"
                >
                  {{ matchStatus(line).text }}
                </v-chip>
                <v-chip
                  v-if="line.equipped"
                  size="small"
                  variant="outlined"
                >
                  Equipped
                </v-chip>
              </v-card-title>
              <v-card-text>
                <p
                  v-if="line.description"
                  class="text-body-2 text-medium-emphasis mb-3"
                >
                  {{ line.description }}
                </p>
                <v-row dense>
                  <v-col
                    cols="12"
                    sm="3"
                  >
                    <v-text-field
                      v-model.number="line.quantity"
                      type="number"
                      min="1"
                      density="compact"
                      label="Quantity"
                    />
                  </v-col>
                  <v-col
                    cols="12"
                    sm="3"
                  >
                    <v-select
                      v-model="line.action"
                      density="compact"
                      label="Action"
                      :items="[
                        { title: 'Add', value: 'add' },
                        { title: 'Leave untouched', value: 'leave' },
                      ]"
                    />
                  </v-col>
                  <v-col
                    cols="12"
                    sm="6"
                  >
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
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </section>
          <section
            v-if="importChanges.length"
            class="mt-6"
          >
            <h3 class="text-h6 mb-3">Calculated changes</h3>
            <v-card
              v-for="group in importChanges"
              :key="group.key"
              variant="outlined"
              class="mb-3"
            >
              <v-card-title class="text-subtitle-1">{{ group.label }}</v-card-title>
              <v-card-text>
                <div
                  v-for="row in group.rows"
                  :key="row.key"
                  class="calculation-comparison"
                >
                  <div class="font-weight-medium calculation-label">
                    {{ row.label }}
                  </div>
                  <CalculationBreakdown
                    :calculation="row.before"
                    label="Before"
                    expanded
                  />
                  <v-icon
                    class="calculation-arrow"
                    color="primary"
                  >
                    mdi-arrow-right
                  </v-icon>
                  <CalculationBreakdown
                    :calculation="row.after"
                    label="After import"
                    expanded
                  />
                </div>
              </v-card-text>
            </v-card>
          </section>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancel">Cancel</v-btn>
        <v-btn
          color="primary"
          :disabled="!preview || hasFieldErrors"
          :loading="busy"
          @click="commit"
        >
          Import
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.checkbox-column {
  width: 56px;
}

.import-fields-table :deep(table) {
  table-layout: fixed;
  width: 100%;
}

.import-fields-table :deep(th:nth-child(2)) {
  width: 14%;
}

.import-fields-table :deep(td:nth-child(3)) {
  width: 28%;
  overflow-wrap: anywhere;
}

.import-fields-table :deep(td:nth-child(4)) {
  width: 52%;
}

.calculation-comparison {
  align-items: start;
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(110px, 0.6fr) minmax(180px, 1fr) auto minmax(
      180px,
      1fr
    );
  padding: 12px 0;
}

.calculation-comparison + .calculation-comparison {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.calculation-label {
  padding-top: 20px;
}

.calculation-arrow {
  align-self: center;
}

@media (max-width: 700px) {
  .calculation-comparison {
    grid-template-columns: 1fr;
  }

  .calculation-label {
    padding-top: 0;
  }

  .calculation-arrow {
    transform: rotate(90deg);
  }
}
</style>
