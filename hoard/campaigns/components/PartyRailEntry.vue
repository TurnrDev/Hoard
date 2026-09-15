<template>
  <li
    class="party-rail__entry align-items-center"
    :class="`party-rail__entry--${healthState}`"
    :aria-current="current ? 'step' : undefined"
  >
    <div class="position-relative">
      <OverlayBadge
        v-if="showAvatarBadge"
        :value="badgeValue"
        :severity="badgeSeverity"
        :pt="conditionBadgePassThrough"
        :aria-label="avatarBadgeLabel"
        :title="primaryConditionDescription"
      >
        <CharacterAvatar
          :class="[
            'party-rail__avatar',
            { 'border border-3 border-warning rounded-circle': current },
          ]"
          :name="name"
          :portrait-url="portraitUrl"
          size="rail"
        />
      </OverlayBadge>
      <CharacterAvatar
        v-else
        :class="[
          'party-rail__avatar',
          { 'border border-3 border-warning rounded-circle': current },
        ]"
        :name="name"
        :portrait-url="portraitUrl"
        size="rail"
      />
    </div>

    <div
      v-if="expanded"
      class="party-rail__character-details"
    >
      <span
        class="party-rail__entry-name d-block text-truncate"
        :class="{ 'inspired-name': inspired }"
      >
        {{ name }}
      </span>
      <span
        v-if="inspired"
        class="visually-hidden"
      >
        — Inspired
      </span>
      <span
        v-if="current"
        class="d-block small fw-semibold"
      >
        <span
          class="mdi mdi-sword-cross me-1"
          aria-hidden="true"
        />
        Current turn
      </span>
      <span
        v-if="showPresence"
        class="visually-hidden"
      >
        — {{ connected ? "Connected" : "Offline" }}
      </span>
      <ConditionIndicators
        v-if="additionalConditions.length"
        class="my-1"
        :combatant-name="name"
        :conditions="additionalConditions"
        expanded
      />
      <span
        v-if="showHpNumbers && currentHp !== null && maxHp !== null"
        class="d-block text-truncate small text-body-secondary tabular-nums"
      >
        {{ currentHp }} / {{ maxHp }} HP
      </span>
      <ProgressBar
        v-if="showHpBar && healthPercentage !== null"
        :value="healthPercentage"
        :show-value="false"
        :aria-label="healthLabel"
      />
      <slot />
    </div>

    <ProgressBar
      v-else-if="showHpBar && healthPercentage !== null"
      class="party-rail__compact-health"
      :value="healthPercentage"
      :show-value="false"
      :aria-label="healthLabel"
    />
  </li>
</template>

<script lang="ts">
import OverlayBadge from "primevue/overlaybadge";
import ProgressBar from "primevue/progressbar";
import { defineComponent, type PropType } from "vue";
import type { ActiveCondition } from "@/api";
import { conditionIcon } from "@/campaigns/conditionDisplay";
import CharacterAvatar from "./CharacterAvatar.vue";
import ConditionIndicators from "./ConditionIndicators.vue";

export default defineComponent({
  components: {
    CharacterAvatar,
    ConditionIndicators,
    OverlayBadge,
    ProgressBar,
  },
  props: {
    name: { type: String, required: true },
    portraitUrl: {
      type: String as PropType<string | null>,
      default: null,
    },
    conditions: {
      type: Array as PropType<ActiveCondition[]>,
      default: () => [],
    },
    connected: { type: Boolean, default: false },
    showPresence: { type: Boolean, default: false },
    expanded: { type: Boolean, default: false },
    currentHp: {
      type: Number as PropType<number | null>,
      default: null,
    },
    maxHp: {
      type: Number as PropType<number | null>,
      default: null,
    },
    healthPercentage: {
      type: Number as PropType<number | null>,
      default: null,
    },
    showHpBar: { type: Boolean, default: true },
    showHpNumbers: { type: Boolean, default: true },
    current: { type: Boolean, default: false },
    inspired: { type: Boolean, default: false },
  },
  computed: {
    primaryCondition(): ActiveCondition | undefined {
      return this.conditions[0];
    },
    additionalConditions(): ActiveCondition[] {
      return this.conditions.slice(1);
    },
    showAvatarBadge(): boolean {
      return Boolean(this.primaryCondition || this.showPresence);
    },
    badgeValue(): string {
      if (this.primaryCondition) {
        return " ";
      }

      return this.connected ? "✓" : "○";
    },
    badgeSeverity(): "warn" | "success" | "secondary" {
      if (this.primaryCondition) {
        return "warn";
      }

      return this.connected ? "success" : "secondary";
    },
    conditionBadgePassThrough(): object | undefined {
      if (!this.primaryCondition) {
        return undefined;
      }

      return {
        pcBadge: {
          root: {
            class: ["mdi", conditionIcon(this.primaryCondition.id)],
          },
        },
      };
    },
    primaryConditionDescription(): string | undefined {
      if (!this.primaryCondition) {
        return undefined;
      }

      const level =
        this.primaryCondition.exhaustion_level === null
          ? ""
          : ` level ${this.primaryCondition.exhaustion_level}`;
      const cause =
        this.primaryCondition.instances.length > 1
          ? `${this.primaryCondition.instances.length} active causes`
          : [this.primaryCondition.source, this.primaryCondition.duration]
              .filter(Boolean)
              .join(", ");

      return `${this.primaryCondition.label}${level}${cause ? `, ${cause}` : ""}`;
    },
    avatarBadgeLabel(): string {
      const presence = this.showPresence
        ? this.connected
          ? "Connected"
          : "Offline"
        : "";

      return [this.name, this.primaryConditionDescription, presence]
        .filter(Boolean)
        .join(" — ");
    },
    healthLabel(): string {
      if (this.showHpNumbers && this.currentHp !== null && this.maxHp !== null) {
        return `${this.name} health: ${this.currentHp} of ${this.maxHp}`;
      }

      return `${this.name} health bar`;
    },
    healthState(): "critical" | "wounded" | "healthy" | "unknown" {
      if (!this.showHpBar || this.healthPercentage === null) {
        return "unknown";
      }

      if (this.healthPercentage <= 25) {
        return "critical";
      }

      if (this.healthPercentage <= 60) {
        return "wounded";
      }

      return "healthy";
    },
  },
});
</script>
