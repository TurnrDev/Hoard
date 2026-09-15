<template>
  <ul
    class="d-flex flex-wrap align-items-center gap-1 list-unstyled mb-0"
    :aria-label="`${combatantName} conditions`"
  >
    <li
      v-for="condition in conditions"
      :key="condition.id"
      class="condition-indicator d-inline-flex align-items-center gap-1 border rounded px-1 small"
      tabindex="0"
      :aria-label="conditionDescription(condition)"
      :title="conditionDescription(condition)"
    >
      <span
        :class="['mdi', conditionIcon(condition.id)]"
        aria-hidden="true"
      />
      <span v-if="expanded">{{ conditionDescription(condition) }}</span>
    </li>
  </ul>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import { conditionIcon } from "@/campaigns/conditionDisplay";
import type { PartyRailCondition } from "./partyRailTypes";

export default defineComponent({
  props: {
    combatantName: { type: String, required: true },
    conditions: { type: Array as PropType<PartyRailCondition[]>, required: true },
    expanded: { type: Boolean, default: false },
  },
  methods: {
    conditionIcon,
    conditionDescription(condition: PartyRailCondition): string {
      const details = [condition.label];

      if (condition.exhaustion_level !== null) {
        details.push(`level ${condition.exhaustion_level}`);
      }

      if (condition.instances && condition.instances.length > 1) {
        details.push(`${condition.instances.length} active causes`);

        for (const instance of condition.instances) {
          const cause = [instance.source, instance.duration].filter(Boolean).join(", ");

          if (cause) {
            details.push(cause);
          }
        }
      } else {
        if (condition.duration) {
          details.push(condition.duration);
        }

        if (condition.source) {
          details.push(`source: ${condition.source}`);
        }
      }

      return details.join(", ");
    },
  },
});
</script>
