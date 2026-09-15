<template>
  <section
    class="border rounded-3 p-3 p-md-4 h-100"
    aria-labelledby="shared-xp-heading"
  >
    <header class="mb-3">
      <h3
        id="shared-xp-heading"
        class="h4"
      >
        <span
          class="mdi mdi-star-four-points"
          aria-hidden="true"
        />
        Give shared XP
      </h3>
      <p class="mb-0 text-body-secondary">
        Level {{ level }} · {{ sharedExperience.toLocaleString() }} shared XP
      </p>
    </header>
    <label class="d-grid gap-2 mb-3">
      <span class="fw-semibold">Total encounter XP</span>
      <InputNumber
        v-model="amount"
        :min="1"
        fluid
      />
    </label>
    <section
      class="border-start border-4 ps-3 mb-3"
      aria-live="polite"
    >
      <h4 class="h6">Live preview</h4>
      <strong v-if="preview">{{ preview }} XP each</strong>
      <p v-else>Enter a valid XP amount.</p>
    </section>
    <label class="d-grid gap-2 mb-3">
      <span class="fw-semibold">Reason / encounter</span>
      <Textarea
        v-model="description"
        fluid
        rows="2"
      />
    </label>
    <Message
      v-if="error"
      severity="error"
    >
      {{ error }}
    </Message>
    <div class="d-flex justify-content-end">
      <Button
        :disabled="!preview"
        label="Award XP"
        @click="submit"
      />
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import Textarea from "primevue/textarea";
import { createSharedXpAward, type Character } from "@/api";

export default defineComponent({
  components: { Button, InputNumber, Message, Textarea },
  props: {
    contextId: { type: Number, required: true },
    characters: { type: Array as PropType<Character[]>, required: true },
    level: { type: Number, required: true },
    sharedExperience: { type: Number, required: true },
  },
  emits: ["completed"],
  data() {
    return { amount: 10, description: "", error: "" };
  },
  computed: {
    recipients(): number {
      return this.characters.filter(
        (item) => item.is_active && item.is_player_character,
      ).length;
    },
    preview(): number {
      return this.recipients && this.amount > 0
        ? Math.floor(this.amount / this.recipients)
        : 0;
    },
  },
  methods: {
    async submit(): Promise<void> {
      try {
        this.error = "";
        await createSharedXpAward(this.contextId, {
          amount: this.amount,
          description: this.description,
        });
        this.description = "";
        this.$emit(
          "completed",
          `Awarded ${this.preview} XP to each of ${this.recipients} active PCs.`,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to award XP.";
      }
    },
  },
});
</script>
