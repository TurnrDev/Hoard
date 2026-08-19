<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { createMoneyTransfer, getCharacters, type Character } from "../api";
import GmCharacterSelect from "./GmCharacterSelect.vue";
const props = defineProps<{ contextId: number }>();
const emit = defineEmits<{ completed: [message: string] }>();
const characterId = ref<number>();
const denomination = ref("gp");
const amount = ref(1);
const description = ref("");
const error = ref("");
const characters = ref<Character[]>([]);
const selectedCharacter = computed(() =>
  characters.value.find((character) => character.id === characterId.value),
);
async function submit(give: boolean) {
  try {
    error.value = "";
    await createMoneyTransfer(props.contextId, {
      from_character_id: give ? null : (characterId.value ?? null),
      to_character_id: give ? (characterId.value ?? null) : null,
      amounts: { [denomination.value]: amount.value },
      description: description.value,
    });
    description.value = "";
    const recipient = selectedCharacter.value?.name ?? "character";
    emit(
      "completed",
      give
        ? `Granted ${recipient} ${amount.value} ${denomination.value}.`
        : `Took ${amount.value} ${denomination.value} from ${recipient}.`,
    );
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to move coins.";
  }
}
onMounted(async () => {
  characters.value = await getCharacters(props.contextId);
});
</script>
<template>
  <v-card class="pa-2 h-100" color="surface"
    ><v-card-title class="text-h5"
      ><v-icon color="primary" class="mr-2">mdi-coins</v-icon>Give or take
      coins</v-card-title
    ><v-card-text
      ><GmCharacterSelect
        :characters="characters"
        @selected="characterId = $event"
      /><v-select
        v-model="denomination"
        :items="['cp', 'sp', 'ep', 'gp', 'pp']"
        label="Denomination"
      /><v-text-field
        v-model.number="amount"
        type="number"
        min="1"
        label="Amount"
      /><v-textarea v-model="description" label="Reason" /><v-snackbar
        :model-value="Boolean(error)"
        color="error"
        @update:model-value="(visible) => !visible && (error = '')"
        >{{ error }}</v-snackbar
      >
      <div class="d-flex ga-3">
        <v-btn
          class="flex-grow-1"
          color="primary"
          size="large"
          :disabled="!characterId"
          @click="submit(true)"
          >Give coins</v-btn
        ><v-btn
          class="flex-grow-1"
          color="error"
          size="large"
          :disabled="!characterId"
          @click="submit(false)"
          >Take coins</v-btn
        >
      </div></v-card-text
    ></v-card
  >
</template>
