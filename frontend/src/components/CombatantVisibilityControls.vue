<template>
  <fieldset>
    <legend class="visually-hidden">{{ combatant.name }} visibility</legend>
    <div class="d-flex gap-1">
      <Button
        type="button"
        icon="mdi mdi-heart-pulse"
        size="small"
        rounded
        :outlined="!combatant.show_hp_bar"
        :severity="combatant.show_hp_bar ? 'success' : 'secondary'"
        :aria-pressed="combatant.show_hp_bar"
        :aria-label="hpBarLabel"
        :title="hpBarLabel"
        @click="updateHpBar"
      />
      <Button
        type="button"
        icon="mdi mdi-numeric"
        size="small"
        rounded
        :outlined="!combatant.show_hp_numbers"
        :severity="combatant.show_hp_numbers ? 'success' : 'secondary'"
        :aria-pressed="combatant.show_hp_numbers"
        :aria-label="hpNumbersLabel"
        :title="hpNumbersLabel"
        @click="updateHpNumbers"
      />
    </div>
  </fieldset>
</template>

<script lang="ts">
import Button from "primevue/button";
import { defineComponent, type PropType } from "vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: { Button },
  props: {
    combatant: { type: Object as PropType<PartyRailCombatant>, required: true },
  },
  emits: ["update-visibility"],
  computed: {
    hpBarLabel(): string {
      return `${this.combatant.show_hp_bar ? "Hide" : "Show"} ${this.combatant.name} HP bar to players`;
    },
    hpNumbersLabel(): string {
      return `${this.combatant.show_hp_numbers ? "Hide" : "Show"} ${this.combatant.name} HP numbers to players`;
    },
  },
  methods: {
    updateHpBar(): void {
      this.$emit("update-visibility", {
        combatantId: this.combatant.id,
        show_hp_bar: !this.combatant.show_hp_bar,
      });
    },
    updateHpNumbers(): void {
      this.$emit("update-visibility", {
        combatantId: this.combatant.id,
        show_hp_numbers: !this.combatant.show_hp_numbers,
      });
    },
  },
});
</script>
