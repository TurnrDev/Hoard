<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  completeLevelUp,
  getLevelUpClass,
  getLevelUpDefinition,
  getLevelUpFeats,
  previewLevelUp,
  type BuilderEntry,
  type LevelUpDefinition,
  type LevelUpFeat,
  type LevelUpPreview,
  type LevelUpRules,
} from "../api";
import CompendiumEntryPicker from "../components/CompendiumEntryPicker.vue";
import { displayIdentifier } from "../display";

const route = useRoute();
const router = useRouter();
const contextId = Number(route.params.id);
const characterId = Number(route.params.characterId);
const abilities = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

const definition = ref<LevelUpDefinition>();
const preview = ref<LevelUpPreview>();
const rules = ref<LevelUpRules>();
const classEntryId = ref<number>();
const hpMethod = ref<"roll" | "average">("roll");
const hpIncrease = ref<number>();
const subclassIdentifier = ref("");
const subclassName = ref("");
const subclassOverride = ref("");
const abilityAdjustments = ref<Record<string, number>>({});
const asiChoice = ref<"scores" | "feat">();
const featEntryId = ref<number>();
const featOverride = ref("");
const feats = ref<LevelUpFeat[]>([]);
const featsLoading = ref(false);
const loadedFeatQuery = ref<string>();
let activeFeatQuery: string | undefined;
let featRequestVersion = 0;
const selectedChoices = ref<Record<string, string[]>>({});
const customChoices = ref<Record<string, string>>({});
const step = ref(1);
const loading = ref(true);
const previewLoading = ref(false);
const rulesLoading = ref(false);
const completing = ref(false);
const error = ref("");

const classes = computed<BuilderEntry[]>(() =>
  (definition.value?.classes ?? []).map((entry) => ({
    ...entry,
    alias_ids: [],
    repository: "",
    repository_identifier: "default",
  })),
);
const hasClassChoices = computed(() =>
  Boolean(rules.value?.class.subclass_required || rules.value?.choices.length),
);
const hasAsi = computed(() => Boolean(rules.value?.ability_score_improvement));
const asiPointsRemaining = computed(
  () =>
    2 -
    Object.values(abilityAdjustments.value).reduce(
      (total, value) => total + (Number(value) || 0),
      0,
    ),
);
const steps = computed(() => [
  "Class",
  ...(hasClassChoices.value ? ["Class choices"] : []),
  "Hit points",
  ...(hasAsi.value ? ["Ability score improvement"] : []),
  "Review",
]);
const chosenClass = computed(() =>
  classes.value.find((entry) => entry.id === classEntryId.value),
);

function hpAverage(): void {
  if (rules.value) hpIncrease.value = rules.value.class.average_hp;
}

async function refreshPreview(): Promise<void> {
  if (!classEntryId.value) return;
  previewLoading.value = true;
  try {
    preview.value = await previewLevelUp(contextId, characterId, {
      class_entry_id: classEntryId.value,
      hp_increase: hpIncrease.value ?? 0,
      ability_adjustments: abilityAdjustments.value,
    });
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to calculate level-up changes.";
  } finally {
    previewLoading.value = false;
  }
}

async function loadClassRules(): Promise<void> {
  if (!classEntryId.value) {
    rules.value = undefined;
    return;
  }
  rulesLoading.value = true;
  preview.value = undefined;
  try {
    rules.value = await getLevelUpClass(contextId, characterId, classEntryId.value);
    if (hpMethod.value === "average") hpAverage();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load this class's level-up choices.";
  } finally {
    rulesLoading.value = false;
  }
}

watch(classEntryId, loadClassRules);
watch(hpMethod, (method) => {
  if (method === "average") hpAverage();
});
watch(hasAsi, (available) => {
  if (available) {
    if (!feats.value.length && !featsLoading.value) void searchFeats();
  } else {
    asiChoice.value = undefined;
    abilityAdjustments.value = {};
    featEntryId.value = undefined;
    featOverride.value = "";
  }
});

async function searchFeats(query = ""): Promise<void> {
  const normalizedQuery = query.trim();
  if (
    loadedFeatQuery.value === normalizedQuery ||
    (featsLoading.value && activeFeatQuery === normalizedQuery)
  ) {
    return;
  }
  const requestVersion = ++featRequestVersion;
  activeFeatQuery = normalizedQuery;
  featsLoading.value = true;
  try {
    const results = await getLevelUpFeats(contextId, characterId, normalizedQuery);
    if (requestVersion === featRequestVersion) {
      feats.value = results;
      loadedFeatQuery.value = normalizedQuery;
    }
  } catch (exception) {
    if (requestVersion === featRequestVersion) {
      error.value =
        exception instanceof Error ? exception.message : "Unable to load feats.";
    }
  } finally {
    if (requestVersion === featRequestVersion) {
      activeFeatQuery = undefined;
      featsLoading.value = false;
    }
  }
}

function featTitle(feat: LevelUpFeat): string {
  return `${feat.name} — ${feat.source}${feat.source_book ? ` · ${feat.source_book}` : ""}`;
}

watch(asiChoice, (choice) => {
  if (choice === "feat" && !feats.value.length && !featsLoading.value)
    void searchFeats();
  if (choice === "feat") abilityAdjustments.value = {};
  if (choice === "scores") {
    featEntryId.value = undefined;
    featOverride.value = "";
  }
});

async function load(): Promise<void> {
  loading.value = true;
  try {
    definition.value = await getLevelUpDefinition(contextId, characterId);
    classEntryId.value = definition.value.preferred_class_ids[0];
  } catch (exception) {
    const detail =
      exception instanceof Error
        ? exception.message
        : "This character cannot level up right now.";
    await router.replace({
      path: `/c/${contextId}/characters/${characterId}`,
      query: { level_up_error: detail },
    });
  } finally {
    loading.value = false;
  }
}

async function next(): Promise<void> {
  error.value = "";
  const classChoicesStep = 2;
  const hpStep = hasClassChoices.value ? 3 : 2;
  if (hasClassChoices.value && step.value === classChoicesStep) {
    if (
      rules.value?.class.subclass_required &&
      !subclassIdentifier.value &&
      !subclassOverride.value.trim()
    ) {
      error.value = "Choose a subclass or provide a custom override.";
      return;
    }
    for (const choice of rules.value?.choices ?? []) {
      if (
        (selectedChoices.value[choice.identifier]?.length ?? 0) < choice.amount &&
        !customChoices.value[choice.identifier]?.trim()
      ) {
        error.value = `Choose ${choice.name} or provide a custom override.`;
        return;
      }
    }
  }
  if (
    step.value === hpStep &&
    (!hpIncrease.value ||
      hpIncrease.value < 1 ||
      hpIncrease.value > (rules.value?.class.hit_die ?? 0))
  ) {
    error.value = "Enter a valid HP increase for this class hit die.";
    return;
  }
  const asiStep = hasClassChoices.value ? 4 : 3;
  if (hasAsi.value && step.value === asiStep) {
    if (!asiChoice.value) {
      error.value = "Choose ability scores or a feat.";
      return;
    }
    if (asiChoice.value === "scores" && asiPointsRemaining.value !== 0) {
      error.value = "Distribute exactly two ability-score points.";
      return;
    }
    if (
      asiChoice.value === "feat" &&
      !featEntryId.value &&
      !featOverride.value.trim()
    ) {
      error.value = "Choose a feat or enter a custom feat override.";
      return;
    }
  }
  if (step.value + 1 === steps.value.length) await refreshPreview();
  if (!error.value && step.value < steps.value.length) step.value += 1;
}

function back(): void {
  if (step.value > 1) step.value -= 1;
}

function classChoicePayload() {
  const choices = (rules.value?.choices ?? []).map((choice) => ({
    identifier: choice.identifier,
    kind: "class_choice",
    values: selectedChoices.value[choice.identifier] ?? [],
    is_override: false,
  }));
  for (const [identifier, value] of Object.entries(customChoices.value)) {
    if (value.trim())
      choices.push({
        identifier: `custom:${identifier}`,
        kind: "custom",
        values: [value.trim()],
        is_override: true,
      });
  }
  return choices;
}

async function complete(): Promise<void> {
  if (!classEntryId.value || !hpIncrease.value) {
    error.value =
      "Choose a class and enter its HP increase before completing level-up.";
    return;
  }
  completing.value = true;
  try {
    await completeLevelUp(contextId, characterId, {
      class_entry_id: classEntryId.value,
      hp_method: hpMethod.value,
      hp_increase: hpIncrease.value,
      subclass_identifier: subclassIdentifier.value,
      subclass_name: subclassOverride.value.trim() || subclassName.value,
      class_override: Boolean(subclassOverride.value.trim()),
      ability_adjustments: abilityAdjustments.value,
      asi_choice: asiChoice.value ?? "",
      feat_entry_id: featEntryId.value,
      feat_override: featOverride.value,
      choices: classChoicePayload(),
    });
    await router.replace(`/c/${contextId}/characters/${characterId}`);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to complete level-up.";
  } finally {
    completing.value = false;
  }
}

onMounted(load);
</script>

<template>
  <v-container class="page-shell">
    <header class="page-heading mb-4">
      <div>
        <div class="text-overline text-secondary">Guided level-up</div>
        <h1>{{ definition?.character.name ?? "Level up" }}</h1>
        <p v-if="definition">Campaign level {{ definition.level }}.</p>
      </div>
    </header>

    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
      class="mb-4"
    />
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
    <v-alert
      type="info"
      variant="tonal"
      class="mb-4"
    >
      This is a helpful guide, not a definitive rules list. Consult official resources
      and useful references such as
      <a
        href="https://dreionsden.wordpress.com/"
        target="_blank"
        rel="noopener"
      >
        Dreion’s Den
      </a>
      before completing your level-up.
    </v-alert>

    <v-card
      v-if="definition"
      :loading="rulesLoading || previewLoading"
    >
      <v-card-text>
        <v-progress-linear
          :model-value="(step / steps.length) * 100"
          class="mb-6"
        />
        <div class="text-overline mb-2">
          Step {{ step }} of {{ steps.length }} · {{ steps[step - 1] }}
        </div>

        <section v-if="step === 1">
          <CompendiumEntryPicker
            v-model="classEntryId"
            :items="classes"
            :preferred-ids="definition.preferred_class_ids"
            label="Class receiving this level"
            :loading="loading"
          />
          <p
            v-if="chosenClass"
            class="text-caption mt-2"
          >
            {{ chosenClass.source }} · {{ chosenClass.source_book }}
          </p>
        </section>

        <section v-else-if="hasClassChoices && step === 2">
          <v-alert
            v-if="rules?.gains.length"
            type="success"
            variant="tonal"
            class="mb-4"
            title="Automatic gains"
          >
            <div
              v-for="gain in rules.gains"
              :key="gain.identifier"
              class="mb-2"
            >
              <strong>{{ gain.name }}</strong>
              <span v-if="gain.description">— {{ gain.description }}</span>
            </div>
          </v-alert>
          <v-select
            v-if="rules?.class.subclass_required"
            v-model="subclassIdentifier"
            :items="rules.class.subclasses"
            item-title="name"
            item-value="identifier"
            label="Subclass"
            @update:model-value="
              subclassName =
                rules?.class.subclasses.find(
                  (row) => row.identifier === subclassIdentifier,
                )?.name ?? ''
            "
          />
          <v-text-field
            v-if="rules?.class.subclass_required"
            v-model="subclassOverride"
            label="Custom subclass override"
            hint="Use this when your subclass is not listed."
            persistent-hint
          />
          <template
            v-for="choice in rules?.choices"
            :key="choice.identifier"
          >
            <v-select
              v-model="selectedChoices[choice.identifier]"
              :items="choice.options"
              item-title="name"
              item-value="identifier"
              :label="`${choice.name} — choose ${choice.amount}`"
              :multiple="choice.amount > 1"
              clearable
            />
            <v-text-field
              v-model="customChoices[choice.identifier]"
              :label="`Custom ${choice.name.toLowerCase()} override`"
              hint="Use this when your rule or homebrew choice is not listed."
              persistent-hint
            />
          </template>
          <v-alert
            v-if="!rules?.class.subclass_required && !rules?.choices.length"
            type="info"
            variant="tonal"
          >
            No structured choices were found for this class level. Review your source
            material for any manual choices.
          </v-alert>
        </section>

        <section v-else-if="step === (hasClassChoices ? 3 : 2)">
          <p v-if="rules">
            {{ rules.class.name }} {{ rules.class.class_level }} uses a d{{
              rules.class.hit_die
            }}
            hit die.
          </p>
          <v-radio-group
            v-model="hpMethod"
            inline
            label="HP method"
          >
            <v-radio
              label="Rolled"
              value="roll"
            />
            <v-radio
              label="Average"
              value="average"
            />
          </v-radio-group>
          <v-number-input
            v-model="hpIncrease"
            control-variant="split"
            :min="hpMethod === 'roll' ? 1 : rules?.class.average_hp"
            :max="hpMethod === 'roll' ? rules?.class.hit_die : rules?.class.average_hp"
            :label="hpMethod === 'roll' ? 'What did you roll?' : 'Average HP increase'"
          />
        </section>

        <section v-else-if="hasAsi && step === (hasClassChoices ? 4 : 3)">
          <p class="mb-4">
            This class level grants an Ability Score Improvement. Choose either ability
            scores or a feat.
          </p>
          <v-radio-group
            v-model="asiChoice"
            inline
            label="ASI choice"
          >
            <v-radio
              label="Increase ability scores"
              value="scores"
            />
            <v-radio
              label="Take a feat"
              value="feat"
            />
          </v-radio-group>
          <v-alert
            v-if="asiChoice === 'scores'"
            type="info"
            variant="tonal"
            class="mb-4"
          >
            {{ asiPointsRemaining }} of 2 points remaining. Increase one score by +2 or
            two scores by +1.
          </v-alert>
          <v-row v-if="asiChoice === 'scores'">
            <v-col
              v-for="ability in abilities"
              :key="ability"
              cols="12"
              sm="6"
              md="4"
            >
              <v-number-input
                v-model="abilityAdjustments[ability]"
                control-variant="split"
                :min="0"
                :max="2"
                :label="`${ability} adjustment`"
              />
            </v-col>
          </v-row>
          <template v-else-if="asiChoice === 'feat'">
            <v-autocomplete
              v-model="featEntryId"
              :items="feats"
              item-value="id"
              :item-title="featTitle"
              label="Feat from Compendium"
              :loading="featsLoading"
              clearable
              @update:search="searchFeats"
            />
            <v-text-field
              v-model="featOverride"
              label="Custom feat override"
              hint="Use this when the feat is not in the enabled Compendium."
              persistent-hint
            />
          </template>
        </section>

        <section v-else>
          <v-alert
            v-if="previewLoading"
            type="info"
            variant="tonal"
          >
            Calculating changes…
          </v-alert>
          <template v-else-if="preview">
            <h2 class="text-h6 mb-3">Changes to apply</h2>
            <v-table
              density="compact"
              class="a11y-table"
            >
              <caption class="visually-hidden">Level-up changes to apply</caption>
              <thead>
                <tr>
                  <th scope="col">Value</th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    Before
                  </th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    After
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Maximum HP</th>
                  <td class="a11y-number">
                    {{ preview.before.max_hp.toLocaleString() }}
                  </td>
                  <td class="a11y-number">
                    {{ preview.after.max_hp.toLocaleString() }}
                  </td>
                </tr>
                <tr>
                  <th scope="row">Proficiency bonus</th>
                  <td class="a11y-number">
                    {{ preview.before.proficiency_bonus.toLocaleString() }}
                  </td>
                  <td class="a11y-number">
                    {{ preview.after.proficiency_bonus.toLocaleString() }}
                  </td>
                </tr>
                <tr
                  v-for="ability in abilities"
                  :key="ability"
                >
                  <th scope="row">{{ displayIdentifier(ability) }}</th>
                  <td class="a11y-number">
                    {{ preview.before.abilities[ability]?.score }}
                  </td>
                  <td class="a11y-number">
                    {{ preview.after.abilities[ability]?.score }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </template>
        </section>
      </v-card-text>
      <v-card-actions class="px-4 pb-4">
        <v-btn
          v-if="step > 1"
          @click="back"
        >
          Back
        </v-btn>
        <v-spacer />
        <v-btn
          v-if="step < steps.length"
          color="primary"
          :disabled="step === 1 && !classEntryId"
          @click="next"
        >
          Continue
        </v-btn>
        <v-btn
          v-else
          color="primary"
          :loading="completing"
          @click="complete"
        >
          Complete level-up
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>
