<template>
  <Transition
    name="ability-card-flip"
    mode="out-in"
  >
    <article
      v-if="!flipped"
      key="front"
      class="border rounded-3 p-3 h-100 text-center"
    >
      <header class="mb-3">
        <h3 class="h5 mb-0">{{ label }}</h3>
        <span class="small text-uppercase text-body-secondary">
          {{ abbreviation }} · {{ ability.score }}
        </span>
      </header>
      <div class="row row-cols-2 g-2 align-items-start tabular-nums">
        <div class="col">
          <span class="small text-body-secondary d-block mb-1">Modifier</span>
          <strong class="fs-3 lh-1">{{ signed(ability.modifier) }}</strong>
        </div>
        <div class="col">
          <span class="small text-body-secondary d-block mb-1">Save</span>
          <div class="d-flex align-items-center justify-content-center gap-1">
            <span
              v-if="save.proficiency === 'proficient'"
              class="mdi mdi-shield-check proficiency-bonus"
              role="img"
              aria-label="Proficient saving throw"
              title="Proficient saving throw"
            />
            <strong
              class="fs-3 lh-1"
              :class="
                save.proficiency === 'proficient'
                  ? 'proficiency-bonus proficiency-bonus--proficient'
                  : undefined
              "
            >
              {{ signed(save.bonus) }}
            </strong>
          </div>
        </div>
      </div>
      <Button
        class="mt-3"
        size="small"
        text
        icon="mdi mdi-rotate-3d-variant"
        label="Show calculation"
        :aria-label="`Show ${label} calculation`"
        @click="flipped = true"
      />
    </article>
    <article
      v-else
      key="back"
      class="border rounded-3 p-3 h-100"
    >
      <header class="d-flex align-items-start justify-content-between gap-3 mb-3">
        <div>
          <h3 class="h5 mb-0">{{ label }}</h3>
          <span class="small text-body-secondary">Calculation</span>
        </div>
        <Button
          size="small"
          text
          rounded
          icon="mdi mdi-rotate-3d-variant"
          :aria-label="`Show ${label} summary`"
          @click="flipped = false"
        />
      </header>
      <CalculationBreakdown
        :label="`${label} score`"
        :calculation="ability.formula"
        expanded
      />
      <dl class="small mb-3 mt-3 pt-3 border-top">
        <div class="d-flex justify-content-between gap-3">
          <dt class="text-body-secondary fw-normal">Modifier from score</dt>
          <dd class="mb-0 fw-semibold tabular-nums">
            {{ signed(ability.modifier) }}
          </dd>
        </div>
      </dl>
      <div class="pt-3 mt-3 border-top">
        <CalculationBreakdown
          :label="`${label} saving throw`"
          :calculation="save.formula"
          expanded
        />
      </div>
      <Button
        class="mt-3"
        size="small"
        text
        icon="mdi mdi-arrow-u-left-top"
        label="Back to summary"
        @click="flipped = false"
      />
    </article>
  </Transition>
</template>

<script lang="ts">
import Button from "primevue/button";
import { defineComponent, type PropType } from "vue";
import type { CharacterSheet } from "@/api";
import CalculationBreakdown from "./CalculationBreakdown.vue";

export default defineComponent({
  components: { Button, CalculationBreakdown },
  props: {
    label: { type: String, required: true },
    abbreviation: { type: String, required: true },
    ability: {
      type: Object as PropType<CharacterSheet["abilities"][string]>,
      required: true,
    },
    save: { type: Object as PropType<CharacterSheet["saves"][string]>, required: true },
  },
  data: () => ({ flipped: false }),
  methods: {
    signed(value: number): string {
      return value >= 0 ? `+${value}` : `−${Math.abs(value)}`;
    },
  },
});
</script>
