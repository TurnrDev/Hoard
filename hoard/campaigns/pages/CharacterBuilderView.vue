<template>
  <section
    class="mx-auto"
    style="max-width: 62rem"
    aria-labelledby="builder-title"
  >
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-4"
    >
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Character builder
        </p>
        <h1
          id="builder-title"
          class="display-5 mb-0"
        >
          {{
            isEditing
              ? `Edit ${form.name || "character"}`
              : form.name || "New character"
          }}
        </h1>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <CharacterImportMenu
          :context-id="contextId"
          :character-id="characterId"
          :items="items"
          :items-loading="itemsLoading"
          @completed="load"
          @error="showImportError"
        />
        <Button
          v-if="isEditing"
          :as="'router-link'"
          :to="`/c/${contextId}/characters/${characterId}`"
          label="Cancel"
          severity="secondary"
          outlined
        />
      </div>
    </header>
    <Message
      v-if="error"
      severity="error"
      closable
      class="mb-4"
      @close="error = ''"
    >
      {{ error }}
    </Message>
    <ProgressBar
      :value="(step / 6) * 100"
      :show-value="false"
      :aria-label="`Character builder progress: step ${step} of 6`"
      class="mb-5"
    />
    <section class="border rounded-3 p-3 p-md-4">
      <header class="mb-4">
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Step {{ step }} of 6
        </p>
        <h2 class="h3 mb-0">{{ stepTitles[step - 1] }}</h2>
      </header>
      <div class="row g-3">
        <template v-if="step === 1">
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Character rules</span>
            <Select
              :model-value="form.native_system_id"
              :options="definition?.systems ?? []"
              option-label="name"
              option-value="id"
              :loading="definitionLoading || draftLoading"
              :disabled="systemSelectionLocked"
              fluid
              @update:model-value="selectSystem"
            />
            <small class="text-body-secondary">
              5e and 5e 2024 equipment, spells, feats, ancestries, and backgrounds can
              be mixed. Classes and subclasses stay in the rules version chosen when the
              character starts.
            </small>
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Name</span>
            <InputText
              v-model="form.name"
              fluid
            />
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Alignment</span>
            <Select
              v-model="form.alignment"
              :loading="draftLoading"
              :disabled="draftLoading"
              :options="[
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
              fluid
            />
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">About (optional)</span>
            <Textarea
              v-model="form.about"
              rows="3"
              fluid
            />
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Personality traits (optional)</span>
            <Textarea
              v-model="form.personality_traits"
              rows="3"
              fluid
            />
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Ideals (optional)</span>
            <Textarea
              v-model="form.ideals"
              rows="3"
              fluid
            />
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Bonds (optional)</span>
            <Textarea
              v-model="form.bonds"
              rows="3"
              fluid
            />
          </label>
          <label class="col-12 d-grid gap-2">
            <span class="fw-semibold">Flaws (optional)</span>
            <Textarea
              v-model="form.flaws"
              rows="3"
              fluid
            />
          </label>
        </template>
        <template v-else-if="step === 2">
          <div class="col-12">
            <div class="d-flex align-items-center gap-2">
              <ToggleSwitch
                v-model="raceOverride"
                input-id="race-override"
              />
              <label
                for="race-override"
                class="fw-semibold"
              >
                Use a custom ancestry
              </label>
            </div>
            <small class="d-block text-body-secondary mt-1">
              Enable this when the character's ancestry is not available in the
              Compendium.
            </small>
          </div>
          <div class="col-12">
            <CompendiumEntryPicker
              v-if="!raceOverride"
              :model-value="form.race_entry_id"
              label="Race"
              :items="definition?.race"
              :loading="definitionLoading || draftLoading"
              :disabled="definitionLoading || draftLoading"
              @update:model-value="selectRace"
            />
            <label
              v-else
              class="d-grid gap-2"
            >
              <span class="fw-semibold">Custom race</span>
              <InputText
                v-model="form.race"
                fluid
              />
            </label>
          </div>
          <div
            v-if="!raceOverride && raceSubchoices().length > 0"
            class="col-12"
          >
            <CompendiumChoicePicker
              v-model="form.subrace_name"
              :items="raceSubchoices()"
              label="Subrace"
              hint="Choose a subrace provided by the selected race."
              :allow-custom="false"
              :loading="draftLoading || entryLoading(form.race_entry_id)"
              :disabled="
                definitionLoading || draftLoading || entryLoading(form.race_entry_id)
              "
            />
          </div>
          <div class="col-12 mt-3">
            <h3 class="h5 mb-1">Ability scores</h3>
            <p class="text-body-secondary mb-0">
              Enter the rolled or standard score, then apply any ancestry bonus or
              manual adjustment. The calculated score is shown for each ability.
            </p>
          </div>
          <div class="col-12">
            <div class="row g-3">
              <div
                v-for="ability in abilities"
                :key="ability"
                class="col-12 col-md-6 col-xl-4"
              >
                <fieldset class="border rounded-3 p-3 h-100 d-grid gap-3">
                  <legend class="float-none w-auto h5 mb-0">
                    {{ displayIdentifier(ability) }}
                  </legend>
                  <label class="d-grid gap-2">
                    <span class="fw-semibold">Raw score</span>
                    <InputNumber
                      v-model.number="form[ability]"
                      show-buttons
                      button-layout="horizontal"
                      :min="1"
                      :max="30"
                      fluid
                    />
                  </label>
                  <label class="d-grid gap-2">
                    <span class="fw-semibold">Ancestry bonus</span>
                    <InputNumber
                      v-model.number="form.ability_bonuses[ability]"
                      show-buttons
                      button-layout="horizontal"
                      :min="-10"
                      :max="10"
                      fluid
                    />
                  </label>
                  <label class="d-grid gap-2">
                    <span class="fw-semibold">Manual adjustment</span>
                    <InputNumber
                      v-model.number="form.ability_score_adjustments[ability]"
                      show-buttons
                      button-layout="horizontal"
                      :min="-30"
                      :max="30"
                      fluid
                    />
                  </label>
                  <div class="border-top pt-2 tabular-nums">
                    <span class="text-body-secondary">Calculated score</span>
                    <strong class="float-end fs-5">
                      {{ finalAbility(ability) }}
                    </strong>
                    <small class="d-block text-body-secondary mt-1">
                      {{ form[ability] }} + {{ form.ability_bonuses[ability] ?? 0 }} +
                      {{ form.ability_score_adjustments[ability] ?? 0 }}
                    </small>
                  </div>
                </fieldset>
              </div>
            </div>
          </div>
        </template>
        <template v-else-if="step === 3">
          <Message severity="info" class="mb-4">
            Choose the class receiving each campaign level. Classes are native
            Compendium resources; their levels and subclass selections are stored in
            the RPG Companion character state.
          </Message>
          <div
            class="col-12 row g-3"
            v-for="row in classLevels"
            :key="row.level"
          >
            <div class="col-12 col-lg-2 fw-semibold">Level {{ row.level }}</div>
            <div class="col-12 col-lg-5">
              <CompendiumEntryPicker
                :model-value="row.class_entry_id"
                :items="definition?.class"
                label="Class"
                :loading="definitionLoading || draftLoading"
                :disabled="definitionLoading || draftLoading"
                @update:model-value="selectClass(row, $event)"
              />
            </div>
            <div class="col-12 col-lg-5">
              <CompendiumChoicePicker
                v-if="row.class_entry_id && entryLoading(row.class_entry_id)"
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
                class="small text-body-secondary pt-2"
              >
                {{ subclassStatus(row) }}
              </div>
              <div
                v-else
                class="small text-body-secondary pt-2"
              >
                Choose this level's class to load its level-gated choices.
              </div>
            </div>
          </div>
        </template>
        <template v-else-if="step === 4">
          <div class="col-12">
            <div class="d-flex align-items-center gap-2">
              <ToggleSwitch
                v-model="backgroundOverride"
                input-id="background-override"
              />
              <label
                for="background-override"
                class="fw-semibold"
              >
                Use a custom background
              </label>
            </div>
          </div>
          <div class="col-12">
            <CompendiumEntryPicker
              v-if="!backgroundOverride"
              v-model="form.background_entry_id"
              label="Background"
              :items="definition?.background"
              :loading="definitionLoading || draftLoading"
              :disabled="definitionLoading || draftLoading"
              @update:model-value="loadEntryData"
            />
            <label
              v-else
              class="d-grid gap-2"
            >
              <span class="fw-semibold">Custom background</span>
              <InputText
                v-model="form.background"
                fluid
              />
            </label>
          </div>
          <fieldset class="col-12 border-0 p-0 m-0">
            <legend class="h6 mb-2">Languages</legend>
            <div
              v-for="(language, index) in form.languages"
              :key="index"
              class="input-group mb-2"
            >
              <InputText
                v-model="form.languages[index]"
                :aria-label="`Language ${index + 1}`"
              />
              <Button
                icon="mdi mdi-delete-outline"
                severity="danger"
                outlined
                :aria-label="`Remove language ${language || index + 1}`"
                @click="removeLanguage(index)"
              />
            </div>
            <Button
              icon="mdi mdi-plus"
              label="Add language"
              size="small"
              outlined
              @click="addLanguage"
            />
          </fieldset>
          <div class="col-12 text-uppercase fw-semibold small text-body-secondary mt-3">
            Skill proficiencies
          </div>
          <ProgressBar
            v-if="definitionLoading"
            indeterminate
            class="mb-3"
          />
          <div class="col-12 row g-3">
            <SkillProficiencyPicker
              v-for="skill in definition?.skills"
              :key="skill"
              v-model="form.skill_proficiencies[skill]"
              class="col-12 col-md-6 col-lg-4 d-grid gap-2"
              :input-id="`builder-skill-${skill}`"
              :label="displayIdentifier(skill)"
              :loading="draftLoading"
              :disabled="draftLoading"
            />
          </div>
          <div class="col-12 text-uppercase fw-semibold small text-body-secondary mt-3">
            Equipment proficiencies
          </div>
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
          <label class="col-12 col-md-6 d-grid gap-2 align-content-start">
            <span class="fw-semibold">Base HP</span>
            <InputNumber
              v-model.number="form.base_hp"
              show-buttons
              button-layout="horizontal"
              :min="1"
              fluid
            />
            <small class="text-body-secondary">
              Hit-die pool before ability modifiers
            </small>
          </label>
          <label class="col-12 col-md-6 d-grid gap-2 align-content-start">
            <span class="fw-semibold">HP-only adjustment</span>
            <InputNumber
              v-model.number="form.hp_adjustment"
              show-buttons
              button-layout="horizontal"
              fluid
            />
          </label>
          <section class="col-12 border rounded-3 p-3">
            <strong>Maximum HP: {{ maxHp }}</strong>
            <div>
              {{ form.base_hp }} + ({{ hpModifier }} × {{ definition?.level ?? 1 }}) +
              {{ form.hp_adjustment }} = {{ maxHp }}
            </div>
          </section>
        </template>
        <template v-else>
          <ul class="col-12 list-group">
            <li class="list-group-item">
              <strong>Identity</strong>
              <span class="d-block text-body-secondary">
                {{
                  `${form.name} · ${form.race || entry("race", form.race_entry_id)?.name || ""} · ${form.alignment}`
                }}
              </span>
            </li>
            <li class="list-group-item">
              <strong>Campaign level</strong>
              <span class="d-block text-body-secondary">{{ definition?.level }}</span>
            </li>
            <li class="list-group-item">
              <strong>Classes</strong>
              <span class="d-block text-body-secondary">
                {{
                  classLevels
                    .map(
                      (row) =>
                        row.class_name || entry("class", row.class_entry_id)?.name,
                    )
                    .join(" / ")
                }}
              </span>
            </li>
            <li class="list-group-item">
              <strong>Maximum HP</strong>
              <span class="d-block text-body-secondary tabular-nums">
                {{
                  `${maxHp} (${form.base_hp} + ${hpModifier} × ${definition?.level ?? 1} + ${form.hp_adjustment})`
                }}
              </span>
            </li>
          </ul>
        </template>
      </div>
      <footer
        class="d-flex flex-wrap justify-content-between gap-2 border-top mt-4 pt-3"
      >
        <Button
          :disabled="step === 1"
          label="Back"
          severity="secondary"
          outlined
          @click="step -= 1"
        />
        <Button
          v-if="step < 6"
          label="Save and continue"
          :loading="busy"
          @click="next"
        />
        <Button
          v-else
          :label="isEditing ? 'Save changes' : 'Complete character'"
          :loading="busy"
          @click="complete"
        />
      </footer>
    </section>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { defineComponent } from "vue";
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
} from "@/api";
import {
  classLevelAt as allocationClassLevelAt,
  sameClass,
} from "@/campaigns/builderProgression";
import CharacterImportMenu from "@/campaigns/components/CharacterImportMenu.vue";
import CompendiumChoicePicker, {
  type CompendiumChoice,
} from "@/campaigns/components/CompendiumChoicePicker.vue";
import CompendiumEntryPicker from "@/campaigns/components/CompendiumEntryPicker.vue";
import SkillProficiencyPicker from "@/campaigns/components/SkillProficiencyPicker.vue";
import { displayIdentifier } from "@/campaigns/display";

type ClassLevel = {
  level: number;
  class_entry_id?: number;
  class_name: string;
  subclass_identifier: string;
  subclass_name: string;
  is_override: boolean;
};

type Ability =
  "strength" | "dexterity" | "constitution" | "intelligence" | "wisdom" | "charisma";
export default defineComponent({
  components: {
    Button,
    Checkbox,
    InputNumber,
    InputText,
    Message,
    ProgressBar,
    Select,
    Textarea,
    ToggleSwitch,
    CharacterImportMenu,
    CompendiumChoicePicker,
    CompendiumEntryPicker,
    SkillProficiencyPicker,
  },
  data() {
    const abilities = [
      "strength",
      "dexterity",
      "constitution",
      "intelligence",
      "wisdom",
      "charisma",
    ] as const;
    const equipmentCategories = ["armor", "weapons", "tools"] as const;

    return {
      abilities,
      equipmentCategories,
      stepTitles: [
        "Identity",
        "Ancestry and ability scores",
        "Classes and levels",
        "Background and proficiencies",
        "Hit points",
        "Review",
      ],
      step: 1,
      definition: undefined as BuilderDefinition | undefined,
      character: undefined as Character | undefined,
      items: [] as Item[],
      classLevels: [] as ClassLevel[],
      startingEquipment: [] as string[],
      raceOverride: false,
      backgroundOverride: false,
      error: "",
      busy: false,
      definitionLoading: true,
      draftLoading: true,
      itemsLoading: true,
      loadingEntryIds: new Set<number>(),
      entryRequests: new Map<number, Promise<void>>(),
      form: {
        native_system_id: "5e" as "5e" | "5e2024",
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
        hp_adjustment: 0,
      },
    };
  },
  computed: {
    contextId(): number {
      return Number(this.$route.params.id);
    },
    characterId(): number {
      return Number(this.$route.params.characterId);
    },
    isEditing(): boolean {
      return this.$route.query.mode === "edit";
    },
    resumeKey(): string {
      return `hoard:builder:${this.characterId}:${this.isEditing ? "edit" : "build"}:step`;
    },
    hpModifier(): number {
      const ability = (this.character?.sheet.hp_ability ??
        "constitution") as (typeof this.abilities)[number];
      const score =
        this.form[ability] +
        (this.form.ability_bonuses[ability] ?? 0) +
        (this.form.ability_score_adjustments[ability] ?? 0);
      return Math.floor((score - 10) / 2);
    },
    maxHp(): number {
      return Math.max(
        1,
        this.form.base_hp +
          this.hpModifier * (this.definition?.level ?? 1) +
          this.form.hp_adjustment,
      );
    },
    ruleChoicesLoading(): boolean {
      return [
        this.form.race_entry_id,
        this.form.background_entry_id,
        ...this.classLevels.map((row) => row.class_entry_id),
      ].some((id) => this.entryLoading(id));
    },
    systemSelectionLocked(): boolean {
      return (
        this.definitionLoading ||
        this.draftLoading ||
        this.classLevels.some((row) => typeof row.class_entry_id === "number")
      );
    },
  },
  watch: {
    step(value: number) {
      this.saveCurrentStep(value);
    },
    raceOverride(value: boolean) {
      if (value) {
        this.form.subrace_name = "";
        this.form.subrace_identifier = "";
      }
    },
  },
  methods: {
    canonicalEntryId(
      kind: "race" | "class" | "background",
      id: number | null | undefined,
    ): number | undefined {
      if (typeof id !== "number") {
        return undefined;
      }
      const canonical = this.definition?.[kind].find(
        (candidate) => candidate.id === id || (candidate.alias_ids ?? []).includes(id),
      );
      return canonical?.id ?? id;
    },

    finalAbility(ability: Ability): number {
      return (
        this.form[ability] +
        (this.form.ability_bonuses[ability] ?? 0) +
        (this.form.ability_score_adjustments[ability] ?? 0)
      );
    },

    saveCurrentStep(value: number): void {
      localStorage.setItem(this.resumeKey, String(value));
    },

    showImportError(message: string): void {
      this.error = message;
    },

    addLanguage(): void {
      this.form.languages.push("");
    },

    removeLanguage(index: number): void {
      this.form.languages.splice(index, 1);
    },

    async loadDefinition(systemId?: "5e" | "5e2024"): Promise<BuilderDefinition> {
      try {
        const selectedSystemId = systemId ?? this.form.native_system_id;
        const nextDefinition = await getBuilderDefinition(
          this.contextId,
          selectedSystemId,
        );
        this.definition = nextDefinition;

        return nextDefinition;
      } finally {
        this.definitionLoading = false;
      }
    },

    async loadItems(): Promise<Item[]> {
      try {
        const nextItems = await getItems(this.contextId);
        this.items = nextItems;

        return nextItems;
      } finally {
        this.itemsLoading = false;
      }
    },

    async load(): Promise<void> {
      try {
        const [nextDefinition, draft, nextItems] = await Promise.all([
          this.loadDefinition(),
          getCharacterBuilder(this.contextId, this.characterId),
          this.loadItems(),
        ]);
        this.items = nextItems;
        const value = draft.character as Character;
        const activeDefinition =
          nextDefinition.system_id === value.native_system_id
            ? nextDefinition
            : await this.loadDefinition(value.native_system_id);
        this.character = value;
        Object.assign(this.form, {
          native_system_id: value.native_system_id,
          name: value.name,
          race: value.race,
          race_entry_id: this.canonicalEntryId("race", value.race_entry_id),
          subrace_name: value.subrace,
          background: value.background,
          background_entry_id: this.canonicalEntryId(
            "background",
            value.background_entry_id,
          ),
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
          strength: value.sheet.abilities.strength.raw,
          dexterity: value.sheet.abilities.dexterity.raw,
          constitution: value.sheet.abilities.constitution.raw,
          intelligence: value.sheet.abilities.intelligence.raw,
          wisdom: value.sheet.abilities.wisdom.raw,
          charisma: value.sheet.abilities.charisma.raw,
        });
        const nativeClasses =
          (draft.classes as Array<{
            class_entry_id?: number;
            class_level: number;
            subclass_identifier: string;
          }>) ?? [];
        this.classLevels = [];
        for (const selected of nativeClasses) {
          for (let index = 0; index < selected.class_level; index += 1) {
            this.classLevels.push({
              level: this.classLevels.length + 1,
              class_entry_id: selected.class_entry_id,
              class_name: "",
              subclass_identifier:
                index === selected.class_level - 1
                  ? selected.subclass_identifier
                  : "",
              subclass_name: "",
              is_override: false,
            });
          }
        }
        for (const row of this.classLevels) {
          row.class_entry_id = this.canonicalEntryId("class", row.class_entry_id);
        }
        for (let level = 1; level <= activeDefinition.level; level += 1) {
          if (!this.classLevels.some((row) => row.level === level)) {
            this.classLevels.push({
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
            this.form.race_entry_id,
            this.form.background_entry_id,
            ...this.classLevels.map((row) => row.class_entry_id),
          ]
            .filter((id): id is number => typeof id === "number")
            .map((id) => this.loadEntryData(id)),
        );
        this.reconcileSubclassChoices();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to load builder.";
      } finally {
        this.draftLoading = false;
      }
    },

    findEntry(id: number): BuilderEntry | undefined {
      return [
        ...(this.definition?.race ?? []),
        ...(this.definition?.class ?? []),
        ...(this.definition?.background ?? []),
      ].find((row) => row.id === id);
    },

    async loadEntryData(id?: number | null): Promise<void> {
      if (!id) {
        return;
      }
      const candidate = this.findEntry(id);
      if (!candidate || candidate.data) {
        return;
      }
      const existing = this.entryRequests.get(id);
      if (existing) {
        return existing;
      }
      this.loadingEntryIds.add(id);
      const request = this.loadEntryDetails(id, candidate);
      this.entryRequests.set(id, request);

      return request;
    },

    async selectRace(raceEntryId: number | undefined): Promise<void> {
      this.form.race_entry_id = raceEntryId;
      this.form.subrace_name = "";
      this.form.subrace_identifier = "";
      await this.loadEntryData(raceEntryId);
    },

    async selectSystem(value: "5e" | "5e2024"): Promise<void> {
      if (value === this.form.native_system_id || this.systemSelectionLocked) {
        return;
      }

      this.form.native_system_id = value;
      this.definitionLoading = true;

      try {
        await this.loadDefinition(value);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to change character rules.";
      }
    },

    async loadEntryDetails(id: number, candidate: BuilderEntry): Promise<void> {
      try {
        const details = await getBuilderEntry(
          this.contextId,
          id,
          this.form.native_system_id,
        );
        Object.assign(candidate, details);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load Compendium choices.";
      } finally {
        this.entryRequests.delete(id);
        this.loadingEntryIds.delete(id);
      }
    },

    entryLoading(id?: number | null): boolean {
      return typeof id === "number" && this.loadingEntryIds.has(id);
    },

    entry(
      kind: "race" | "class" | "background",
      id?: number,
    ): BuilderEntry | undefined {
      return (this.definition?.[kind] as BuilderEntry[] | undefined)?.find(
        (row) => row.id === id,
      );
    },

    entryChoices(
      kind: "race" | "class" | "background",
      id: number | undefined,
      key: string,
    ): CompendiumChoice[] {
      const selected = this.entry(kind, id);
      const values = selected?.data?.[key];
      if (!selected || !Array.isArray(values)) {
        return [];
      }
      return values
        .map((value): CompendiumChoice | undefined => {
          if (typeof value === "string") {
            return value ? { name: value, source: selected.source } : undefined;
          }
          if (!value || typeof value !== "object") {
            return undefined;
          }
          const choice = value as Record<string, unknown>;
          const name = String(choice.name ?? "").trim();
          if (!name) {
            return undefined;
          }
          return {
            identifier: String(choice.identifier ?? ""),
            name,
            source: String(choice.source ?? selected.source),
            level:
              typeof choice.level === "number"
                ? choice.level
                : Number(choice.level) || 1,
          };
        })
        .filter((value): value is CompendiumChoice => Boolean(value));
    },

    classSubchoices(row: ClassLevel): CompendiumChoice[] {
      const subclasses = this.entryChoices("class", row.class_entry_id, "subclasses");
      return subclasses.length
        ? subclasses
        : this.entryChoices("class", row.class_entry_id, "subchoices");
    },

    classLevelAt(row: ClassLevel): number {
      return allocationClassLevelAt(this.classLevels, row);
    },

    subclassUnlockLevel(row: ClassLevel): number | undefined {
      const value = this.entry("class", row.class_entry_id)?.data
        ?.subclass_selection_level;
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
    },

    isSubclassUnlock(row: ClassLevel): boolean {
      const unlockLevel = this.subclassUnlockLevel(row);
      return (
        this.classSubchoices(row).length > 0 &&
        unlockLevel !== undefined &&
        this.classLevelAt(row) === unlockLevel
      );
    },

    chosenSubclass(row: ClassLevel): ClassLevel | undefined {
      return this.classLevels.find(
        (candidate) => sameClass(candidate, row) && Boolean(candidate.subclass_name),
      );
    },

    subclassStatus(row: ClassLevel): string {
      const classEntry = this.entry("class", row.class_entry_id);
      const unlockLevel = this.subclassUnlockLevel(row);
      if (
        !classEntry ||
        !this.classSubchoices(row).length ||
        unlockLevel === undefined
      ) {
        return "No Compendium subclass choice at this class level.";
      }
      const currentClassLevel = this.classLevelAt(row);
      if (currentClassLevel < unlockLevel) {
        return `Subclass unlocks at ${classEntry.name} level ${unlockLevel}.`;
      }
      const selected = this.chosenSubclass(row);
      return selected
        ? `${selected.subclass_name} was selected at ${classEntry.name} level ${unlockLevel}.`
        : `Subclass choice is incomplete at ${classEntry.name} level ${unlockLevel}.`;
    },

    reconcileSubclassChoices(): void {
      for (const row of this.classLevels) {
        if (!row.class_entry_id) {
          continue;
        }
        const unlockLevel = this.subclassUnlockLevel(row);
        if (!unlockLevel) {
          continue;
        }
        const matching = this.classLevels.filter((candidate) =>
          sameClass(candidate, row),
        );
        const target = matching[unlockLevel - 1];
        const previous = matching.find((candidate) => candidate.subclass_name);
        if (!target || !previous || target === previous || target.subclass_name) {
          continue;
        }
        target.subclass_identifier = previous.subclass_identifier;
        target.subclass_name = previous.subclass_name;
        previous.subclass_identifier = "";
        previous.subclass_name = "";
      }
    },

    async selectClass(
      row: ClassLevel,
      classEntryId: number | undefined,
    ): Promise<void> {
      if (row.class_entry_id !== classEntryId) {
        row.subclass_identifier = "";
        row.subclass_name = "";
      }
      row.class_entry_id = classEntryId;
      row.class_name = this.entry("class", classEntryId)?.name ?? "";
      await this.loadEntryData(classEntryId);
      this.reconcileSubclassChoices();
    },

    selectSubclass(row: ClassLevel, value: string | string[]): void {
      const name = Array.isArray(value) ? String(value[0] ?? "") : value;
      const selected = this.classSubchoices(row).find((choice) => choice.name === name);
      row.subclass_name = name;
      row.subclass_identifier = selected?.identifier ?? "";
    },

    raceSubchoices(): CompendiumChoice[] {
      return this.entryChoices("race", this.form.race_entry_id, "subchoices");
    },

    selectedRuleEntries(): BuilderEntry[] {
      return [
        this.entry("race", this.form.race_entry_id),
        this.entry("background", this.form.background_entry_id),
        ...this.classLevels.map((row) => this.entry("class", row.class_entry_id)),
      ].filter((value): value is BuilderEntry => Boolean(value));
    },

    ruleSuggestions(key: string): CompendiumChoice[] {
      const choices = this.selectedRuleEntries().flatMap((selected) => {
        const values = selected.data?.[key];
        if (!Array.isArray(values)) {
          return [];
        }
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
    },

    equipmentSuggestionKey(category: "armor" | "weapons" | "tools"): string {
      return `${category === "armor" ? "armor" : category.slice(0, -1)}_proficiencies`;
    },

    async save(): Promise<void> {
      this.busy = true;
      try {
        if (this.raceOverride) {
          this.form.race_entry_id = undefined;
        } else {
          this.form.race =
            this.entry("race", this.form.race_entry_id)?.name ?? this.form.race;
        }
        if (this.backgroundOverride) {
          this.form.background_entry_id = undefined;
        } else {
          this.form.background =
            this.entry("background", this.form.background_entry_id)?.name ??
            this.form.background;
        }
        const selectedClasses = new Map<
          number,
          {
            class_entry_id: number;
            class_level: number;
            subclass_identifier: string;
          }
        >();

        for (const row of this.classLevels) {
          if (!row.class_entry_id) {
            continue;
          }

          const selected = selectedClasses.get(row.class_entry_id) ?? {
            class_entry_id: row.class_entry_id,
            class_level: 0,
            subclass_identifier: "",
          };
          selected.class_level += 1;
          selected.subclass_identifier ||= row.subclass_identifier;
          selectedClasses.set(row.class_entry_id, selected);
        }
        await saveCharacterBuilder(this.contextId, this.characterId, {
          fields: {
            ...this.form,
            languages: this.form.languages
              .map((language) => language.trim())
              .filter(Boolean),
          },
          classes: [...selectedClasses.values()],
          is_override:
            this.raceOverride ||
            this.backgroundOverride,
        });
      } finally {
        this.busy = false;
      }
    },

    async next(): Promise<void> {
      try {
        await this.save();
        this.step = Math.min(6, this.step + 1);
        localStorage.setItem(this.resumeKey, String(this.step));
      } catch (exception) {
        this.error = exception instanceof Error ? exception.message : "Unable to save.";
      }
    },

    async complete(): Promise<void> {
      try {
        await this.save();
        if (this.isEditing) {
          localStorage.removeItem(this.resumeKey);
          await this.$router.replace(
            `/c/${this.contextId}/characters/${this.characterId}`,
          );
          return;
        }
        await completeCharacterBuilder(this.contextId, this.characterId);
        localStorage.removeItem(this.resumeKey);
        await this.$router.replace(
          `/c/${this.contextId}/characters/${this.characterId}`,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to complete character.";
      }
    },
    displayIdentifier,
  },
  mounted() {
    this.step = Math.min(
      6,
      Math.max(1, Number(localStorage.getItem(this.resumeKey)) || 1),
    );
    void this.load();
  },
});
</script>
