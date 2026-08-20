<script setup lang="ts">
import { computed, ref } from "vue";
import { adjustCalendar, type CampaignCalendar } from "../api";
import { formatCampaignDate } from "../calendar";

const props = defineProps<{ contextId: number; calendar: CampaignCalendar }>();
const emit = defineEmits<{ changed: [calendar: CampaignCalendar] }>();
const busy = ref(false);
const error = ref("");
const canDecrement = computed(() => props.calendar.year > 1 || props.calendar.day > 1);

async function adjust(amount: -1 | 1): Promise<void> {
  busy.value = true;
  error.value = "";
  try {
    emit("changed", await adjustCalendar(props.contextId, amount));
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update date.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <v-card>
    <v-card-title class="text-overline">Campaign date</v-card-title>
    <v-card-text>
      <div class="text-h5">{{ formatCampaignDate(calendar) }}</div>
      <div class="text-caption">{{ calendar.era_name }}</div>
      <v-alert
        v-if="error"
        density="compact"
        type="error"
        class="mt-3"
      >
        {{ error }}
      </v-alert>
    </v-card-text>
    <v-card-actions>
      <v-btn
        :disabled="!canDecrement"
        :loading="busy"
        prepend-icon="mdi-minus"
        @click="adjust(-1)"
      >
        DEC one day
      </v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        :loading="busy"
        append-icon="mdi-plus"
        @click="adjust(1)"
      >
        INC one day
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
