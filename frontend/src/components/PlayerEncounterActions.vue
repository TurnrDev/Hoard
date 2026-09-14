<template>
  <section
    v-if="tieCombatant || currentCombatant || upNextCombatant"
    class="alert border rounded p-3 mb-4"
    :class="[
      currentCombatant ? 'alert-warning sticky-top' : 'alert-info',
      { 'shadow-sm': currentCombatant },
    ]"
    aria-labelledby="player-encounter-actions-heading"
    role="status"
  >
    <div class="d-flex flex-column flex-md-row align-items-md-center gap-3">
      <div class="flex-grow-1">
        <h2
          id="player-encounter-actions-heading"
          class="h5 mb-1"
        >
          {{ encounterHeading }}
        </h2>

        <fieldset
          v-if="tieCombatant"
          class="border-0 p-0 m-0"
        >
          <legend class="fs-6 fw-semibold mb-1">Who should act first?</legend>
          <p class="text-body-secondary small mb-2">
            Your final initiative and Dexterity modifier are tied. Everyone involved
            must choose the same combatant; otherwise the system picks.
          </p>
          <Message
            class="mb-3"
            :severity="tieCombatant.tie_resolution === null ? 'info' : 'success'"
            :closable="false"
          >
            <span
              class="mdi me-2"
              :class="
                tieCombatant.tie_resolution === null
                  ? 'mdi-account-clock-outline'
                  : 'mdi-check-circle-outline'
              "
              aria-hidden="true"
            />
            {{ tieOutcome }}
          </Message>
          <div class="d-flex flex-wrap gap-2">
            <Button
              v-for="option in tieCombatant.tie_options"
              :key="option.combatant_id"
              size="small"
              :outlined="tieCombatant.tie_choice_id !== option.combatant_id"
              :disabled="busy || tieCombatant.tie_resolution !== null"
              :aria-label="`${option.name}: ${voteLabel(option.vote_count)}`"
              @click="chooseTie(option.combatant_id)"
            >
              <span>{{ option.name }}</span>
              <Badge
                :value="option.vote_count"
                severity="secondary"
              />
            </Button>
          </div>
        </fieldset>

        <p
          v-else-if="currentCombatant"
          class="text-body-secondary mb-0"
        >
          Finish your actions, then pass initiative to the next combatant.
        </p>
        <p
          v-else
          class="text-body-secondary mb-0"
        >
          Get ready to act when the current combatant finishes their turn.
        </p>
      </div>

      <Button
        v-if="currentCombatant"
        label="End my turn"
        icon="mdi mdi-skip-next"
        :loading="busy"
        @click="finishTurn"
      />
    </div>

    <Message
      v-if="error"
      class="mt-3 mb-0"
      severity="error"
      :closable="false"
    >
      {{ error }}
    </Message>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Badge from "primevue/badge";
import Message from "primevue/message";
import { defineComponent, type PropType } from "vue";
import { chooseInitiativeTie, endPlayerTurn, type EncounterCombatant } from "../api";

export default defineComponent({
  components: {
    Badge,
    Button,
    Message,
  },
  props: {
    contextId: { type: Number, required: true },
    characterId: { type: Number, required: true },
    currentCombatantId: {
      type: Number as PropType<number | null>,
      default: null,
    },
    combatants: {
      type: Array as PropType<EncounterCombatant[]>,
      required: true,
    },
  },
  data() {
    return {
      busy: false,
      error: "",
    };
  },
  watch: {
    resolvedTieResultKey(resultKey: string | undefined): void {
      if (!resultKey) {
        return;
      }

      this.announceTieResolution();
    },
  },
  computed: {
    ownedCombatants(): EncounterCombatant[] {
      return this.combatants.filter(
        (combatant) => combatant.character_id === this.characterId,
      );
    },
    orderedCombatants(): EncounterCombatant[] {
      return [...this.combatants].sort(
        (left, right) => left.initiative_position - right.initiative_position,
      );
    },
    tieCombatant(): EncounterCombatant | undefined {
      return this.ownedCombatants.find(
        (combatant) =>
          combatant.tie_options.length > 1 && combatant.tie_resolution === null,
      );
    },
    resolvedTieCombatant(): EncounterCombatant | undefined {
      return this.ownedCombatants.find(
        (combatant) =>
          combatant.tie_options.length > 1 && combatant.tie_resolution !== null,
      );
    },
    resolvedTieResultKey(): string | undefined {
      if (!this.resolvedTieCombatant) {
        return undefined;
      }

      return [
        this.resolvedTieCombatant.id,
        this.resolvedTieCombatant.tie_resolution,
        this.resolvedTieCombatant.tie_winner_id,
      ].join(":");
    },
    currentCombatant(): EncounterCombatant | undefined {
      return this.ownedCombatants.find((combatant) => combatant.can_end_turn);
    },
    nextCombatant(): EncounterCombatant | undefined {
      if (this.currentCombatantId === null || this.orderedCombatants.length < 2) {
        return undefined;
      }

      const currentIndex = this.orderedCombatants.findIndex(
        (combatant) => combatant.id === this.currentCombatantId,
      );
      if (currentIndex === -1) {
        return undefined;
      }

      return this.orderedCombatants[(currentIndex + 1) % this.orderedCombatants.length];
    },
    upNextCombatant(): EncounterCombatant | undefined {
      if (this.currentCombatant) {
        return undefined;
      }

      return this.nextCombatant?.character_id === this.characterId
        ? this.nextCombatant
        : undefined;
    },
    encounterHeading(): string {
      if (this.currentCombatant) {
        return "It’s your turn";
      }

      if (this.tieCombatant) {
        return "Initiative decision required";
      }

      return "Get ready, your turn is next";
    },
    tieOutcome(): string {
      if (!this.tieCombatant) {
        return "";
      }

      return `${this.tieCombatant.tie_votes_cast} of ${this.tieCombatant.tie_votes_required} players voted. Waiting for everyone before resolving the tie.`;
    },
  },
  methods: {
    announceTieResolution(): void {
      const combatant = this.resolvedTieCombatant;

      if (!combatant) {
        return;
      }

      const winner = combatant.tie_options.find(
        (option) => option.combatant_id === combatant.tie_winner_id,
      );
      if (!winner) {
        return;
      }

      const agreementReached = combatant.tie_resolution === "agreement";
      this.$toast.add({
        severity: agreementReached ? "success" : "info",
        summary: agreementReached
          ? "Initiative agreement reached"
          : "Initiative tie resolved",
        detail: agreementReached
          ? `${winner.name} will go first.`
          : `No agreement was reached, so Hoard selected ${winner.name}.`,
        life: 5_000,
      });
    },
    async chooseTie(combatantId: number): Promise<void> {
      const recorded = await this.runAction(
        () => chooseInitiativeTie(this.contextId, combatantId),
        "Unable to record your initiative choice.",
      );
      if (recorded) {
        this.$toast.add({
          severity: "success",
          summary: "Initiative vote recorded",
          detail: "The shared vote count will update now.",
          life: 4_000,
        });
      }
    },
    async finishTurn(): Promise<void> {
      await this.runAction(
        () => endPlayerTurn(this.contextId),
        "Unable to end your turn.",
      );
    },
    voteLabel(count: number): string {
      return `${count} ${count === 1 ? "vote" : "votes"}`;
    },
    async runAction(
      action: () => Promise<void>,
      fallbackError: string,
    ): Promise<boolean> {
      this.busy = true;
      this.error = "";

      try {
        await action();
        return true;
      } catch (exception) {
        this.error = exception instanceof Error ? exception.message : fallbackError;
        return false;
      } finally {
        this.busy = false;
      }
    },
  },
});
</script>
