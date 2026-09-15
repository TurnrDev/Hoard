<template>
  <section
    class="border rounded-3 p-3 p-md-4"
    aria-labelledby="encounter-heading"
  >
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-4"
    >
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Encounter
        </p>
        <h2
          id="encounter-heading"
          class="h4 mb-1"
        >
          {{ campaign.encounter ? "Combat in progress" : "Initiative tracker" }}
        </h2>
        <p class="text-body-secondary mb-0">
          <template v-if="campaign.encounter">
            {{ campaign.encounter.combatants.length }} initiative
            {{ campaign.encounter.combatants.length === 1 ? "entry" : "entries" }}
          </template>
          <template v-else>
            Starting combat adds every active player character at initiative 0.
          </template>
        </p>
      </div>
      <div
        v-if="campaign.encounter"
        class="d-flex flex-wrap justify-content-end gap-2"
      >
        <template v-if="campaign.encounter.current_combatant_id === null">
          <Button
            icon="mdi mdi-play"
            label="Begin"
            :loading="busy"
            :disabled="orderedCombatants.length === 0"
            @click="beginTurns"
          />
        </template>
        <template v-else>
          <Button
            icon="mdi mdi-skip-previous"
            label="Previous turn"
            severity="secondary"
            outlined
            :disabled="busy || orderedCombatants.length === 0"
            @click="moveCurrentTurn(-1)"
          />
          <Button
            icon="mdi mdi-skip-next"
            label="Next turn"
            :disabled="busy || orderedCombatants.length === 0"
            @click="moveCurrentTurn(1)"
          />
        </template>
        <Button
          label="End combat"
          icon="mdi mdi-flag-checkered"
          severity="danger"
          outlined
          @click="endDialogOpen = true"
        />
      </div>
      <Button
        v-else
        label="Start combat"
        icon="mdi mdi-sword-cross"
        :loading="busy"
        @click="startCombat"
      />
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

    <template v-if="campaign.encounter">
      <div class="table-responsive mb-4">
        <table class="table table-striped align-middle mb-0">
          <caption>
            Current initiative entries. A character can appear more than once.
          </caption>
          <thead>
            <tr>
              <th scope="col">Combatant</th>
              <th scope="col">Initiative</th>
              <th scope="col">HP</th>
              <th scope="col">Status</th>
              <th
                scope="col"
                class="text-end"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="combatant in orderedCombatants"
              :key="combatant.id"
              :class="{
                'table-active border-start border-4 border-warning':
                  campaign.encounter.current_combatant_id === combatant.id,
              }"
              :aria-current="
                campaign.encounter.current_combatant_id === combatant.id
                  ? 'step'
                  : undefined
              "
              @dragover.prevent
              @drop="finishReorder($event, combatant.id)"
            >
              <th scope="row">
                <span class="d-inline-flex align-items-center gap-2">
                  <span
                    class="initiative-drag-handle mdi mdi-drag-vertical text-body-secondary"
                    draggable="true"
                    :aria-label="`Drag ${combatant.name} to reorder initiative`"
                    role="img"
                    @dragstart="startReorder($event, combatant.id)"
                    @dragend="draggedCombatantId = null"
                  />
                  <span
                    v-if="campaign.encounter.current_combatant_id === combatant.id"
                    class="mdi mdi-sword-cross text-warning"
                    aria-hidden="true"
                  />
                  <span
                    v-if="campaign.encounter.current_combatant_id === combatant.id"
                    class="visually-hidden"
                  >
                    Current turn:
                  </span>
                  {{ combatant.name }}
                </span>
              </th>
              <td>
                <Button
                  :label="String(combatant.initiative)"
                  severity="secondary"
                  text
                  rounded
                  class="tabular-nums"
                  :aria-label="`Set ${combatant.name} initiative, currently ${combatant.initiative}`"
                  @click="openInitiativeDialog(combatant)"
                />
              </td>
              <td>
                <template v-if="hasTrackedHealth(combatant)">
                  <span class="d-block small tabular-nums mb-1">
                    {{ combatant.current_hp }} / {{ combatant.max_hp }} HP
                  </span>
                  <ProgressBar
                    :value="combatant.health_percentage ?? 0"
                    :show-value="false"
                    :aria-label="`${combatant.name} health: ${combatant.current_hp} of ${combatant.max_hp}`"
                  />
                </template>
                <span
                  v-else
                  class="small text-body-secondary"
                >
                  Not tracked
                </span>
              </td>
              <td>
                <ConditionIndicators
                  v-if="combatant.conditions.length"
                  :combatant-name="combatant.name"
                  :conditions="combatant.conditions"
                  expanded
                />
                <span
                  v-else
                  class="small text-body-secondary"
                >
                  No active effects
                </span>
              </td>
              <td>
                <div class="d-flex justify-content-end gap-2">
                  <Button
                    icon="mdi mdi-sword-cross"
                    size="small"
                    :severity="
                      campaign.encounter.current_combatant_id === combatant.id
                        ? 'warn'
                        : 'secondary'
                    "
                    :outlined="campaign.encounter.current_combatant_id !== combatant.id"
                    rounded
                    :disabled="busy"
                    :aria-label="`Make ${combatant.name} the current turn`"
                    :title="`Make ${combatant.name} the current turn`"
                    @click="setCurrentTurn(combatant.id)"
                  />
                  <Button
                    icon="mdi mdi-heart-minus-outline"
                    size="small"
                    severity="danger"
                    text
                    rounded
                    :disabled="!hasTrackedHealth(combatant) || busy"
                    :aria-label="`Deal damage to ${combatant.name}`"
                    :title="`Deal damage to ${combatant.name}`"
                    @click="openHealthDialog(combatant, 'damage')"
                  />
                  <Button
                    icon="mdi mdi-heart-plus-outline"
                    size="small"
                    severity="success"
                    text
                    rounded
                    :disabled="!hasTrackedHealth(combatant) || busy"
                    :aria-label="`Heal ${combatant.name}`"
                    :title="`Heal ${combatant.name}`"
                    @click="openHealthDialog(combatant, 'healing')"
                  />
                  <ConditionManager
                    :conditions="combatant.conditions"
                    :target-name="combatant.name"
                    :target-id="`gm-combatant-${combatant.id}`"
                    can-edit
                    trigger-only
                    icon-only
                    @apply="applyCondition(combatant.id, $event)"
                    @remove="removeCondition(combatant.id, $event)"
                  />
                  <Button
                    icon="mdi mdi-arrow-up"
                    size="small"
                    severity="secondary"
                    text
                    rounded
                    :disabled="orderedCombatants[0]?.id === combatant.id || busy"
                    :aria-label="`Move ${combatant.name} earlier in initiative`"
                    @click="moveCombatant(combatant.id, -1)"
                  />
                  <Button
                    icon="mdi mdi-arrow-down"
                    size="small"
                    severity="secondary"
                    text
                    rounded
                    :disabled="
                      orderedCombatants[orderedCombatants.length - 1]?.id ===
                        combatant.id || busy
                    "
                    :aria-label="`Move ${combatant.name} later in initiative`"
                    @click="moveCombatant(combatant.id, 1)"
                  />
                  <Button
                    icon="mdi mdi-close"
                    severity="danger"
                    text
                    rounded
                    :aria-label="`Remove ${combatant.name} from initiative`"
                    @click="removeCombatant(combatant)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <form
        class="encounter-participant-form border-top pt-4"
        @submit.prevent="addParticipant"
      >
        <fieldset>
          <legend class="h5">Add an initiative entry</legend>
          <p class="small text-body-secondary">
            Add another turn for a character, or enter a custom combatant name.
          </p>

          <div class="d-grid gap-3">
            <div>
              <label
                class="form-label fw-semibold"
                for="encounter-character"
              >
                Existing character
              </label>
              <Select
                id="encounter-character"
                v-model="characterId"
                class="w-100"
                :options="characterOptions"
                option-label="label"
                option-value="value"
                show-clear
                filter
                placeholder="Choose a character"
              />
              <div class="form-text">
                Leave this blank to add a custom combatant below.
              </div>
            </div>

            <template v-if="characterId === null">
              <div>
                <label
                  class="form-label fw-semibold"
                  for="combatant-name"
                >
                  Name or label
                </label>
                <InputText
                  id="combatant-name"
                  v-model="combatantName"
                  class="w-100"
                  maxlength="200"
                  placeholder="For example: Goblin 2 or The Black Knight"
                />
              </div>
            </template>

            <div class="row g-3 mx-0">
              <div
                class="col-12"
                :class="characterId === null ? 'col-md-6' : 'col-md-4'"
              >
                <label
                  class="form-label fw-semibold"
                  for="participant-initiative"
                >
                  Initiative
                </label>
                <InputNumber
                  v-model="newInitiative"
                  input-id="participant-initiative"
                  class="w-100"
                  input-class="w-100 tabular-nums"
                  show-buttons
                  button-layout="horizontal"
                  decrement-button-icon="mdi mdi-minus"
                  increment-button-icon="mdi mdi-plus"
                  :min="-100"
                  :max="100"
                />
              </div>
              <div
                v-if="characterId === null"
                class="col-12 col-md-6"
              >
                <label
                  class="form-label fw-semibold"
                  for="combatant-max-hp"
                >
                  Maximum HP
                </label>
                <InputNumber
                  v-model="maximumHp"
                  input-id="combatant-max-hp"
                  class="w-100"
                  input-class="w-100 tabular-nums"
                  show-buttons
                  button-layout="horizontal"
                  decrement-button-icon="mdi mdi-minus"
                  increment-button-icon="mdi mdi-plus"
                  :min="1"
                />
              </div>
            </div>
          </div>

          <div class="d-flex justify-content-end mt-3">
            <Button
              type="submit"
              label="Add to initiative"
              icon="mdi mdi-plus"
              :loading="busy"
              :disabled="participantInvalid"
            />
          </div>
        </fieldset>
      </form>
    </template>

    <Dialog
      v-model:visible="healthDialogOpen"
      modal
      :header="healthDialogTitle"
      :style="{ width: 'min(28rem, calc(100vw - 2rem))' }"
    >
      <form
        id="quick-health-form"
        class="d-grid gap-3"
        @submit.prevent="applyHealthChange"
      >
        <div>
          <label
            class="form-label fw-semibold"
            for="quick-health-amount"
          >
            Hit points
          </label>
          <InputNumber
            v-model="healthAmount"
            input-id="quick-health-amount"
            class="w-100"
            input-class="w-100 tabular-nums"
            show-buttons
            button-layout="horizontal"
            decrement-button-icon="mdi mdi-minus"
            increment-button-icon="mdi mdi-plus"
            :min="1"
          />
        </div>
        <div>
          <label
            class="form-label fw-semibold"
            for="quick-health-note"
          >
            Note (optional)
          </label>
          <InputText
            id="quick-health-note"
            v-model="healthNote"
            class="w-100"
            maxlength="200"
            placeholder="For example: goblin arrow"
          />
        </div>
      </form>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          text
          @click="healthDialogOpen = false"
        />
        <Button
          form="quick-health-form"
          type="submit"
          :label="healthMode === 'damage' ? 'Deal damage' : 'Apply healing'"
          :severity="healthMode === 'damage' ? 'danger' : 'success'"
          :loading="busy"
          :disabled="healthAmount < 1"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="initiativeDialogOpen"
      modal
      header="Set initiative"
      :style="{ width: 'min(24rem, calc(100vw - 2rem))' }"
    >
      <div class="d-grid gap-2">
        <label
          class="form-label fw-semibold"
          for="initiative-dialog-value"
        >
          {{ initiativeCombatant?.name }} initiative
        </label>
        <InputNumber
          v-model="initiativeDialogValue"
          input-id="initiative-dialog-value"
          class="w-100"
          input-class="w-100 tabular-nums"
          show-buttons
          button-layout="horizontal"
          decrement-button-icon="mdi mdi-minus"
          increment-button-icon="mdi mdi-plus"
          :min="-100"
          :max="100"
        />
      </div>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          text
          @click="initiativeDialogOpen = false"
        />
        <Button
          label="Set initiative"
          :loading="busy"
          @click="setInitiative"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="endDialogOpen"
      modal
      header="End combat?"
      :style="{ width: 'min(32rem, calc(100vw - 2rem))' }"
    >
      <p>
        The initiative order will close. Conditions on campaign characters will remain
        active after combat.
      </p>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          text
          @click="endDialogOpen = false"
        />
        <Button
          label="End combat"
          severity="danger"
          :loading="busy"
          @click="endCombat"
        />
      </template>
    </Dialog>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import Select from "primevue/select";
import { defineComponent, type PropType } from "vue";
import {
  addCharacterToEncounter,
  addEncounterCombatant,
  endEncounter,
  postHealth,
  removeCombatantCondition,
  removeEncounterCombatant,
  reorderEncounterCombatants,
  setCombatantCondition,
  setCurrentEncounterCombatant,
  startEncounter,
  updateEncounterCombatant,
  type Campaign,
  type Character,
  type ConditionMutation,
  type EncounterCombatant,
} from "../api";
import ConditionIndicators from "./ConditionIndicators.vue";
import ConditionManager from "./ConditionManager.vue";

export default defineComponent({
  components: {
    Button,
    ConditionIndicators,
    ConditionManager,
    Dialog,
    InputNumber,
    InputText,
    Message,
    ProgressBar,
    Select,
  },
  props: {
    campaign: { type: Object as PropType<Campaign>, required: true },
    characters: { type: Array as PropType<Character[]>, required: true },
    contextId: { type: Number, required: true },
  },
  emits: ["completed"],
  data() {
    return {
      busy: false,
      error: "",
      endDialogOpen: false,
      initiativeDialogOpen: false,
      initiativeCombatant: null as EncounterCombatant | null,
      initiativeDialogValue: 0,
      healthDialogOpen: false,
      healthCombatant: null as EncounterCombatant | null,
      healthMode: "damage" as "damage" | "healing",
      healthAmount: 1,
      healthNote: "",
      draggedCombatantId: null as number | null,
      characterId: null as number | null,
      combatantName: "",
      newInitiative: 0,
      maximumHp: null as number | null,
    };
  },
  computed: {
    orderedCombatants(): EncounterCombatant[] {
      return [...(this.campaign.encounter?.combatants ?? [])].sort(
        (left, right) => left.initiative_position - right.initiative_position,
      );
    },
    characterOptions(): Array<{ label: string; value: number }> {
      return this.characters
        .filter((character) => character.is_active && !character.is_archived)
        .map((character) => ({ label: character.name, value: character.id }))
        .sort((left, right) => left.label.localeCompare(right.label));
    },
    participantInvalid(): boolean {
      if (this.characterId !== null) {
        return false;
      }

      return !this.combatantName.trim();
    },
    healthDialogTitle(): string {
      const action = this.healthMode === "damage" ? "Deal damage to" : "Heal";

      return `${action} ${this.healthCombatant?.name ?? "combatant"}`;
    },
  },
  methods: {
    reportError(exception: unknown, fallback: string): void {
      this.error = exception instanceof Error ? exception.message : fallback;
    },
    resetParticipant(): void {
      this.characterId = null;
      this.combatantName = "";
      this.newInitiative = 0;
      this.maximumHp = null;
    },
    async startCombat(): Promise<void> {
      this.busy = true;
      this.error = "";

      try {
        await startEncounter(this.contextId);
        this.$emit("completed", "Combat started. Set initiative for each participant.");
      } catch (exception) {
        this.reportError(exception, "Unable to start combat.");
      } finally {
        this.busy = false;
      }
    },
    async endCombat(): Promise<void> {
      this.busy = true;
      this.error = "";

      try {
        await endEncounter(this.contextId);
        this.endDialogOpen = false;
        this.$emit("completed", "Combat ended. Persistent conditions remain active.");
      } catch (exception) {
        this.reportError(exception, "Unable to end combat.");
      } finally {
        this.busy = false;
      }
    },
    openInitiativeDialog(combatant: EncounterCombatant): void {
      this.initiativeCombatant = combatant;
      this.initiativeDialogValue = combatant.initiative;
      this.initiativeDialogOpen = true;
    },
    async setInitiative(): Promise<void> {
      if (!this.initiativeCombatant) {
        return;
      }

      this.busy = true;
      this.error = "";

      try {
        await updateEncounterCombatant(this.contextId, this.initiativeCombatant.id, {
          initiative: this.initiativeDialogValue,
        });
        this.initiativeDialogOpen = false;
        this.$emit(
          "completed",
          `${this.initiativeCombatant.name}'s initiative is ${this.initiativeDialogValue}.`,
        );
      } catch (exception) {
        this.reportError(exception, "Unable to update initiative.");
      } finally {
        this.busy = false;
      }
    },
    async setCurrentTurn(combatantId: number): Promise<void> {
      this.busy = true;
      this.error = "";

      try {
        await setCurrentEncounterCombatant(this.contextId, combatantId);
      } catch (exception) {
        this.reportError(exception, "Unable to set the current turn.");
      } finally {
        this.busy = false;
      }
    },
    async beginTurns(): Promise<void> {
      const firstCombatant = this.orderedCombatants[0];

      if (!firstCombatant) {
        return;
      }

      await this.setCurrentTurn(firstCombatant.id);
    },
    async moveCurrentTurn(offset: -1 | 1): Promise<void> {
      if (!this.campaign.encounter || this.orderedCombatants.length === 0) {
        return;
      }

      const currentId = this.campaign.encounter.current_combatant_id;
      const currentIndex = this.orderedCombatants.findIndex(
        (combatant) => combatant.id === currentId,
      );
      const nextIndex =
        currentIndex === -1
          ? offset === 1
            ? 0
            : this.orderedCombatants.length - 1
          : (currentIndex + offset + this.orderedCombatants.length) %
            this.orderedCombatants.length;

      await this.setCurrentTurn(this.orderedCombatants[nextIndex].id);
    },
    hasTrackedHealth(combatant: EncounterCombatant): boolean {
      return combatant.current_hp !== null && combatant.max_hp !== null;
    },
    openHealthDialog(combatant: EncounterCombatant, mode: "damage" | "healing"): void {
      this.healthCombatant = combatant;
      this.healthMode = mode;
      this.healthAmount = 1;
      this.healthNote = "";
      this.healthDialogOpen = true;
    },
    async applyHealthChange(): Promise<void> {
      const combatant = this.healthCombatant;
      if (!combatant || combatant.current_hp === null || this.healthAmount < 1) {
        return;
      }

      this.busy = true;
      this.error = "";

      try {
        if (combatant.character_id !== null) {
          const direction = this.healthMode === "damage" ? -1 : 1;
          await postHealth(this.contextId, {
            character_id: combatant.character_id,
            reason: this.healthMode,
            current_hp_delta: direction * this.healthAmount,
            description: this.healthNote.trim() || `Combat: ${combatant.name}`,
          });
        } else {
          const maximumHp = combatant.max_hp ?? combatant.current_hp;
          const nextHp =
            this.healthMode === "damage"
              ? Math.max(0, combatant.current_hp - this.healthAmount)
              : Math.min(maximumHp, combatant.current_hp + this.healthAmount);

          await updateEncounterCombatant(this.contextId, combatant.id, {
            current_hp: nextHp,
          });
        }

        this.healthDialogOpen = false;
        this.$emit(
          "completed",
          `${combatant.name} ${this.healthMode === "damage" ? "took damage" : "was healed"}.`,
        );
      } catch (exception) {
        this.reportError(exception, "Unable to change the combatant's health.");
      } finally {
        this.busy = false;
      }
    },
    async applyCondition(
      combatantId: number,
      condition: ConditionMutation,
    ): Promise<void> {
      this.error = "";

      try {
        await setCombatantCondition(this.contextId, combatantId, condition);
      } catch (exception) {
        this.reportError(exception, "Unable to apply the condition.");
      }
    },
    async removeCondition(combatantId: number, conditionId: number): Promise<void> {
      this.error = "";

      try {
        await removeCombatantCondition(this.contextId, combatantId, conditionId);
      } catch (exception) {
        this.reportError(exception, "Unable to remove the condition.");
      }
    },
    startReorder(event: DragEvent, combatantId: number): void {
      this.draggedCombatantId = combatantId;

      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(combatantId));
      }
    },
    async finishReorder(event: DragEvent, targetId: number): Promise<void> {
      const sourceId = this.draggedCombatantId;
      this.draggedCombatantId = null;

      if (sourceId === null || sourceId === targetId) {
        return;
      }

      const orderedIds = this.orderedCombatants.map((combatant) => combatant.id);
      const sourceIndex = orderedIds.indexOf(sourceId);
      const targetIndex = orderedIds.indexOf(targetId);

      if (sourceIndex === -1 || targetIndex === -1) {
        return;
      }

      orderedIds.splice(sourceIndex, 1);
      const targetRow = event.currentTarget as HTMLTableRowElement;
      const insertAfter =
        event.clientY >
        targetRow.getBoundingClientRect().top + targetRow.offsetHeight / 2;
      const insertionIndex =
        targetIndex + (insertAfter ? 1 : 0) - (sourceIndex < targetIndex ? 1 : 0);
      orderedIds.splice(insertionIndex, 0, sourceId);

      await this.saveCombatantOrder(orderedIds);
    },
    async moveCombatant(combatantId: number, offset: -1 | 1): Promise<void> {
      const orderedIds = this.orderedCombatants.map((combatant) => combatant.id);
      const currentIndex = orderedIds.indexOf(combatantId);
      const nextIndex = currentIndex + offset;

      if (currentIndex === -1 || nextIndex < 0 || nextIndex >= orderedIds.length) {
        return;
      }

      [orderedIds[currentIndex], orderedIds[nextIndex]] = [
        orderedIds[nextIndex],
        orderedIds[currentIndex],
      ];

      await this.saveCombatantOrder(orderedIds);
    },
    async saveCombatantOrder(combatantIds: number[]): Promise<void> {
      this.busy = true;
      this.error = "";

      try {
        await reorderEncounterCombatants(this.contextId, combatantIds);
        this.$emit("completed", "Initiative order updated.");
      } catch (exception) {
        this.reportError(exception, "Unable to reorder initiative.");
      } finally {
        this.busy = false;
      }
    },
    async removeCombatant(combatant: EncounterCombatant): Promise<void> {
      this.busy = true;
      this.error = "";

      try {
        await removeEncounterCombatant(this.contextId, combatant.id);
        this.$emit("completed", `${combatant.name} removed from initiative.`);
      } catch (exception) {
        this.reportError(exception, "Unable to remove the combatant.");
      } finally {
        this.busy = false;
      }
    },
    async addParticipant(): Promise<void> {
      if (this.participantInvalid) {
        return;
      }

      this.busy = true;
      this.error = "";

      try {
        if (this.characterId !== null) {
          await addCharacterToEncounter(
            this.contextId,
            this.characterId,
            this.newInitiative,
          );
        } else {
          await addEncounterCombatant(this.contextId, {
            name: this.combatantName.trim(),
            initiative: this.newInitiative,
            ...(this.maximumHp === null
              ? {}
              : { current_hp: this.maximumHp, max_hp: this.maximumHp }),
          });
        }

        this.resetParticipant();
        this.$emit("completed", "Initiative entry added.");
      } catch (exception) {
        this.reportError(exception, "Unable to add the initiative entry.");
      } finally {
        this.busy = false;
      }
    },
  },
});
</script>

<style scoped>
.encounter-participant-form,
.encounter-participant-form fieldset,
.encounter-participant-form :deep(.p-select),
.encounter-participant-form :deep(.p-inputnumber),
.encounter-participant-form :deep(.p-inputtext),
.encounter-participant-form :deep(.p-inputnumber-input) {
  min-width: 0;
  max-width: 100%;
}

.initiative-drag-handle {
  cursor: grab;
}

.encounter-participant-form :deep(.p-inputnumber-input) {
  flex: 1 1 auto;
  width: 1%;
}
</style>
