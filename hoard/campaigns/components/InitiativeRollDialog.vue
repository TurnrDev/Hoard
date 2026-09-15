<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :close-on-escape="false"
    :dismissable-mask="false"
    :draggable="false"
    class="initiative-roll-dialog"
    :header="bonusRoll ? 'Roll your second initiative' : 'Roll initiative'"
  >
    <form
      class="d-grid gap-3"
      @submit.prevent="submitInitiative"
    >
      <div
        v-if="bonusRoll"
        class="alert alert-success mb-0"
        role="status"
      >
        <strong>Natural 20!</strong>
        You act at the top of the order and gain one additional initiative.
      </div>

      <div>
        <p class="fs-5 fw-semibold mb-1">Enter your bare d20 roll</p>
        <p class="text-body-secondary mb-0">
          Enter only the number shown on the die. Hoard adds your Dexterity modifier and
          shows your resulting initiative.
        </p>
      </div>

      <div class="d-grid gap-2">
        <label
          for="player-initiative-roll"
          class="fw-semibold"
        >
          {{ bonusRoll ? "Second d20 roll" : "Initiative roll" }} (1–20)
        </label>
        <InputNumber
          v-model="initiativeRoll"
          input-id="player-initiative-roll"
          :min="1"
          :max="20"
          show-buttons
          button-layout="horizontal"
          :disabled="busy"
        />
      </div>

      <small class="text-body-secondary">
        Your Dexterity modifier is
        <strong>{{ signedModifier }}</strong>
        .
      </small>

      <Message
        v-if="error"
        severity="error"
        :closable="false"
      >
        {{ error }}
      </Message>

      <Button
        type="submit"
        :label="bonusRoll ? 'Set second initiative' : 'Set my initiative'"
        icon="mdi mdi-dice-d20-outline"
        :loading="busy"
      />
    </form>
  </Dialog>
</template>

<script lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import { defineComponent, type PropType } from "vue";
import { rollPlayerInitiative, type EncounterCombatant } from "@/api";

export default defineComponent({
  components: {
    Button,
    Dialog,
    InputNumber,
    Message,
  },
  props: {
    contextId: { type: Number, required: true },
    combatant: {
      type: Object as PropType<EncounterCombatant>,
      required: true,
    },
    bonusRoll: { type: Boolean, default: false },
  },
  data() {
    return {
      visible: true,
      initiativeRoll: 10,
      busy: false,
      error: "",
    };
  },
  computed: {
    signedModifier(): string {
      const modifier = this.combatant.initiative_modifier;

      return modifier >= 0 ? `+${modifier}` : `${modifier}`;
    },
  },
  watch: {
    "combatant.id"(): void {
      this.visible = true;
      this.initiativeRoll = 10;
      this.error = "";
    },
  },
  methods: {
    async submitInitiative(): Promise<void> {
      this.busy = true;
      this.error = "";

      try {
        await rollPlayerInitiative(this.contextId, this.initiativeRoll);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to submit your initiative roll.";
      } finally {
        this.busy = false;
      }
    },
  },
});
</script>

<style>
.initiative-roll-dialog {
  width: min(32rem, calc(100vw - 2rem));
}
</style>
