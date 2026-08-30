<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { createMoneyTransfer, getCharacters, type Character } from "../api";
import { createSnackbarDismissHandler } from "../dismissibleMessage";
import CoinAmountPicker from "./CoinAmountPicker.vue";
import GmCharacterSelect from "./GmCharacterSelect.vue";
const props = defineProps<{ contextId: number }>();
const emit = defineEmits<{ completed: [message: string] }>();
const characterId = ref<number>();
const action = ref<"give" | "take">("give");
const amounts = ref<Record<string, number>>({ pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 });
const description = ref("");
const error = ref("");
const clearErrorWhenClosed = createSnackbarDismissHandler(error);
const characters = ref<Character[]>([]);
const selectedCharacter = computed(() =>
  characters.value.find((character) => character.id === characterId.value),
);

const submittedAmounts = computed(() =>
  Object.fromEntries(
    Object.entries(amounts.value).filter(
      ([, amount]) => Number.isInteger(amount) && amount > 0,
    ),
  ),
);
const hasInvalidAmount = computed(() =>
  Object.values(amounts.value).some(
    (amount) => !Number.isInteger(amount) || amount < 0,
  ),
);
const hasAmounts = computed(() => Object.keys(submittedAmounts.value).length > 0);

async function submit() {
  try {
    error.value = "";
    await createMoneyTransfer(props.contextId, {
      from_character_id: action.value === "give" ? null : (characterId.value ?? null),
      to_character_id: action.value === "give" ? (characterId.value ?? null) : null,
      amounts: submittedAmounts.value,
      description: description.value,
    });
    description.value = "";
    amounts.value = { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 };
    const recipient = selectedCharacter.value?.name ?? "character";
    emit(
      "completed",
      action.value === "give"
        ? `Granted coins to ${recipient}.`
        : `Took coins from ${recipient}.`,
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
  <v-card
    class="pa-2 h-100"
    color="surface"
  >
    <v-card-title class="text-h5">
      <v-icon
        color="primary"
        class="mr-2"
      >
        mdi-cash-multiple
      </v-icon>
      Coins
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
      <CoinAmountPicker v-model="amounts" />
      <v-textarea
        v-model="description"
        label="Reason"
      />
      <v-snackbar
        :model-value="Boolean(error)"
        color="error"
        @update:model-value="clearErrorWhenClosed"
      >
        {{ error }}
      </v-snackbar>
      <v-alert
        v-if="hasInvalidAmount"
        type="error"
        density="compact"
        class="mb-3"
      >
        Amounts must be whole numbers of zero or more.
      </v-alert>
      <v-btn
        block
        :color="action === 'give' ? 'primary' : 'error'"
        size="large"
        :disabled="!characterId || !hasAmounts || hasInvalidAmount"
        @click="submit"
      >
        Confirm {{ action }}
      </v-btn>
    </v-card-text>
  </v-card>
</template>
