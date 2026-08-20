<script setup lang="ts">
import { computed, ref } from "vue";
import { createSharedXpAward, type Character } from "../api";

const props = defineProps<{ contextId: number; characters: Character[] }>();
const emit = defineEmits<{ completed: [message: string] }>();
const amount = ref(10);
const description = ref("");
const error = ref("");
const recipients = computed(
  () =>
    props.characters.filter((item) => item.is_active && item.is_player_character)
      .length,
);
const preview = computed(() =>
  recipients.value && amount.value > 0
    ? Math.floor(amount.value / recipients.value)
    : 0,
);

async function submit() {
  try {
    error.value = "";
    await createSharedXpAward(props.contextId, {
      amount: amount.value,
      description: description.value,
    });
    description.value = "";
    emit(
      "completed",
      `Awarded ${preview.value} XP to each of ${recipients.value} active PCs.`,
    );
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to award XP.";
  }
}
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
        mdi-star-four-points
      </v-icon>
      Give shared XP
    </v-card-title>
    <v-card-text>
      <v-text-field
        v-model.number="amount"
        type="number"
        min="1"
        label="Total encounter XP"
      />
      <v-sheet
        rounded
        class="pa-4 mb-3"
        color="background"
      >
        <div class="text-caption">Live preview</div>
        <div
          v-if="preview"
          class="text-h3 text-primary"
        >
          {{ preview }} XP each
        </div>
        <div
          v-else
          class="text-medium-emphasis"
        >
          Enter a valid XP amount.
        </div>
      </v-sheet>
      <v-textarea
        v-model="description"
        label="Reason / encounter"
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
        :disabled="!preview"
        @click="submit"
      >
        Award XP
      </v-btn>
    </v-card-text>
  </v-card>
</template>
