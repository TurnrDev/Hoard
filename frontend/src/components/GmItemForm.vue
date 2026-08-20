<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  createInventoryTransaction,
  getCharacters,
  type Character,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";
import GmCharacterSelect from "./GmCharacterSelect.vue";
import ItemPickerDialog from "./ItemPickerDialog.vue";

const props = defineProps<{ contextId: number; items: Item[] }>();
const emit = defineEmits<{ completed: [message: string] }>();
const characterId = ref<number>();
const itemId = ref<number>();
const quantity = ref(1);
const description = ref("");
const action = ref<"give" | "take">("give");
const error = ref("");
const characters = ref<Character[]>([]);
const selectedCharacter = computed(() =>
  characters.value.find((item) => item.id === characterId.value),
);
const candidates = computed<PickerCandidate[]>(() =>
  action.value === "give"
    ? props.items.map((item) => ({ item }))
    : (selectedCharacter.value?.inventory.flatMap((entry) => {
        const item = props.items.find((value) => value.id === entry.item_id);
        return item ? [{ item, quantity: entry.quantity }] : [];
      }) ?? []),
);
const selectedItem = computed(() =>
  props.items.find((item) => item.id === itemId.value),
);

watch(candidates, (values) => {
  if (!values.some(({ item }) => item.id === itemId.value)) itemId.value = undefined;
});

async function submit(): Promise<void> {
  try {
    error.value = "";
    await createInventoryTransaction(props.contextId, {
      from_character_id: action.value === "take" ? (characterId.value ?? null) : null,
      to_character_id: action.value === "give" ? (characterId.value ?? null) : null,
      item_id: itemId.value ?? 0,
      quantity: quantity.value,
      description: description.value,
    });
    emit(
      "completed",
      `${action.value === "give" ? "Gave" : "Took"} ${quantity.value} × ${selectedItem.value?.name ?? "item"}.`,
    );
    itemId.value = undefined;
    quantity.value = 1;
    description.value = "";
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to move item.";
  }
}

onMounted(async () => {
  characters.value = await getCharacters(props.contextId);
});
</script>

<template>
  <v-card
    class="pa-2 h-100 action-card"
    color="surface"
  >
    <v-card-title class="text-h6">
      <v-icon
        color="primary"
        class="mr-2"
      >
        mdi-package-variant
      </v-icon>
      Items
    </v-card-title>
    <v-card-text>
      <GmCharacterSelect
        :characters="characters"
        @selected="characterId = $event"
      />
      <v-btn-toggle
        v-model="action"
        mandatory
        divided
        class="mb-4 w-100"
        color="primary"
      >
        <v-btn value="give">Give</v-btn>
        <v-btn
          value="take"
          color="error"
        >
          Take
        </v-btn>
      </v-btn-toggle>
      <ItemPickerDialog
        v-model="itemId"
        :candidates="candidates"
        :label="action === 'give' ? 'Item' : 'Item in inventory'"
      />
      <v-text-field
        v-model.number="quantity"
        type="number"
        min="1"
        label="Quantity"
      />
      <v-textarea
        v-model="description"
        label="Reason"
        rows="2"
      />
      <v-alert
        v-if="error"
        type="error"
        density="compact"
        class="mb-3"
      >
        {{ error }}
      </v-alert>
      <v-btn
        block
        :color="action === 'give' ? 'primary' : 'error'"
        :disabled="!characterId || !itemId || quantity < 1"
        @click="submit"
      >
        Confirm {{ action }}
      </v-btn>
    </v-card-text>
  </v-card>
</template>
