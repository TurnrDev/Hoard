<template>
  <time
    :datetime="value"
    :title="absoluteTime"
  >
    {{ relativeTime }}
    <span class="visually-hidden">({{ absoluteTime }})</span>
  </time>
</template>

<script lang="ts">
import moment from "moment";
import { defineComponent } from "vue";

export default defineComponent({
  props: {
    value: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      absoluteTime: "",
      relativeTime: "",
      refreshTimer: undefined as number | undefined,
    };
  },
  watch: {
    value: {
      immediate: true,
      handler(): void {
        this.updateLabels();
      },
    },
  },
  mounted() {
    this.refreshTimer = window.setInterval(() => {
      this.updateLabels();
    }, 30_000);
  },
  beforeUnmount() {
    if (this.refreshTimer !== undefined) {
      window.clearInterval(this.refreshTimer);
    }
  },
  methods: {
    updateLabels(): void {
      const parsedValue = moment(this.value);

      if (!parsedValue.isValid()) {
        this.absoluteTime = this.value;
        this.relativeTime = this.value;

        return;
      }

      this.absoluteTime = parsedValue.format("LLLL");
      this.relativeTime = parsedValue.fromNow();
    },
  },
});
</script>
