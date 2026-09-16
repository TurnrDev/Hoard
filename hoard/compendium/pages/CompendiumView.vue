<template>
  <section aria-labelledby="compendium-title">
    <header class="mb-5">
      <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
        Campaign library
      </p>
      <h1
        id="compendium-title"
        class="display-5 mb-2"
      >
        Compendium
      </h1>
      <p class="mb-0 text-body-secondary">The Compendium is coming soon.</p>
    </header>

    <section
      class="border rounded-3 p-4"
      aria-labelledby="compendium-coming-soon-title"
    >
      <h2
        id="compendium-coming-soon-title"
        class="h3"
      >
        Reference library — coming soon
      </h2>
      <p class="text-body-secondary">
        Browse and campaign-specific reference management will be available in a future
        release.
      </p>
      <div
        class="d-grid gap-3"
        aria-label="Compendium preview"
      >
        <Skeleton height="2.5rem" />
        <Skeleton height="7rem" />
        <Skeleton height="7rem" />
      </div>
    </section>
  </section>
</template>

<script lang="ts">
import Skeleton from "primevue/skeleton";
import { defineComponent } from "vue";

export default defineComponent({
  components: { Skeleton },
});
</script>
