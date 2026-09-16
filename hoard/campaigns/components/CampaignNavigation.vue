<template>
  <nav
    class="campaign-navigation-container"
    :class="{ 'campaign-navigation-container--collapsed': !expanded }"
    aria-label="Campaign navigation"
  >
    <ul class="campaign-navigation list-unstyled mb-0">
      <li>
        <RouterLink
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
          :to="contextPath(activeContext)"
          :aria-label="expanded ? undefined : 'Play'"
          :title="expanded ? undefined : 'Play'"
        >
          <span
            class="mdi mdi-play-circle-outline"
            aria-hidden="true"
          />
          <span v-if="expanded">Play</span>
        </RouterLink>
      </li>
      <li>
        <RouterLink
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/characters`"
          :aria-label="expanded ? undefined : 'Characters'"
          :title="expanded ? undefined : 'Characters'"
        >
          <span
            class="mdi mdi-account-group-outline"
            aria-hidden="true"
          />
          <span v-if="expanded">Characters</span>
        </RouterLink>
      </li>
      <li>
        <span
          class="campaign-navigation__item campaign-navigation__item--disabled d-flex align-items-center gap-3"
          aria-disabled="true"
          aria-label="Compendium — coming soon"
          :title="expanded ? undefined : 'Compendium — coming soon'"
        >
          <span
            class="mdi mdi-book-open-variant-outline"
            aria-hidden="true"
          />
          <span v-if="expanded">Compendium</span>
          <span
            v-if="expanded"
            class="campaign-navigation__coming-soon badge rounded-pill border border-secondary text-body-secondary bg-transparent ms-auto"
          >
            Coming soon
          </span>
        </span>
      </li>
      <li>
        <RouterLink
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/ledger`"
          :aria-label="expanded ? undefined : 'Ledger'"
          :title="expanded ? undefined : 'Ledger'"
        >
          <span
            class="mdi mdi-notebook-outline"
            aria-hidden="true"
          />
          <span v-if="expanded">Ledger</span>
        </RouterLink>
      </li>
      <li v-if="activeContext.kind === 'gm'">
        <RouterLink
          class="campaign-navigation__item d-flex align-items-center gap-3 text-decoration-none"
          :to="`/c/${contextId}/manage`"
          :aria-label="expanded ? undefined : 'Manage'"
          :title="expanded ? undefined : 'Manage'"
        >
          <span
            class="mdi mdi-cog-outline"
            aria-hidden="true"
          />
          <span v-if="expanded">Manage</span>
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
    expanded: { type: Boolean, default: true },
  },
  methods: {
    contextPath,
  },
});
</script>
