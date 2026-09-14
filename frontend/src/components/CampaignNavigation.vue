<template>
  <nav aria-label="Campaign navigation">
    <ul class="campaign-navigation list-unstyled mb-0">
      <li>
        <RouterLink
          class="d-flex align-items-center gap-3 text-decoration-none"
          :to="contextPath(activeContext)"
        >
          <span
            class="mdi mdi-play-circle-outline"
            aria-hidden="true"
          />
          <span>Play</span>
        </RouterLink>
      </li>
      <li>
        <RouterLink
          class="d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/characters`"
        >
          <span
            class="mdi mdi-account-group-outline"
            aria-hidden="true"
          />
          <span>Characters</span>
        </RouterLink>
      </li>
      <li>
        <RouterLink
          class="d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/compendium`"
        >
          <span
            class="mdi mdi-book-open-variant-outline"
            aria-hidden="true"
          />
          <span>Compendium</span>
        </RouterLink>
      </li>
      <li>
        <RouterLink
          class="d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/ledger`"
        >
          <span
            class="mdi mdi-notebook-outline"
            aria-hidden="true"
          />
          <span>Ledger</span>
        </RouterLink>
      </li>
      <li v-if="activeContext.kind === 'gm'">
        <RouterLink
          class="d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/gm`"
        >
          <span
            class="mdi mdi-shield-crown-outline"
            aria-hidden="true"
          />
          <span>GM desk</span>
        </RouterLink>
      </li>
      <li v-if="activeContext.kind === 'gm'">
        <RouterLink
          class="d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/manage`"
        >
          <span
            class="mdi mdi-cog-outline"
            aria-hidden="true"
          />
          <span>Manage</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { ActingContext } from "../context";
import { contextPath } from "../context";

export default defineComponent({
  props: {
    contextId: { type: Number, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
  },
  methods: {
    contextPath,
  },
});
</script>
