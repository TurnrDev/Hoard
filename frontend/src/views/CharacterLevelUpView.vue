<template>
  <section
    class="mx-auto"
    style="max-width: 62rem"
    aria-labelledby="level-up-title"
  >
    <header class="mb-4">
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Guided level-up
        </p>
        <h1
          id="level-up-title"
          class="display-5 mb-2"
        >
          {{ definition?.character.name ?? "Level up" }}
        </h1>
        <p
          v-if="definition"
          class="mb-0 text-body-secondary"
        >
          Campaign level {{ definition.level }}.
        </p>
      </div>
    </header>

    <ProgressBar
      v-if="loading"
      indeterminate
      class="mb-4"
    />
    <Message
      v-if="error"
      severity="error"
      closable
      @click:close="error = ''"
    >
      {{ error }}
    </Message>
    <Message severity="info">
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
    </Message>

    <section
      v-if="definition"
      class="border rounded-3 p-3 p-md-4"
    >
      <div class="d-grid gap-4">
        <ProgressBar
          :model-value="(step / steps.length) * 100"
          class="mb-0"
        />
        <p class="mb-0 text-uppercase fw-semibold small text-body-secondary">
          Step {{ step }} of {{ steps.length }} · {{ steps[step - 1] }}
        </p>

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
            class="small text-body-secondary mt-2"
          >
            {{ chosenClass.source }} · {{ chosenClass.source_book }}
          </p>
        </section>

        <section v-else-if="hasClassChoices && step === 2">
          <Message
            v-if="rules?.gains.length"
            severity="success"
            class="mb-4"
          >
            <div
              v-for="gain in rules.gains"
              :key="gain.identifier"
              class="mb-2"
            >
              <strong>{{ gain.name }}</strong>
              <span v-if="gain.description">— {{ gain.description }}</span>
            </div>
          </Message>
          <Select
            v-if="rules?.class.subclass_required"
            v-model="subclassIdentifier"
            :options="rules.class.subclasses"
            option-label="name"
            option-value="identifier"
            @update:model-value="
              subclassName =
                rules?.class.subclasses.find(
                  (row) => row.identifier === subclassIdentifier,
                )?.name ?? ''
            "
          />
          <InputText
            v-if="rules?.class.subclass_required"
            v-model="subclassOverride"
            placeholder="Custom subclass override"
          />
          <template
            v-for="choice in rules?.choices"
            :key="choice.identifier"
          >
            <Select
              v-model="selectedChoices[choice.identifier]"
              :options="choice.options"
              option-label="name"
              option-value="identifier"
              :multiple="choice.amount > 1"
              show-clear
            />
            <InputText
              v-model="customChoices[choice.identifier]"
              :placeholder="`Custom ${choice.name.toLowerCase()} override`"
            />
          </template>
          <Message
            v-if="!rules?.class.subclass_required && !rules?.choices.length"
            severity="info"
          >
            No structured choices were found for this class level. Review your source
            material for any manual choices.
          </Message>
        </section>

        <section v-else-if="step === (hasClassChoices ? 3 : 2)">
          <p v-if="rules">
            {{ rules.class.name }} {{ rules.class.class_level }} uses a d{{
              rules.class.hit_die
            }}
            hit die.
          </p>
          <fieldset class="d-flex flex-wrap gap-3">
            <legend class="fs-6 fw-semibold">HP method</legend>
            <label class="d-flex align-items-center gap-2">
              <RadioButton
                v-model="hpMethod"
                value="roll"
              />
              Rolled
            </label>
            <label class="d-flex align-items-center gap-2">
              <RadioButton
                v-model="hpMethod"
                value="average"
              />
              Average
            </label>
          </fieldset>
          <InputNumber
            v-model="hpIncrease"
            :min="hpMethod === 'roll' ? 1 : rules?.class.average_hp"
            :max="hpMethod === 'roll' ? rules?.class.hit_die : rules?.class.average_hp"
            :placeholder="
              hpMethod === 'roll' ? 'What did you roll?' : 'Average HP increase'
            "
          />
        </section>

        <section v-else-if="hasAsi && step === (hasClassChoices ? 4 : 3)">
          <p class="mb-4">
            This class level grants an Ability Score Improvement. Choose either ability
            scores or a feat.
          </p>
          <fieldset class="d-flex flex-wrap gap-3">
            <legend class="fs-6 fw-semibold">ASI choice</legend>
            <label class="d-flex align-items-center gap-2">
              <RadioButton
                v-model="asiChoice"
                value="scores"
              />
              Increase ability scores
            </label>
            <label class="d-flex align-items-center gap-2">
              <RadioButton
                v-model="asiChoice"
                value="feat"
              />
              Take a feat
            </label>
          </fieldset>
          <Message
            v-if="asiChoice === 'scores'"
            severity="info"
            class="mb-4"
          >
            {{ asiPointsRemaining }} of 2 points remaining. Increase one score by +2 or
            two scores by +1.
          </Message>
          <div
            v-if="asiChoice === 'scores'"
            class="row g-3"
          >
            <div
              v-for="ability in abilities"
              :key="ability"
              class="col-12 col-md-6 col-lg-4"
            >
              <InputNumber
                v-model="abilityAdjustments[ability]"
                :min="0"
                :max="2"
                :placeholder="`${ability} adjustment`"
              />
            </div>
          </div>
          <template v-else-if="asiChoice === 'feat'">
            <AutoComplete
              v-model="featEntryId"
              :items="feats"
              item-value="id"
              :item-title="featTitle"
              label="Feat from Compendium"
              :loading="featsLoading"
              clearable
              @update:search="searchFeats"
            />
            <InputText
              v-model="featOverride"
              label="Custom feat override"
              hint="Use this when the feat is not in the enabled Compendium."
              persistent-hint
            />
          </template>
        </section>

        <section v-else>
          <Message
            v-if="previewLoading"
            severity="info"
          >
            Calculating changes…
          </Message>
          <template v-else-if="preview">
            <h2 class="h4 mb-3">Changes to apply</h2>
            <div class="table-responsive border rounded-3">
              <table class="table table-striped mb-0">
                <caption>Level-up changes to apply</caption>
                <thead>
                  <tr>
                    <th scope="col">Value</th>
                    <th
                      scope="col"
                      class="text-end"
                    >
                      Before
                    </th>
                    <th
                      scope="col"
                      class="text-end"
                    >
                      After
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">Maximum HP</th>
                    <td class="text-end tabular-nums">
                      {{ preview.before.max_hp.toLocaleString() }}
                    </td>
                    <td class="text-end tabular-nums">
                      {{ preview.after.max_hp.toLocaleString() }}
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Proficiency bonus</th>
                    <td class="text-end tabular-nums">
                      {{ preview.before.proficiency_bonus.toLocaleString() }}
                    </td>
                    <td class="text-end tabular-nums">
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
              </table>
            </div>
          </template>
        </section>
      </div>
      <footer class="d-flex flex-wrap justify-content-between gap-2 border-top pt-3">
        <Button
          v-if="step > 1"
          label="Back"
          severity="secondary"
          outlined
          @click="back"
        />
        <span v-else />
        <Button
          v-if="step < steps.length"
          severity="primary"
          :disabled="step === 1 && !classEntryId"
          label="Continue"
          @click="next"
        />
        <Button
          v-else
          severity="primary"
          :loading="completing"
          label="Complete level-up"
          @click="complete"
        />
      </footer>
    </section>
  </section>
</template>

<script lang="ts">
import AutoComplete from "primevue/autocomplete";
import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import RadioButton from "primevue/radiobutton";
import Select from "primevue/select";
import { defineComponent } from "vue";
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

export default defineComponent({
  components: {
    AutoComplete,
    Button,
    InputNumber,
    InputText,
    Message,
    ProgressBar,
    RadioButton,
    Select,
    CompendiumEntryPicker,
  },
  data() {
    return {
      abilities: [
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
      ],
      definition: undefined as LevelUpDefinition | undefined,
      preview: undefined as LevelUpPreview | undefined,
      rules: undefined as LevelUpRules | undefined,
      classEntryId: undefined as number | undefined,
      hpMethod: "roll" as "roll" | "average",
      hpIncrease: undefined as number | undefined,
      subclassIdentifier: "",
      subclassName: "",
      subclassOverride: "",
      abilityAdjustments: {} as Record<string, number>,
      asiChoice: undefined as "scores" | "feat" | undefined,
      featEntryId: undefined as number | undefined,
      featOverride: "",
      feats: [] as LevelUpFeat[],
      featsLoading: false,
      loadedFeatQuery: undefined as string | undefined,
      activeFeatQuery: undefined as string | undefined,
      featRequestVersion: 0,
      selectedChoices: {} as Record<string, string[]>,
      customChoices: {} as Record<string, string>,
      step: 1,
      loading: true,
      previewLoading: false,
      rulesLoading: false,
      completing: false,
      error: "",
    };
  },
  computed: {
    contextId(): number {
      return Number(this.$route.params.id);
    },
    characterId(): number {
      return Number(this.$route.params.characterId);
    },
    classes(): BuilderEntry[] {
      return (this.definition?.classes ?? []).map((entry) => ({
        ...entry,
        alias_ids: [],
        repository: "",
        repository_identifier: "default",
      }));
    },
    hasClassChoices(): boolean {
      return Boolean(this.rules?.class.subclass_required || this.rules?.choices.length);
    },
    hasAsi(): boolean {
      return Boolean(this.rules?.ability_score_improvement);
    },
    asiPointsRemaining(): number {
      return (
        2 -
        Object.values(this.abilityAdjustments).reduce(
          (total, value) => total + (Number(value) || 0),
          0,
        )
      );
    },
    steps(): string[] {
      return [
        "Class",
        ...(this.hasClassChoices ? ["Class choices"] : []),
        "Hit points",
        ...(this.hasAsi ? ["Ability score improvement"] : []),
        "Review",
      ];
    },
    chosenClass(): BuilderEntry | undefined {
      return this.classes.find((entry) => entry.id === this.classEntryId);
    },
  },
  watch: {
    classEntryId() {
      void this.loadClassRules();
    },
    hpMethod(method: "roll" | "average") {
      if (method === "average") {
        this.hpAverage();
      }
    },
    hasAsi(available: boolean) {
      if (available) {
        if (!this.feats.length && !this.featsLoading) {
          void this.searchFeats();
        }
        return;
      }
      this.asiChoice = undefined;
      this.abilityAdjustments = {};
      this.featEntryId = undefined;
      this.featOverride = "";
    },
    asiChoice(choice: "scores" | "feat" | undefined) {
      if (choice === "feat" && !this.feats.length && !this.featsLoading) {
        void this.searchFeats();
      }
      if (choice === "feat") {
        this.abilityAdjustments = {};
      }
      if (choice === "scores") {
        this.featEntryId = undefined;
        this.featOverride = "";
      }
    },
  },
  methods: {
    hpAverage(): void {
      if (this.rules) {
        this.hpIncrease = this.rules.class.average_hp;
      }
    },

    async refreshPreview(): Promise<void> {
      if (!this.classEntryId) {
        return;
      }
      this.previewLoading = true;
      try {
        this.preview = await previewLevelUp(this.contextId, this.characterId, {
          class_entry_id: this.classEntryId,
          hp_increase: this.hpIncrease ?? 0,
          ability_adjustments: this.abilityAdjustments,
        });
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to calculate level-up changes.";
      } finally {
        this.previewLoading = false;
      }
    },

    async loadClassRules(): Promise<void> {
      if (!this.classEntryId) {
        this.rules = undefined;
        return;
      }
      this.rulesLoading = true;
      this.preview = undefined;
      try {
        this.rules = await getLevelUpClass(
          this.contextId,
          this.characterId,
          this.classEntryId,
        );
        if (this.hpMethod === "average") {
          this.hpAverage();
        }
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load this class's level-up choices.";
      } finally {
        this.rulesLoading = false;
      }
    },

    async searchFeats(query = ""): Promise<void> {
      const normalizedQuery = query.trim();
      if (
        this.loadedFeatQuery === normalizedQuery ||
        (this.featsLoading && this.activeFeatQuery === normalizedQuery)
      ) {
        return;
      }
      const requestVersion = ++this.featRequestVersion;
      this.activeFeatQuery = normalizedQuery;
      this.featsLoading = true;
      try {
        const results = await getLevelUpFeats(
          this.contextId,
          this.characterId,
          normalizedQuery,
        );
        if (requestVersion === this.featRequestVersion) {
          this.feats = results;
          this.loadedFeatQuery = normalizedQuery;
        }
      } catch (exception) {
        if (requestVersion === this.featRequestVersion) {
          this.error =
            exception instanceof Error ? exception.message : "Unable to load feats.";
        }
      } finally {
        if (requestVersion === this.featRequestVersion) {
          this.activeFeatQuery = undefined;
          this.featsLoading = false;
        }
      }
    },

    featTitle(feat: LevelUpFeat): string {
      return `${feat.name} — ${feat.source}${feat.source_book ? ` · ${feat.source_book}` : ""}`;
    },

    async load(): Promise<void> {
      this.loading = true;
      try {
        this.definition = await getLevelUpDefinition(this.contextId, this.characterId);
        this.classEntryId = this.definition.preferred_class_ids[0];
      } catch (exception) {
        const detail =
          exception instanceof Error
            ? exception.message
            : "This character cannot level up right now.";
        await this.$router.replace({
          path: `/c/${this.contextId}/characters/${this.characterId}`,
          query: { level_up_error: detail },
        });
      } finally {
        this.loading = false;
      }
    },

    async next(): Promise<void> {
      this.error = "";
      const classChoicesStep = 2;
      const hpStep = this.hasClassChoices ? 3 : 2;
      if (this.hasClassChoices && this.step === classChoicesStep) {
        if (
          this.rules?.class.subclass_required &&
          !this.subclassIdentifier &&
          !this.subclassOverride.trim()
        ) {
          this.error = "Choose a subclass or provide a custom override.";
          return;
        }
        for (const choice of this.rules?.choices ?? []) {
          if (
            (this.selectedChoices[choice.identifier]?.length ?? 0) < choice.amount &&
            !this.customChoices[choice.identifier]?.trim()
          ) {
            this.error = `Choose ${choice.name} or provide a custom override.`;
            return;
          }
        }
      }
      if (
        this.step === hpStep &&
        (!this.hpIncrease ||
          this.hpIncrease < 1 ||
          this.hpIncrease > (this.rules?.class.hit_die ?? 0))
      ) {
        this.error = "Enter a valid HP increase for this class hit die.";
        return;
      }
      const asiStep = this.hasClassChoices ? 4 : 3;
      if (this.hasAsi && this.step === asiStep) {
        if (!this.asiChoice) {
          this.error = "Choose ability scores or a feat.";
          return;
        }
        if (this.asiChoice === "scores" && this.asiPointsRemaining !== 0) {
          this.error = "Distribute exactly two ability-score points.";
          return;
        }
        if (
          this.asiChoice === "feat" &&
          !this.featEntryId &&
          !this.featOverride.trim()
        ) {
          this.error = "Choose a feat or enter a custom feat override.";
          return;
        }
      }
      if (this.step + 1 === this.steps.length) {
        await this.refreshPreview();
      }
      if (!this.error && this.step < this.steps.length) {
        this.step += 1;
      }
    },

    back(): void {
      if (this.step > 1) {
        this.step -= 1;
      }
    },

    classChoicePayload() {
      const choices = (this.rules?.choices ?? []).map((choice) => ({
        identifier: choice.identifier,
        kind: "class_choice",
        values: this.selectedChoices[choice.identifier] ?? [],
        is_override: false,
      }));
      for (const [identifier, value] of Object.entries(this.customChoices)) {
        if (value.trim()) {
          choices.push({
            identifier: `custom:${identifier}`,
            kind: "custom",
            values: [value.trim()],
            is_override: true,
          });
        }
      }
      return choices;
    },

    async complete(): Promise<void> {
      if (!this.classEntryId || !this.hpIncrease) {
        this.error =
          "Choose a class and enter its HP increase before completing level-up.";
        return;
      }
      this.completing = true;
      try {
        await completeLevelUp(this.contextId, this.characterId, {
          class_entry_id: this.classEntryId,
          hp_method: this.hpMethod,
          hp_increase: this.hpIncrease,
          subclass_identifier: this.subclassIdentifier,
          subclass_name: this.subclassOverride.trim() || this.subclassName,
          class_override: Boolean(this.subclassOverride.trim()),
          ability_adjustments: this.abilityAdjustments,
          asi_choice: this.asiChoice ?? "",
          feat_entry_id: this.featEntryId,
          feat_override: this.featOverride,
          choices: this.classChoicePayload(),
        });
        await this.$router.replace(
          `/c/${this.contextId}/characters/${this.characterId}`,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to complete level-up.";
      } finally {
        this.completing = false;
      }
    },
    displayIdentifier,
  },
  mounted() {
    void this.load();
  },
});
</script>
