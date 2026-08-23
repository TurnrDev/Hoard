<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  completeCharacterBuilder,
  getBuilderEntry,
  getBuilderDefinition,
  getCharacterBuilder,
  getItems,
  saveCharacterBuilder,
  type BuilderDefinition,
  type BuilderEntry,
  type Character,
  type Item,
} from "../api";
import {
  classLevelAt as allocationClassLevelAt,
  sameClass,
} from "../builderProgression";
import CharacterImportMenu from "../components/CharacterImportMenu.vue";
import CompendiumChoicePicker, {
  type CompendiumChoice,
} from "../components/CompendiumChoicePicker.vue";
import CompendiumEntryPicker from "../components/CompendiumEntryPicker.vue";
import { displayIdentifier } from "../display";

type ClassLevel = {
  level: number;
  class_entry_id?: number;
  class_name: string;
  subclass_identifier: string;
  subclass_name: string;
  is_override: boolean;
};
const abilities = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
] as const;
const equipmentCategories = ["armor", "weapons", "tools"] as const;
const proficiencyOptions = [
  { title: "No proficiency", value: "none" },
  { title: "Half proficiency", value: "half" },
  { title: "Proficient", value: "proficient" },
  { title: "Expertise", value: "expertise" },
];

const route = useRoute();
const router = useRouter();
const contextId = Number(route.params.id);
const characterId = Number(route.params.characterId);
const isEditing = computed(() => route.query.mode === "edit");
const resumeKey = computed(
  () => `hoard:builder:${characterId}:${isEditing.value ? "edit" : "build"}:step`,
);
const step = ref(
  Math.min(6, Math.max(1, Number(localStorage.getItem(resumeKey.value)) || 1)),
);
watch(step, (value) => localStorage.setItem(resumeKey.value, String(value)));
const definition = ref<BuilderDefinition>();
const character = ref<Character>();
const items = ref<Item[]>([]);
const classLevels = ref<ClassLevel[]>([]);
const startingEquipment = ref<string[]>([]);
const raceOverride = ref(false);
const backgroundOverride = ref(false);
const error = ref("");
const busy = ref(false);
const definitionLoading = ref(true);
const draftLoading = ref(true);
const itemsLoading = ref(true);
const loadingEntryIds = ref(new Set<number>());
const entryRequests = new Map<number, Promise<void>>();
const form = ref({
  name: "",
  race: "",
  race_entry_id: undefined as number | undefined,
  subrace_name: "",
  subrace_identifier: "",
  background: "",
  background_entry_id: undefined as number | undefined,
  alignment: "",
  personality_traits: "",
  ideals: "",
  bonds: "",
  flaws: "",
  about: "",
  languages: [] as string[],
  skill_proficiencies: {} as Record<string, string>,
  equipment_proficiencies: {
    armor: [] as string[],
    weapons: [] as string[],
    tools: [] as string[],
  },
  ability_bonuses: {} as Record<string, number>,
  ability_score_adjustments: {} as Record<string, number>,
  strength: 10,
  dexterity: 10,
  constitution: 10,
  intelligence: 10,
  wisdom: 10,
  charisma: 10,
  base_hp: 1,
  hp_ability: "constitution" as (typeof abilities)[number],
  hp_adjustment: 0,
});
const hpModifier = computed(() => {
  const ability = form.value.hp_ability as (typeof abilities)[number];
  const score =
    form.value[ability] +
    (form.value.ability_bonuses[ability] ?? 0) +
    (form.value.ability_score_adjustments[ability] ?? 0);
  return Math.floor((score - 10) / 2);
});
const maxHp = computed(() =>
  Math.max(
    1,
    form.value.base_hp +
      hpModifier.value * (definition.value?.level ?? 1) +
      form.value.hp_adjustment,
  ),
);
const languageText = computed({
  get: () => form.value.languages.join("\n"),
  set: (value: string) => {
    form.value.languages = value
      .split(/\r?\n/)
      .map((entry) => entry.trim())
      .filter(Boolean);
  },
});

function canonicalEntryId(
  kind: "race" | "class" | "background",
  id: number | null | undefined,
): number | undefined {
  if (typeof id !== "number") return undefined;
  const canonical = definition.value?.[kind].find(
    (candidate) => candidate.id === id || (candidate.alias_ids ?? []).includes(id),
  );
  return canonical?.id ?? id;
}

const ruleChoicesLoading = computed(() =>
  [
    form.value.race_entry_id,
    form.value.background_entry_id,
    ...classLevels.value.map((row) => row.class_entry_id),
  ].some((id) => entryLoading(id)),
);

function finalAbility(ability: (typeof abilities)[number]): number {
  return (
    form.value[ability] +
    (form.value.ability_bonuses[ability] ?? 0) +
    (form.value.ability_score_adjustments[ability] ?? 0)
  );
}

async function load(): Promise<void> {
  try {
    const [nextDefinition, draft, nextItems] = await Promise.all([
      getBuilderDefinition(contextId)
        .then((value) => {
          definition.value = value;
          return value;
        })
        .finally(() => (definitionLoading.value = false)),
      getCharacterBuilder(contextId, characterId).finally(
        () => (draftLoading.value = false),
      ),
      getItems(contextId)
        .then((value) => {
          items.value = value;
          return value;
        })
        .finally(() => (itemsLoading.value = false)),
    ]);
    items.value = nextItems;
    const value = draft.character as Character;
    character.value = value;
    Object.assign(form.value, {
      name: value.name,
      race: value.race,
      race_entry_id: canonicalEntryId("race", value.race_entry_id),
      subrace_name: value.subrace,
      background: value.background,
      background_entry_id: canonicalEntryId("background", value.background_entry_id),
      alignment: value.alignment,
      personality_traits: value.personality_traits,
      ideals: value.ideals,
      bonds: value.bonds,
      flaws: value.flaws,
      about: value.about,
      languages: value.languages,
      equipment_proficiencies: value.equipment_proficiencies,
      skill_proficiencies: Object.fromEntries(
        Object.entries(value.sheet.skills).map(([name, row]) => [
          name,
          row.proficiency,
        ]),
      ),
      base_hp: value.sheet.base_hp,
      hp_ability: "constitution",
      strength: value.sheet.abilities.strength.raw,
      dexterity: value.sheet.abilities.dexterity.raw,
      constitution: value.sheet.abilities.constitution.raw,
      intelligence: value.sheet.abilities.intelligence.raw,
      wisdom: value.sheet.abilities.wisdom.raw,
      charisma: value.sheet.abilities.charisma.raw,
    });
    classLevels.value = (draft.class_levels as ClassLevel[]) ?? [];
    for (const row of classLevels.value) {
      row.class_entry_id = canonicalEntryId("class", row.class_entry_id);
    }
    const choices =
      (draft.choices as Array<{
        identifier: string;
        values: string[];
      }>) ?? [];
    startingEquipment.value =
      choices.find((choice) => choice.identifier === "starting_equipment")?.values ??
      [];
    for (let level = 1; level <= nextDefinition.level; level += 1) {
      if (!classLevels.value.some((row) => row.level === level)) {
        classLevels.value.push({
          level,
          class_name: "",
          subclass_identifier: "",
          subclass_name: "",
          is_override: false,
        });
      }
    }
    await Promise.all(
      [
        form.value.race_entry_id,
        form.value.background_entry_id,
        ...classLevels.value.map((row) => row.class_entry_id),
      ]
        .filter((id): id is number => typeof id === "number")
        .map(loadEntryData),
    );
    reconcileSubclassChoices();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to load builder.";
  }
}

function findEntry(id: number): BuilderEntry | undefined {
  return [
    ...(definition.value?.race ?? []),
    ...(definition.value?.class ?? []),
    ...(definition.value?.background ?? []),
  ].find((row) => row.id === id);
}

async function loadEntryData(id?: number | null): Promise<void> {
  if (!id) return;
  const candidate = findEntry(id);
  if (!candidate || candidate.data) return;
  const existing = entryRequests.get(id);
  if (existing) return existing;
  loadingEntryIds.value.add(id);
  const request = getBuilderEntry(contextId, id)
    .then((details) => {
      Object.assign(candidate, details);
    })
    .catch((exception) => {
      error.value =
        exception instanceof Error
          ? exception.message
          : "Unable to load Compendium choices.";
    })
    .finally(() => {
      entryRequests.delete(id);
      loadingEntryIds.value.delete(id);
    });
  entryRequests.set(id, request);
  return request;
}

function entryLoading(id?: number | null): boolean {
  return typeof id === "number" && loadingEntryIds.value.has(id);
}

function entry(
  kind: "race" | "class" | "background",
  id?: number,
): BuilderEntry | undefined {
  return (definition.value?.[kind] as BuilderEntry[] | undefined)?.find(
    (row) => row.id === id,
  );
}

function entryChoices(
  kind: "race" | "class" | "background",
  id: number | undefined,
  key: string,
): CompendiumChoice[] {
  const selected = entry(kind, id);
  const values = selected?.data?.[key];
  if (!selected || !Array.isArray(values)) return [];
  return values
    .map((value): CompendiumChoice | undefined => {
      if (typeof value === "string") {
        return value ? { name: value, source: selected.source } : undefined;
      }
      if (!value || typeof value !== "object") return undefined;
      const choice = value as Record<string, unknown>;
      const name = String(choice.name ?? "").trim();
      if (!name) return undefined;
      return {
        identifier: String(choice.identifier ?? ""),
        name,
        source: String(choice.source ?? selected.source),
        level:
          typeof choice.level === "number" ? choice.level : Number(choice.level) || 1,
      };
    })
    .filter((value): value is CompendiumChoice => Boolean(value));
}

function classSubchoices(row: ClassLevel): CompendiumChoice[] {
  const subclasses = entryChoices("class", row.class_entry_id, "subclasses");
  return subclasses.length
    ? subclasses
    : entryChoices("class", row.class_entry_id, "subchoices");
}

function classLevelAt(row: ClassLevel): number {
  return allocationClassLevelAt(classLevels.value, row);
}

function subclassUnlockLevel(row: ClassLevel): number | undefined {
  const value = entry("class", row.class_entry_id)?.data?.subclass_selection_level;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
}

function isSubclassUnlock(row: ClassLevel): boolean {
  const unlockLevel = subclassUnlockLevel(row);
  return (
    classSubchoices(row).length > 0 &&
    unlockLevel !== undefined &&
    classLevelAt(row) === unlockLevel
  );
}

function chosenSubclass(row: ClassLevel): ClassLevel | undefined {
  return classLevels.value.find(
    (candidate) => sameClass(candidate, row) && Boolean(candidate.subclass_name),
  );
}

function subclassStatus(row: ClassLevel): string {
  const classEntry = entry("class", row.class_entry_id);
  const unlockLevel = subclassUnlockLevel(row);
  if (!classEntry || !classSubchoices(row).length || unlockLevel === undefined) {
    return "No Compendium subclass choice at this class level.";
  }
  const currentClassLevel = classLevelAt(row);
  if (currentClassLevel < unlockLevel) {
    return `Subclass unlocks at ${classEntry.name} level ${unlockLevel}.`;
  }
  const selected = chosenSubclass(row);
  return selected
    ? `${selected.subclass_name} was selected at ${classEntry.name} level ${unlockLevel}.`
    : `Subclass choice is incomplete at ${classEntry.name} level ${unlockLevel}.`;
}

function reconcileSubclassChoices(): void {
  for (const row of classLevels.value) {
    if (!row.class_entry_id) continue;
    const unlockLevel = subclassUnlockLevel(row);
    if (!unlockLevel) continue;
    const matching = classLevels.value.filter((candidate) => sameClass(candidate, row));
    const target = matching[unlockLevel - 1];
    const previous = matching.find((candidate) => candidate.subclass_name);
    if (!target || !previous || target === previous || target.subclass_name) continue;
    target.subclass_identifier = previous.subclass_identifier;
    target.subclass_name = previous.subclass_name;
    previous.subclass_identifier = "";
    previous.subclass_name = "";
  }
}

async function selectClass(
  row: ClassLevel,
  classEntryId: number | undefined,
): Promise<void> {
  if (row.class_entry_id !== classEntryId) {
    row.subclass_identifier = "";
    row.subclass_name = "";
  }
  row.class_entry_id = classEntryId;
  row.class_name = entry("class", classEntryId)?.name ?? "";
  await loadEntryData(classEntryId);
  reconcileSubclassChoices();
}

function selectSubclass(row: ClassLevel, value: string | string[]): void {
  const name = Array.isArray(value) ? String(value[0] ?? "") : value;
  const selected = classSubchoices(row).find((choice) => choice.name === name);
  row.subclass_name = name;
  row.subclass_identifier = selected?.identifier ?? "";
}

function raceSubchoices(): CompendiumChoice[] {
  return entryChoices("race", form.value.race_entry_id, "subchoices");
}

function selectedRuleEntries(): BuilderEntry[] {
  return [
    entry("race", form.value.race_entry_id),
    entry("background", form.value.background_entry_id),
    ...classLevels.value.map((row) => entry("class", row.class_entry_id)),
  ].filter((value): value is BuilderEntry => Boolean(value));
}

function ruleSuggestions(key: string): CompendiumChoice[] {
  const choices = selectedRuleEntries().flatMap((selected) => {
    const values = selected.data?.[key];
    if (!Array.isArray(values)) return [];
    return values.map((name) => ({ name: String(name), source: selected.source }));
  });
  const unique = new Map<string, CompendiumChoice>();
  for (const choice of choices) {
    const previous = unique.get(choice.name);
    unique.set(choice.name, {
      name: choice.name,
      source:
        previous && previous.source !== choice.source
          ? `${previous.source}, ${choice.source}`
          : choice.source,
    });
  }
  return [...unique.values()];
}

function equipmentSuggestionKey(
  category: (typeof equipmentCategories)[number],
): string {
  return `${category === "armor" ? "armor" : category.slice(0, -1)}_proficiencies`;
}

async function save(): Promise<void> {
  busy.value = true;
  try {
    if (raceOverride.value) form.value.race_entry_id = undefined;
    else
      form.value.race =
        entry("race", form.value.race_entry_id)?.name ?? form.value.race;
    if (backgroundOverride.value) form.value.background_entry_id = undefined;
    else
      form.value.background =
        entry("background", form.value.background_entry_id)?.name ??
        form.value.background;
    classLevels.value.forEach((row) => {
      if (row.is_override) row.class_entry_id = undefined;
      else row.class_name = entry("class", row.class_entry_id)?.name ?? row.class_name;
    });
    await saveCharacterBuilder(contextId, characterId, {
      fields: form.value,
      class_levels: classLevels.value,
      choices: [
        {
          level: 1,
          identifier: "starting_equipment",
          kind: "equipment",
          values: startingEquipment.value,
          is_override: true,
        },
      ],
      is_override:
        raceOverride.value ||
        backgroundOverride.value ||
        classLevels.value.some((row) => row.is_override),
    });
  } finally {
    busy.value = false;
  }
}

async function next(): Promise<void> {
  try {
    await save();
    step.value = Math.min(6, step.value + 1);
    localStorage.setItem(resumeKey.value, String(step.value));
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "Unable to save.";
  }
}

async function complete(): Promise<void> {
  try {
    await save();
    if (isEditing.value) {
      localStorage.removeItem(resumeKey.value);
      await router.replace(`/c/${contextId}/characters/${characterId}`);
      return;
    }
    await completeCharacterBuilder(contextId, characterId);
    localStorage.removeItem(resumeKey.value);
    await router.replace(`/c/${contextId}/characters/${characterId}`);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to complete character.";
  }
}

onMounted(load);
</script>

<template>
  <v-container
    class="page-shell"
    style="max-width: 980px"
  >
    <header class="page-heading">
      <div>
        <div class="text-overline">Character builder</div>
        <h1>
          {{
            isEditing
              ? `Edit ${form.name || "character"}`
              : form.name || "New character"
          }}
        </h1>
      </div>
      <CharacterImportMenu
        :context-id="contextId"
        :character-id="characterId"
        :items="items"
        :items-loading="itemsLoading"
        @completed="load"
        @error="(message) => (error = message)"
      />
      <v-btn
        v-if="isEditing"
        :to="`/c/${contextId}/characters/${characterId}`"
        variant="text"
      >
        Cancel
      </v-btn>
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
    <v-progress-linear
      :model-value="(step / 6) * 100"
      class="mb-5"
    />
    <v-card>
      <v-card-title>Step {{ step }} of 6</v-card-title>
      <v-card-text>
        <template v-if="step === 1">
          <v-text-field
            v-model="form.name"
            label="Name"
          />
          <v-select
            v-model="form.alignment"
            label="Alignment"
            :loading="draftLoading"
            :disabled="draftLoading"
            :items="[
              'Lawful Good',
              'Neutral Good',
              'Chaotic Good',
              'Lawful Neutral',
              'True Neutral',
              'Chaotic Neutral',
              'Lawful Evil',
              'Neutral Evil',
              'Chaotic Evil',
            ]"
          />
          <v-textarea
            v-model="form.about"
            label="About (optional)"
          />
          <v-textarea
            v-model="form.personality_traits"
            label="Personality traits (optional)"
          />
          <v-textarea
            v-model="form.ideals"
            label="Ideals (optional)"
          />
          <v-textarea
            v-model="form.bonds"
            label="Bonds (optional)"
          />
          <v-textarea
            v-model="form.flaws"
            label="Flaws (optional)"
          />
        </template>
        <template v-else-if="step === 2">
          <v-switch
            v-model="raceOverride"
            color="warning"
            label="Use a custom race override"
          />
          <CompendiumEntryPicker
            v-if="!raceOverride"
            v-model="form.race_entry_id"
            label="Race"
            :items="definition?.race"
            :loading="definitionLoading || draftLoading"
            :disabled="definitionLoading || draftLoading"
            @update:model-value="loadEntryData"
          />
          <v-text-field
            v-else
            v-model="form.race"
            label="Custom race (override)"
          />
          <CompendiumChoicePicker
            v-model="form.subrace_name"
            :items="raceSubchoices()"
            label="Subrace or custom ancestry choice"
            :loading="draftLoading || entryLoading(form.race_entry_id)"
            :disabled="
              definitionLoading || draftLoading || entryLoading(form.race_entry_id)
            "
          />
          <div class="text-overline mt-4">Raw ability scores</div>
          <v-row>
            <v-col
              v-for="ability in abilities"
              :key="ability"
              cols="6"
              sm="4"
            >
              <v-number-input
                v-model.number="form[ability]"
                control-variant="stacked"
                :label="`${ability} raw`"
              />
              <v-number-input
                v-model.number="form.ability_bonuses[ability]"
                control-variant="stacked"
                label="Ancestry adjustment"
                density="compact"
              />
              <v-number-input
                v-model.number="form.ability_score_adjustments[ability]"
                control-variant="stacked"
                label="Custom override"
                density="compact"
              />
              <div class="text-caption">
                {{ form[ability] }} + {{ form.ability_bonuses[ability] ?? 0 }} +
                {{ form.ability_score_adjustments[ability] ?? 0 }} =
                {{ finalAbility(ability) }}
              </div>
            </v-col>
          </v-row>
        </template>
        <template v-else-if="step === 3">
          <v-alert
            type="info"
            variant="tonal"
            class="mb-4"
          >
            Choose the class receiving each campaign level. Subclass fields allow
            Compendium or GM-approved custom choices.
          </v-alert>
          <v-row
            v-for="row in classLevels"
            :key="row.level"
          >
            <v-col cols="2">Level {{ row.level }}</v-col>
            <v-col cols="5">
              <CompendiumEntryPicker
                v-if="!row.is_override"
                :model-value="row.class_entry_id"
                :items="definition?.class"
                label="Class"
                :loading="definitionLoading || draftLoading"
                :disabled="definitionLoading || draftLoading"
                @update:model-value="selectClass(row, $event)"
              />
              <v-text-field
                v-else
                v-model="row.class_name"
                label="Custom class (override)"
              />
              <v-checkbox
                v-model="row.is_override"
                color="warning"
                label="Custom override"
                density="compact"
              />
            </v-col>
            <v-col cols="5">
              <CompendiumChoicePicker
                v-if="row.is_override"
                :model-value="row.subclass_name"
                :items="[]"
                label="Subclass / class choice override"
                hint="Custom class metadata has no known unlock level"
                @update:model-value="selectSubclass(row, $event)"
              />
              <CompendiumChoicePicker
                v-else-if="row.class_entry_id && entryLoading(row.class_entry_id)"
                :model-value="row.subclass_name"
                :items="[]"
                label="Loading class choices"
                loading
                disabled
                @update:model-value="selectSubclass(row, $event)"
              />
              <CompendiumChoicePicker
                v-else-if="isSubclassUnlock(row)"
                :model-value="row.subclass_name"
                :items="classSubchoices(row)"
                :label="`Subclass · ${entry('class', row.class_entry_id)?.name} level ${classLevelAt(row)}`"
                hint="Choose a Compendium subclass or enter a custom override"
                :disabled="definitionLoading || draftLoading"
                @update:model-value="selectSubclass(row, $event)"
              />
              <div
                v-else-if="row.class_entry_id"
                class="text-body-2 text-medium-emphasis pt-4"
              >
                {{ subclassStatus(row) }}
              </div>
              <div
                v-else
                class="text-body-2 text-medium-emphasis pt-4"
              >
                Choose this level's class to load its level-gated choices.
              </div>
            </v-col>
          </v-row>
        </template>
        <template v-else-if="step === 4">
          <v-switch
            v-model="backgroundOverride"
            color="warning"
            label="Use a custom background override"
          />
          <CompendiumEntryPicker
            v-if="!backgroundOverride"
            v-model="form.background_entry_id"
            label="Background"
            :items="definition?.background"
            :loading="definitionLoading || draftLoading"
            :disabled="definitionLoading || draftLoading"
            @update:model-value="loadEntryData"
          />
          <v-text-field
            v-else
            v-model="form.background"
            label="Custom background (override)"
          />
          <v-textarea
            v-model="languageText"
            label="Languages"
            hint="One language or instruction per line. Keep entries such as “Choose 1” as written."
            persistent-hint
            rows="3"
          />
          <div class="text-overline mt-4">Skill proficiencies</div>
          <v-progress-linear
            v-if="definitionLoading"
            indeterminate
            class="mb-3"
          />
          <v-row>
            <v-col
              v-for="skill in definition?.skills"
              :key="skill"
              cols="6"
              sm="4"
            >
              <v-select
                v-model="form.skill_proficiencies[skill]"
                :label="displayIdentifier(skill)"
                :items="proficiencyOptions"
                :loading="draftLoading"
                :disabled="draftLoading"
              />
            </v-col>
          </v-row>
          <div class="text-overline mt-4">Equipment proficiencies</div>
          <CompendiumChoicePicker
            v-for="category in equipmentCategories"
            :key="category"
            v-model="form.equipment_proficiencies[category]"
            :items="ruleSuggestions(equipmentSuggestionKey(category))"
            :label="displayIdentifier(category)"
            multiple
            chips
            :loading="draftLoading || ruleChoicesLoading"
            :disabled="definitionLoading || draftLoading || ruleChoicesLoading"
          />
          <CompendiumChoicePicker
            v-model="startingEquipment"
            :items="ruleSuggestions('starting_equipment')"
            label="Starting equipment choices"
            hint="Select Compendium suggestions or enter a GM-approved custom item. Items are reviewed before posting."
            multiple
            chips
            :loading="draftLoading || ruleChoicesLoading"
            :disabled="definitionLoading || draftLoading || ruleChoicesLoading"
          />
        </template>
        <template v-else-if="step === 5">
          <v-number-input
            v-model.number="form.base_hp"
            control-variant="split"
            :min="1"
            label="Base HP (hit-die pool before ability modifiers)"
          />
          <v-select
            v-model="form.hp_ability"
            :items="abilities"
            label="HP ability"
            :loading="draftLoading"
            :disabled="draftLoading"
          />
          <v-number-input
            v-model.number="form.hp_adjustment"
            control-variant="split"
            label="HP-only adjustment"
          />
          <v-sheet
            class="pa-4"
            color="background"
            rounded
          >
            <strong>Maximum HP: {{ maxHp }}</strong>
            <div>
              {{ form.base_hp }} + ({{ hpModifier }} × {{ definition?.level ?? 1 }}) +
              {{ form.hp_adjustment }} = {{ maxHp }}
            </div>
          </v-sheet>
        </template>
        <template v-else>
          <v-list>
            <v-list-item
              title="Identity"
              :subtitle="`${form.name} · ${form.race || entry('race', form.race_entry_id)?.name || ''} · ${form.alignment}`"
            />
            <v-list-item
              title="Campaign level"
              :subtitle="String(definition?.level)"
            />
            <v-list-item
              title="Classes"
              :subtitle="
                classLevels
                  .map(
                    (row) => row.class_name || entry('class', row.class_entry_id)?.name,
                  )
                  .join(' / ')
              "
            />
            <v-list-item
              title="Maximum HP"
              :subtitle="`${maxHp} (${form.base_hp} + ${hpModifier} × ${definition?.level ?? 1} + ${form.hp_adjustment})`"
            />
          </v-list>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-btn
          :disabled="step === 1"
          @click="step -= 1"
        >
          Back
        </v-btn>
        <v-spacer />
        <v-btn
          v-if="step < 6"
          color="primary"
          :loading="busy"
          @click="next"
        >
          Save and continue
        </v-btn>
        <v-btn
          v-else
          color="primary"
          :loading="busy"
          @click="complete"
        >
          {{ isEditing ? "Save changes" : "Complete character" }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>
