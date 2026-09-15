<template>
  <nav
    v-if="contextId"
    aria-label="Campaign navigation"
  >
    <ul class="campaign-navigation">
      <li>
        <RouterLink
          :to="activeContext ? contextPath(activeContext) : `/c/${contextId}`"
        >
          <span
            class="mdi mdi-home-variant-outline"
            aria-hidden="true"
          />
          Home
        </RouterLink>
      </li>
      <li>
        <RouterLink :to="`/c/${contextId}/characters`">
          <span
            class="mdi mdi-account-group-outline"
            aria-hidden="true"
          />
          Characters
          <span
            v-if="hasIncompleteLevelUps"
            class="mdi mdi-alert-circle campaign-navigation__warning"
            aria-label="Level-up incomplete"
          />
        </RouterLink>
      </li>
      <li>
        <RouterLink :to="`/c/${contextId}/compendium`">
          <span
            class="mdi mdi-book-open-variant-outline"
            aria-hidden="true"
          />
          Compendium
        </RouterLink>
      </li>
      <li>
        <RouterLink :to="`/c/${contextId}/ledger`">
          <span
            class="mdi mdi-notebook-outline"
            aria-hidden="true"
          />
          Ledger
        </RouterLink>
      </li>
      <li v-if="activeContext?.kind === 'gm'">
        <RouterLink :to="`/c/${contextId}/manage`">
          <span
            class="mdi mdi-cog-outline"
            aria-hidden="true"
          />
          Manage
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import { contextPath, type ActingContext } from "@/campaigns/context";

export default defineComponent({
  props: {
    contextId: { type: Number, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: false },
    hasIncompleteLevelUps: { type: Boolean, default: false },
  },
  methods: { contextPath },
});
</script>
