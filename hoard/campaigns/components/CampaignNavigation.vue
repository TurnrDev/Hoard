<template>
  <nav aria-label="Campaign navigation">
    <ul class="campaign-navigation list-unstyled mb-0">
      <li>
        <RouterLink
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
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
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
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
        <span
          class="campaign-navigation__item campaign-navigation__item--disabled campaign-navigation__item--coming-soon d-flex flex-wrap align-items-center column-gap-3 row-gap-1"
          aria-disabled="true"
        >
          <span
            class="mdi mdi-book-open-variant-outline"
            aria-hidden="true"
          />
          <span>Compendium</span>
          <span
            class="campaign-navigation__coming-soon badge rounded-pill border border-secondary text-body-secondary bg-transparent"
          >
            Coming soon
          </span>
        </span>
      </li>
      <li>
        <RouterLink
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
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
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
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
import type { ActingContext } from "@/campaigns/context";
import { contextPath } from "@/campaigns/context";

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
