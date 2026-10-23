<template>
  <article class="border rounded-3 p-3 p-md-4 h-100">
    <header class="text-uppercase fw-semibold small text-body-secondary">
      {{ label }}
    </header>

    <div class="h4 mt-3 mb-0 tabular-nums">
      <slot>{{ summary }}</slot>
    </div>
  </article>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  props: {
    label: { type: String, required: true },
    summary: { type: String, required: true },
  },
});
</script>
