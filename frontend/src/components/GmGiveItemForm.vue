<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  createInventoryTransaction,
  getCharacters,
  type Character,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";
import GmCharacterSelect from "./GmCharacterSelect.vue";
import ItemPickerDialog from "./ItemPickerDialog.vue";
const props = defineProps<{
  contextId: number;
  items: Item[];
}>();
const emit = defineEmits<{ completed: [message: string] }>();
const characterId = ref<number>();
const itemId = ref<number>();
const quantity = ref(1);
const description = ref("");
const error = ref("");
const characters = ref<Character[]>([]);
const candidates = computed<PickerCandidate[]>(() =>
  props.items.map((item) => ({ item })),
);
const selectedCharacter = computed(() =>
  characters.value.find((character) => character.id === characterId.value),
);
const selectedItem = computed(() =>
  props.items.find((item) => item.id === itemId.value),
);

async function submit() {
  try {
    error.value = "";
    await createInventoryTransaction(props.contextId, {
      from_character_id: null,
      to_character_id: characterId.value ?? null,
      item_id: itemId.value ?? 0,
      quantity: quantity.value,
      description: description.value,
    });
    emit(
      "completed",
      `Granted ${selectedCharacter.value?.name ?? "character"} ${quantity.value} × ${selectedItem.value?.name ?? "item"}.`,
    );
    itemId.value = undefined;
    quantity.value = 1;
    description.value = "";
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to give item.";
  }
}

onMounted(async () => {
  characters.value = await getCharacters(props.contextId);
});
</script>
<template>
  <v-card
    class="pa-2 h-100"
    color="surface"
  >
    <v-card-title class="text-h5">
      <v-icon
        color="primary"
        class="mr-2"
      >
        mdi-gift
      </v-icon>
      Give item
    </v-card-title>
    <v-card-text>
      <GmCharacterSelect
        :characters="characters"
        @selected="characterId = $event"
      />
      <ItemPickerDialog
        v-model="itemId"
        :candidates="candidates"
        label="Item to grant"
      />
      <v-number-input
        v-model.number="quantity"
        control-variant="split"
        :min="1"
        label="Quantity"
      />
      <v-textarea
        v-model="description"
        label="Reason"
      />
      <v-snackbar
        :model-value="Boolean(error)"
        color="error"
        @update:model-value="(visible) => !visible && (error = '')"
      >
        {{ error }}
      </v-snackbar>
      <v-btn
        block
        color="primary"
        size="large"
        :disabled="!characterId || !itemId"
        @click="submit"
      >
        Give item
      </v-btn>
    </v-card-text>
  </v-card>
</template>
