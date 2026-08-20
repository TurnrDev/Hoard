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
  <v-card class="profile-card h-100">
    <v-card-text class="d-flex align-center justify-space-between h-100">
      <div>
        <div class="text-h5">{{ formatCampaignDate(calendar) }}</div>
        <div class="text-caption">{{ calendar.era_name }}</div>
      </div>
      <v-alert
        v-if="error"
        density="compact"
        type="error"
        class="mt-3"
      >
        {{ error }}
      </v-alert>
      <div class="d-flex ga-1">
        <v-btn
          icon="mdi-minus"
          size="small"
          variant="text"
          :disabled="!canDecrement"
          :loading="busy"
          aria-label="Decrement campaign date by one day"
          @click="adjust(-1)"
        />
        <v-btn
          icon="mdi-plus"
          size="small"
          variant="text"
          color="primary"
          :loading="busy"
          aria-label="Increment campaign date by one day"
          @click="adjust(1)"
        />
      </div>
    </v-card-text>
  </v-card>
</template>
