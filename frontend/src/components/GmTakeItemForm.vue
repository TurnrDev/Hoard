<template>
  <section
    class="gm-action-form"
    aria-labelledby="take-item-heading"
  >
    <header>
      <h2 id="take-item-heading">
        <span
          class="mdi mdi-package-variant-remove"
          aria-hidden="true"
        />
        Take item
      </h2>
    </header>
    <GmCharacterSelect
      :characters="characters"
      @selected="characterId = $event"
    />
    <ItemPickerDialog
      v-model="itemId"
      :candidates="candidates"
      label="Item in inventory"
      no-data-text="This character has no recorded items."
    />
    <label class="form-field">
      <span>Quantity</span>
      <InputNumber
        v-model="quantity"
        :min="1"
      />
    </label>
    <label class="form-field">
      <span>Reason</span>
      <Textarea v-model="description" />
    </label>
    <Message
      v-if="error"
      severity="error"
    >
      {{ error }}
    </Message>
    <Button
      severity="danger"
      :disabled="!characterId || !itemId"
      label="Take item"
      @click="submit"
    />
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import Textarea from "primevue/textarea";
import {
  createInventoryTransaction,
  getCharacters,
  type Character,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";
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
    items: { type: Array as PropType<Item[]>, required: true },
  },
  emits: ["completed"],
  data() {
    return {
      characterId: undefined as number | undefined,
      itemId: undefined as number | undefined,
      quantity: 1,
      description: "",
      error: "",
      characters: [] as Character[],
    };
  },
  computed: {
    selected(): Character | undefined {
      return this.characters.find((item) => item.id === this.characterId);
    },
    candidates(): PickerCandidate[] {
      return (
        this.selected?.inventory.flatMap((entry) => {
          const item = this.items.find((value) => value.id === entry.item_id);
          return item ? [{ item, quantity: entry.quantity }] : [];
        }) ?? []
      );
    },
    selectedItem(): Item | undefined {
      return this.items.find((item) => item.id === this.itemId);
    },
  },
  watch: {
    candidates(values: PickerCandidate[]): void {
      if (!values.some((value) => value.item.id === this.itemId)) {
        this.itemId = undefined;
      }
    },
  },
  async mounted(): Promise<void> {
    this.characters = await getCharacters(this.contextId);
  },
  methods: {
    async submit(): Promise<void> {
      try {
        this.error = "";
        await createInventoryTransaction(this.contextId, {
          from_character_id: this.characterId ?? null,
          to_character_id: null,
          item_id: this.itemId ?? 0,
          quantity: this.quantity,
          description: this.description,
        });
        this.$emit(
          "completed",
          `Took ${this.quantity} × ${this.selectedItem?.name ?? "item"} from ${this.selected?.name ?? "character"}.`,
        );
        this.itemId = undefined;
        this.quantity = 1;
        this.description = "";
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to take item.";
      }
    },
  },
});
</script>
