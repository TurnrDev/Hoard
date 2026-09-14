<template>
  <fieldset class="party-rail__visibility-controls">
    <legend class="visually-hidden">{{ combatant.name }} visibility</legend>
    <div class="d-flex flex-column gap-2">
      <label class="d-flex align-items-center gap-2 small">
        <Checkbox
          :model-value="combatant.show_hp_bar"
          binary
          @update:model-value="updateHpBar"
        />
        <span>Show HP bar</span>
      </label>
      <label class="d-flex align-items-center gap-2 small">
        <Checkbox
          :model-value="combatant.show_hp_numbers"
          binary
          @update:model-value="updateHpNumbers"
        />
        <span>Show HP numbers</span>
      </label>
    </div>
  </fieldset>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Checkbox from "primevue/checkbox";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: { Checkbox },
  props: {
    combatant: { type: Object as PropType<PartyRailCombatant>, required: true },
  },
  emits: ["update-visibility"],
  methods: {
    updateHpBar(showHpBar: boolean): void {
      this.$emit("update-visibility", {
        combatantId: this.combatant.id,
        show_hp_bar: showHpBar,
      });
    },
    updateHpNumbers(showHpNumbers: boolean): void {
      this.$emit("update-visibility", {
        combatantId: this.combatant.id,
        show_hp_numbers: showHpNumbers,
      });
    },
  },
});
</script>
