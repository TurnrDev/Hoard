<template>
  <section
    class="border rounded-3 p-3 p-md-4 h-100"
    aria-labelledby="campaign-date-heading"
  >
    <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          In-world date
        </p>
        <h2
          id="campaign-date-heading"
          class="h3 mb-1"
        >
          {{ formatCampaignDate(calendar) }}
        </h2>
        <p class="mb-0 text-body-secondary">{{ calendar.era_name }}</p>
      </div>
      <Message
        v-if="error"
        severity="error"
      >
        {{ error }}
      </Message>
      <div class="d-flex gap-2">
        <Button
          icon="mdi mdi-minus"
          text
          :disabled="!canDecrement"
          :loading="busy"
          aria-label="Decrement campaign date by one day"
          @click="adjust(-1)"
        />
        <Button
          icon="mdi mdi-plus"
          text
          :loading="busy"
          aria-label="Increment campaign date by one day"
          @click="adjust(1)"
        />
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Button from "primevue/button";
import Message from "primevue/message";
import { adjustCalendar, type CampaignCalendar } from "../api";
import { formatCampaignDate } from "../calendar";

export default defineComponent({
  components: { Button, Message },
  props: {
    contextId: { type: Number, required: true },
    calendar: { type: Object as PropType<CampaignCalendar>, required: true },
  },
  data() {
    return { busy: false, error: "" };
  },
  computed: {
    canDecrement(): boolean {
      return this.calendar.year > 1 || this.calendar.day > 1;
    },
  },
  methods: {
    formatCampaignDate,
    async adjust(amount: -1 | 1): Promise<void> {
      this.busy = true;
      this.error = "";
      try {
        await adjustCalendar(this.contextId, amount);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update date.";
      } finally {
        this.busy = false;
      }
    },
  },
});
</script>
