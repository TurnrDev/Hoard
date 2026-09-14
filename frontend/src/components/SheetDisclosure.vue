<template>
  <details class="sheet-disclosure border rounded-3">
    <summary class="d-flex align-items-center gap-2 p-3">
      <span
        class="mdi mdi-chevron-right sheet-disclosure__chevron"
        aria-hidden="true"
      />
      <span class="fw-semibold">{{ title }}</span>
      <span
        v-if="count !== undefined"
        class="small text-body-secondary tabular-nums"
      >
        {{ count }}
      </span>
    </summary>
    <div class="border-top p-3">
      <slot />
    </div>
  </details>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  props: {
    title: {
      type: String,
      required: true,
    },
    count: {
      type: Number,
      default: undefined,
    },
  },
});
</script>

<style scoped>
.sheet-disclosure > summary {
  cursor: pointer;
  list-style: none;
}

.sheet-disclosure > summary::-webkit-details-marker {
  display: none;
}

.sheet-disclosure__chevron {
  transition: transform 150ms ease;
}

.sheet-disclosure[open] .sheet-disclosure__chevron {
  transform: rotate(90deg);
}

@media (prefers-reduced-motion: reduce) {
  .sheet-disclosure__chevron {
    transition: none;
  }
}
</style>
