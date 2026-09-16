<template>
  <ProgressBar
    :class="healthClass"
    :value="percentage"
    :show-value="false"
    :aria-label="label"
  />
</template>

<script lang="ts">
import ProgressBar from "primevue/progressbar";
import { defineComponent } from "vue";

export default defineComponent({
  components: { ProgressBar },
  props: {
    percentage: { type: Number, required: true },
    label: { type: String, required: true },
  },
  computed: {
    healthClass():
      "health-bar--critical" | "health-bar--wounded" | "health-bar--healthy" {
      if (this.percentage <= 25) {
        return "health-bar--critical";
      }

      if (this.percentage <= 60) {
        return "health-bar--wounded";
      }

      return "health-bar--healthy";
    },
  },
});
</script>
