<template>
  <section
    class="border rounded-3 p-3 p-md-4 h-100"
    aria-labelledby="coin-transfer-heading"
  >
    <header class="mb-3">
      <h3
        id="coin-transfer-heading"
        class="h4"
      >
        <span
          class="mdi mdi-cash-multiple"
          aria-hidden="true"
        />
        Coins
      </h3>
    </header>
    <GmCharacterSelect
      :characters="characters"
      @selected="characterId = $event"
    />
    <div
      class="d-flex gap-2 my-3"
      aria-label="Coin transfer direction"
    >
      <Button
        :outlined="action !== 'give'"
        label="Give"
        @click="action = 'give'"
      />
      <Button
        severity="danger"
        :outlined="action !== 'take'"
        label="Take"
        @click="action = 'take'"
      />
    </div>
    <CoinAmountPicker v-model="amounts" />
    <label class="d-grid gap-2 mt-3">
      <span class="fw-semibold">Reason</span>
      <Textarea
        v-model="description"
        fluid
        rows="2"
      />
    </label>
    <Message
      v-if="hasInvalidAmount"
      severity="error"
    >
      Amounts must be whole numbers of zero or more.
    </Message>
    <div class="d-flex justify-content-end mt-3">
      <Button
        :severity="action === 'give' ? 'primary' : 'danger'"
        :disabled="!characterId || !hasAmounts || hasInvalidAmount"
        :label="`Confirm ${action}`"
        @click="submit"
      />
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Button from "primevue/button";
import Message from "primevue/message";
import Textarea from "primevue/textarea";
import { createMoneyTransfer, getCharacters, type Character } from "../api";
import CoinAmountPicker from "./CoinAmountPicker.vue";
import GmCharacterSelect from "./GmCharacterSelect.vue";
export default defineComponent({
  components: {
    Button,
    Message,
    Textarea,
    CoinAmountPicker,
    GmCharacterSelect,
  },
  props: { contextId: { type: Number, required: true } },
  emits: ["completed"],
  data() {
    return {
      characterId: undefined as number | undefined,
      action: "give" as "give" | "take",
      amounts: { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 } as Record<string, number>,
      description: "",
      error: "",
      characters: [] as Character[],
    };
  },
  computed: {
    selectedCharacter(): Character | undefined {
      return this.characters.find((character) => character.id === this.characterId);
    },
    submittedAmounts(): Record<string, number> {
      return Object.fromEntries(
        Object.entries(this.amounts).filter(
          ([, amount]) => Number.isInteger(amount) && amount > 0,
        ),
      );
    },
    hasInvalidAmount(): boolean {
      return Object.values(this.amounts).some(
        (amount) => !Number.isInteger(amount) || amount < 0,
      );
    },
    hasAmounts(): boolean {
      return Object.keys(this.submittedAmounts).length > 0;
    },
  },

  async mounted(): Promise<void> {
    this.characters = await getCharacters(this.contextId);
  },
  methods: {
    async submit(): Promise<void> {
      try {
        this.error = "";
        await createMoneyTransfer(this.contextId, {
          from_character_id: this.action === "give" ? null : (this.characterId ?? null),
          to_character_id: this.action === "give" ? (this.characterId ?? null) : null,
          amounts: this.submittedAmounts,
          description: this.description,
        });
        this.description = "";
        this.amounts = { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 };
        const recipient = this.selectedCharacter?.name ?? "character";
        this.$emit(
          "completed",
          this.action === "give"
            ? `Granted coins to ${recipient}.`
            : `Took coins from ${recipient}.`,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to move coins.";
      }
    },
  },
});
</script>
