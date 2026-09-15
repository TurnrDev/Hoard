<template>
  <section
    class="gm-action-form"
    aria-labelledby="give-item-heading"
  >
    <header>
      <h2 id="give-item-heading">
        <span
          class="mdi mdi-gift"
          aria-hidden="true"
        />
        Give item
      </h2>
    </header>
    <GmCharacterSelect
      :characters="characters"
      @selected="characterId = $event"
    />
    <ItemPickerDialog
      v-model="itemId"
      :candidates="candidates"
      label="Item to grant"
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
      :disabled="!characterId || !itemId"
      label="Give item"
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
} from "@/api";
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
    candidates(): PickerCandidate[] {
      return this.items.map((item) => ({ item }));
    },
    selectedCharacter(): Character | undefined {
      return this.characters.find((character) => character.id === this.characterId);
    },
    selectedItem(): Item | undefined {
      return this.items.find((item) => item.id === this.itemId);
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
          from_character_id: null,
          to_character_id: this.characterId ?? null,
          item_id: this.itemId ?? 0,
          quantity: this.quantity,
          description: this.description,
        });
        this.$emit(
          "completed",
          `Granted ${this.selectedCharacter?.name ?? "character"} ${this.quantity} × ${this.selectedItem?.name ?? "item"}.`,
        );
        this.itemId = undefined;
        this.quantity = 1;
        this.description = "";
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to give item.";
      }
    },
  },
});
</script>
