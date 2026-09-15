<template>
  <section
    class="border rounded-3 p-3 p-md-4 h-100"
    aria-labelledby="items-heading"
  >
    <header class="mb-3">
      <h3
        id="items-heading"
        class="h4"
      >
        <span
          class="mdi mdi-package-variant"
          aria-hidden="true"
        />
        Items
      </h3>
    </header>
    <GmCharacterSelect
      :characters="characters"
      @selected="characterId = $event"
    />
    <div class="d-flex gap-2 my-3">
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
    <ItemPickerDialog
      v-model="itemId"
      :candidates="candidates"
      :label="action === 'give' ? 'Item' : 'Item in inventory'"
    />
    <label class="d-grid gap-2 mt-3">
      <span class="fw-semibold">Quantity</span>
      <InputNumber
        v-model="quantity"
        :min="1"
        fluid
      />
    </label>
    <label class="d-grid gap-2 mt-3">
      <span class="fw-semibold">Reason</span>
      <Textarea
        v-model="description"
        rows="2"
        fluid
      />
    </label>
    <Message
      v-if="error"
      severity="error"
    >
      {{ error }}
    </Message>
    <div class="d-flex justify-content-end mt-3">
      <Button
        :severity="action === 'give' ? 'primary' : 'danger'"
        :disabled="!characterId || !itemId || quantity < 1"
        :label="`Confirm ${action}`"
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
import { createInventoryTransaction, type Character, type Item } from "@/api";
import type { PickerCandidate } from "@/campaigns/itemPicker";
import GmCharacterSelect from "./GmCharacterSelect.vue";
import ItemPickerDialog from "./ItemPickerDialog.vue";

export default defineComponent({
  components: {
    Button,
    InputNumber,
    Message,
    Textarea,
    GmCharacterSelect,
    ItemPickerDialog,
  },
  props: {
    contextId: { type: Number, required: true },
    characters: { type: Array as PropType<Character[]>, required: true },
    items: { type: Array as PropType<Item[]>, required: true },
  },
  emits: ["completed"],
  data() {
    return {
      characterId: undefined as number | undefined,
      itemId: undefined as number | undefined,
      quantity: 1,
      description: "",
      action: "give" as "give" | "take",
      error: "",
    };
  },
  computed: {
    selectedCharacter(): Character | undefined {
      return this.characters.find((item) => item.id === this.characterId);
    },
    candidates(): PickerCandidate[] {
      return this.action === "give"
        ? this.items.map((item) => ({ item }))
        : (this.selectedCharacter?.inventory.flatMap((entry) => {
            const item = this.items.find((value) => value.id === entry.item_id);
            return item ? [{ item, quantity: entry.quantity }] : [];
          }) ?? []);
    },
    selectedItem(): Item | undefined {
      return this.items.find((item) => item.id === this.itemId);
    },
  },
  watch: {
    candidates(values: PickerCandidate[]): void {
      if (!values.some(({ item }) => item.id === this.itemId)) {
        this.itemId = undefined;
      }
    },
  },
  methods: {
    async submit(): Promise<void> {
      try {
        this.error = "";
        await createInventoryTransaction(this.contextId, {
          from_character_id: this.action === "take" ? (this.characterId ?? null) : null,
          to_character_id: this.action === "give" ? (this.characterId ?? null) : null,
          item_id: this.itemId ?? 0,
          quantity: this.quantity,
          description: this.description,
        });
        this.$emit(
          "completed",
          `${this.action === "give" ? "Gave" : "Took"} ${this.quantity} × ${this.selectedItem?.name ?? "item"}.`,
        );
        this.itemId = undefined;
        this.quantity = 1;
        this.description = "";
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to move item.";
      }
    },
  },
});
</script>
