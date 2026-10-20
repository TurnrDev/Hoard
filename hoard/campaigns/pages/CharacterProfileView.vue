<template>
  <section aria-labelledby="character-title">
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-4"
    >
      <div class="d-flex align-items-center gap-3">
        <CharacterAvatar
          v-if="character"
          :character="character"
          size="profile"
        />
        <div>
          <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
            DiceCloud character
          </p>
          <h1
            id="character-title"
            class="display-5 mb-1"
          >
            {{ character?.name ?? "Connect DiceCloud" }}
          </h1>
          <p
            v-if="character?.profile"
            class="text-body-secondary mb-0"
          >
            Level {{ profileLevel }}
            <span aria-hidden="true">·</span>
            {{ character.race || "No race" }}
            <span aria-hidden="true">·</span>
            {{ character.class || "No class" }}
          </p>
          <section
            v-if="experienceProgress"
            class="mt-2"
            aria-label="Party experience progress"
          >
            <div class="d-flex justify-content-between gap-3 small tabular-nums">
              <span>Party XP</span>
              <span>
                {{ formatXp(experienceProgress.current) }} /
                {{ formatXp(experienceProgress.next) }}
                XP
              </span>
            </div>
            <ProgressBar
              class="mt-1"
              :value="experienceProgress.percentage"
              :show-value="false"
              :aria-label="experienceProgress.ariaLabel"
            />
            <p class="small text-body-secondary tabular-nums mb-0">
              {{ formatXp(experienceProgress.remaining) }} XP to level up
            </p>
          </section>
        </div>
      </div>
      <Button
        :as="'router-link'"
        :to="`/c/${campaignId}/characters`"
        icon="mdi mdi-account-group-outline"
        label="Party roster"
        outlined
      />
    </header>

    <Message
      v-if="error"
      severity="error"
      closable
      @close="error = ''"
    >
      {{ error }}
    </Message>

    <section
      v-if="character && canManage"
      class="border rounded-3 p-3 p-md-4 mb-4"
      aria-labelledby="connection-title"
    >
      <h2
        id="connection-title"
        class="h3"
      >
        DiceCloud connection
      </h2>
      <p class="text-body-secondary">
        Hoard reads this public sheet live. Character details, hit points, currency, and
        resources cannot be edited here.
      </p>
      <form
        class="d-flex flex-column flex-md-row gap-2"
        @submit.prevent="connect"
      >
        <label
          class="visually-hidden"
          for="dicecloud-creature"
        >
          DiceCloud creature ID, public character URL, or public API URL
        </label>
        <InputText
          id="dicecloud-creature"
          v-model="creatureInput"
          class="flex-grow-1"
          placeholder="Creature ID or https://dicecloud.com/character/..."
        />
        <Button
          type="submit"
          :loading="busy"
          :label="character.is_connected ? 'Replace sheet' : 'Connect sheet'"
        />
        <Button
          v-if="character.is_connected"
          type="button"
          severity="danger"
          outlined
          :disabled="busy"
          label="Disconnect"
          @click="disconnect"
        />
      </form>
      <div
        v-if="
          character.is_connected ||
          (character.name && character.current_hp !== null && character.max_hp !== null)
        "
        class="form-check mt-3"
      >
        <input
          :id="`character-active-${character.id}`"
          v-model="isActive"
          class="form-check-input"
          type="checkbox"
          :disabled="busy"
          @change="saveActive"
        />
        <label
          class="form-check-label"
          :for="`character-active-${character.id}`"
        >
          Active in this campaign
        </label>
      </div>
    </section>

    <Message
      v-if="character && !character.is_connected && !canManage"
      severity="info"
    >
      This player has not connected a public DiceCloud sheet yet.
    </Message>
    <section
      v-if="character && !character.is_connected && character.max_hp !== null"
      class="border rounded-3 p-3 p-md-4 mb-4"
      aria-labelledby="fallback-details-title"
    >
      <h2
        id="fallback-details-title"
        class="h3"
      >
        Stored character details
      </h2>
      <p class="text-body-secondary">
        These retained values are used only until a DiceCloud sheet is connected.
      </p>
      <dl class="row mb-0">
        <dt class="col-sm-3">Current HP</dt>
        <dd class="col-sm-9 tabular-nums">{{ character.current_hp ?? "—" }}</dd>
        <dt class="col-sm-3">Maximum HP</dt>
        <dd class="col-sm-9 tabular-nums">{{ character.max_hp }}</dd>
      </dl>
    </section>
    <Message
      v-if="character?.profile?.unavailable"
      severity="warn"
    >
      {{ character.profile.error ?? "DiceCloud is unavailable right now." }}
    </Message>
    <Message
      v-if="character?.profile?.stale"
      severity="warn"
    >
      DiceCloud could not be reached. This is the last successful profile fetch from
      {{ formattedFetchTime }}.
    </Message>

    <template v-if="character?.profile && !character.profile.unavailable">
      <p
        v-if="character.profile.details.description"
        class="lead mb-4"
      >
        {{ character.profile.details.description }}
      </p>

      <dl class="row mb-4">
        <template
          v-for="detail in identityDetails"
          :key="detail.label"
        >
          <dt class="col-sm-2">{{ detail.label }}</dt>
          <dd class="col-sm-10">{{ detail.value }}</dd>
        </template>
      </dl>

      <section
        class="row g-3 mb-4"
        aria-label="Combat statistics"
      >
        <div
          v-for="stat in headlineStats"
          :key="stat.key"
          class="col-6 col-md-4 col-xl"
        >
          <section
            v-if="stat.key === 'currency'"
            class="border rounded-3 p-3 p-md-4 h-100"
          >
            <Transition
              name="money-card-flip"
              mode="out-in"
            >
              <div
                v-if="!moneyValueVisible"
                key="coin-pouch"
              >
                <header class="d-flex align-items-start justify-content-between gap-2">
                  <div class="text-uppercase fw-semibold small text-body-secondary">
                    Coin pouch
                  </div>
                  <Button
                    icon="mdi mdi-rotate-3d-variant"
                    text
                    rounded
                    size="small"
                    aria-label="Show coin value"
                    @click="toggleMoneyCard"
                  />
                </header>
                <div class="fs-5 tabular-nums mt-3">
                  {{ stat.summary }}
                </div>
              </div>

              <div
                v-else
                key="coin-value"
              >
                <header class="d-flex align-items-start justify-content-between gap-2">
                  <div class="text-uppercase fw-semibold small text-body-secondary">
                    Coin value
                  </div>
                  <Button
                    icon="mdi mdi-rotate-3d-variant"
                    text
                    rounded
                    size="small"
                    aria-label="Show coin pouch"
                    @click="toggleMoneyCard"
                  />
                </header>
                <div class="h4 mt-3 mb-0 tabular-nums">
                  {{ formatGoldValue(currencyGoldValue) }} ¤
                </div>
              </div>
            </Transition>
          </section>

          <DiceCloudStatCard
            v-else
            :label="stat.label"
            :summary="stat.summary"
          >
            <template v-if="stat.key === 'hitPoints'">
              <div>{{ stat.summary }}</div>
              <HealthBar
                v-if="hitPointPercentage !== null"
                class="mt-3"
                :percentage="hitPointPercentage"
                :label="`${stat.summary} hit points`"
              />
            </template>
            <template v-else>{{ stat.summary }}</template>
          </DiceCloudStatCard>
        </div>
      </section>

      <section
        class="mb-4"
        aria-labelledby="currency-title"
      >
        <h2
          id="currency-title"
          class="h3"
        >
          Currency
        </h2>
        <dl class="row border rounded-3 p-3 mx-0 mb-0">
          <template
            v-for="denomination in currencyRows"
            :key="denomination.label"
          >
            <dt class="col-6 col-md-2">{{ denomination.label }}</dt>
            <dd class="col-6 col-md-2 text-end tabular-nums">
              {{ denomination.value }}
            </dd>
          </template>
        </dl>
      </section>

      <section
        class="mb-4"
        aria-labelledby="abilities-title"
      >
        <header class="mb-3">
          <h2
            id="abilities-title"
            class="h3 mb-1"
          >
            Abilities and saving throws
          </h2>
          <p class="small text-body-secondary mb-0">
            Each card shows the DiceCloud score, derived modifier, and saving throw.
          </p>
        </header>
        <div class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3">
          <div
            v-for="ability in abilityCards"
            :key="ability.key"
            class="col"
          >
            <AbilityCard
              :label="ability.label"
              :abbreviation="ability.abbreviation"
              :score="ability.score"
              :save="ability.save"
            />
          </div>
        </div>
      </section>

      <section
        v-for="section in detailSections"
        :key="section.id"
        class="mb-4"
        :aria-labelledby="`${section.id}-title`"
      >
        <h2
          :id="`${section.id}-title`"
          class="h3"
        >
          {{ section.title }}
        </h2>
        <ul class="list-group">
          <li
            v-for="entry in section.entries"
            :key="`${entry.type}-${entry.name}`"
            class="list-group-item"
          >
            <div class="d-flex justify-content-between gap-3">
              <strong>{{ entry.name }}</strong>
              <span
                v-if="entry.value !== null"
                class="tabular-nums"
              >
                {{ entry.value }}
              </span>
            </div>
            <p
              v-if="entry.description"
              class="mb-0 mt-1 text-body-secondary"
            >
              {{ entry.description }}
            </p>
          </li>
        </ul>
      </section>

      <p class="small text-body-secondary mt-4 mb-0">
        Source fetched {{ formattedFetchTime }}.
        <a
          :href="character.profile.source_url"
          target="_blank"
          rel="noreferrer"
        >
          View public DiceCloud data
        </a>
        .
      </p>
    </template>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import { defineComponent } from "vue";
import AbilityCard from "@/campaigns/components/AbilityCard.vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import DiceCloudStatCard from "@/campaigns/components/DiceCloudStatCard.vue";
import HealthBar from "@/campaigns/components/HealthBar.vue";
import {
  readCoinDisplayMode,
  storeCoinDisplayMode,
} from "@/campaigns/coinDisplayPreference";
import { formatCoinPouch } from "@/campaigns/display";
import { formatGoldValue } from "@/campaigns/money";
import {
  getCampaign,
  linkDiceCloudCharacter,
  setCharacterActive,
  unlinkDiceCloudCharacter,
  type Campaign,
  type Character,
  type DiceCloudEntry,
} from "@/api";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: {
    AbilityCard,
    Button,
    CharacterAvatar,
    DiceCloudStatCard,
    HealthBar,
    InputText,
    Message,
    ProgressBar,
  },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      character: undefined as Character | undefined,
      creatureInput: "",
      isActive: false,
      moneyValueVisible: readCoinDisplayMode() === "value",
      busy: false,
      error: "",
    };
  },
  computed: {
    campaignId(): number {
      return Number(this.$route.params.id);
    },
    characterId(): number {
      return Number(this.$route.params.characterId);
    },
    canManage(): boolean {
      return Boolean(
        this.campaign?.is_game_master ||
        this.character?.context_id === this.campaign?.active_context_id,
      );
    },
    headlineStats(): Array<{
      key: string;
      label: string;
      summary: string;
    }> {
      const stats = this.character?.profile?.stats ?? {};
      const currency = this.character?.profile?.currency ?? {};

      return [
        {
          key: "currency",
          label: "Coin pouch",
          summary: formatCoinPouch(currency),
        },
        {
          key: "armor",
          label: "Armor class",
          summary: this.displayValue(stats.armor),
        },
        {
          key: "initiative",
          label: "Initiative bonus",
          summary: this.signedValue(stats.initiative),
        },
        {
          key: "hitPoints",
          label: "Hit points",
          summary: this.hitPointSummary,
        },
      ];
    },
    hitPointSummary(): string {
      const stats = this.character?.profile?.stats ?? {};
      const current = this.displayValue(stats.hitPoints);
      const maximum = this.displayValue(stats.maxHitPoints ?? stats.hitPoints);

      return `${current} / ${maximum}`;
    },
    profileLevel(): string {
      return this.displayValue(this.character?.profile?.stats.level);
    },
    experienceProgress(): {
      current: number;
      next: number;
      percentage: number;
      remaining: number;
      ariaLabel: string;
    } | null {
      const level = this.numberValue(this.character?.profile?.stats.level);

      if (!this.campaign || level === null) {
        return null;
      }

      const thresholds = [
        0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000,
        120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
      ];
      const normalizedLevel = Math.max(1, Math.floor(level));

      if (normalizedLevel >= thresholds.length) {
        return null;
      }

      const current = this.campaign.shared_experience;
      const lowerBound = thresholds[normalizedLevel - 1];
      const next = thresholds[normalizedLevel];
      const totalForLevel = next - lowerBound;
      const percentage = Math.min(
        100,
        Math.max(0, ((current - lowerBound) / totalForLevel) * 100),
      );
      const remaining = Math.max(0, next - current);

      return {
        current,
        next,
        percentage,
        remaining,
        ariaLabel: `${this.formatXp(current)} of ${this.formatXp(next)} party XP toward level ${normalizedLevel + 1}`,
      };
    },
    hitPointPercentage(): number | null {
      const stats = this.character?.profile?.stats ?? {};
      const current = this.numberValue(stats.hitPoints);
      const maximum = this.numberValue(stats.maxHitPoints ?? stats.hitPoints);

      if (current === null || maximum === null || maximum <= 0) {
        return null;
      }

      return Math.min(100, Math.max(0, (current / maximum) * 100));
    },
    currencyGoldValue(): string | number {
      return this.character?.profile?.currency.gold_value ?? 0;
    },
    abilityCards(): Array<{
      key: string;
      label: string;
      abbreviation: string;
      score: string | number | null;
      save: string | number | null;
    }> {
      const profile = this.character?.profile;
      const abilityDefinitions = [
        { key: "strength", label: "Strength", abbreviation: "STR" },
        { key: "dexterity", label: "Dexterity", abbreviation: "DEX" },
        { key: "constitution", label: "Constitution", abbreviation: "CON" },
        { key: "intelligence", label: "Intelligence", abbreviation: "INT" },
        { key: "wisdom", label: "Wisdom", abbreviation: "WIS" },
        { key: "charisma", label: "Charisma", abbreviation: "CHA" },
      ];

      return abilityDefinitions.map((ability) => ({
        ...ability,
        score: profile?.abilities[ability.key] ?? null,
        save: profile?.saves[ability.key] ?? null,
      }));
    },
    identityDetails(): Array<{ label: string; value: string }> {
      const details = this.character?.profile?.details ?? {};

      return [
        { label: "Race", value: details.race ?? "" },
        { label: "Class", value: details.class ?? "" },
        { label: "Alignment", value: details.alignment ?? "" },
        { label: "Gender", value: details.gender ?? "" },
      ].filter((detail) => Boolean(detail.value));
    },
    detailSections(): Array<{ id: string; title: string; entries: DiceCloudEntry[] }> {
      const profile = this.character?.profile;

      if (!profile) {
        return [];
      }

      return [
        {
          id: "saves",
          title: "Saving throws",
          entries: this.statEntries(profile.saves),
        },
        { id: "skills", title: "Skills", entries: this.statEntries(profile.skills) },
        { id: "resources", title: "Resources", entries: profile.resources },
        { id: "equipment", title: "Equipment", entries: profile.equipment },
        { id: "spells", title: "Spells", entries: profile.spells },
        { id: "features", title: "Features", entries: profile.features },
      ].filter((section) => section.entries.length > 0);
    },
    currencyRows(): Array<{ label: string; value: number | string }> {
      const currency = this.character?.profile?.currency ?? {};

      return [
        { label: "CP", value: currency.cp ?? 0 },
        { label: "SP", value: currency.sp ?? 0 },
        { label: "EP", value: currency.ep ?? 0 },
        { label: "GP", value: currency.gp ?? 0 },
        { label: "PP", value: currency.pp ?? 0 },
      ];
    },
    formattedFetchTime(): string {
      return this.character?.profile?.fetched_at
        ? new Date(this.character.profile.fetched_at).toLocaleString()
        : "";
    },
    campaignRefresh(): number {
      return campaignRefreshRevision.value;
    },
  },
  watch: {
    campaignRefresh(): void {
      void this.load();
    },
    characterId(): void {
      void this.load();
    },
  },
  mounted() {
    void this.load();
  },
  methods: {
    statEntries(values: Record<string, string | number | null>): DiceCloudEntry[] {
      return Object.entries(values).map(([name, value]) => ({
        name: this.formatLabel(name),
        description: "",
        type: "stat",
        value,
      }));
    },
    formatLabel(value: string): string {
      return value
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
    },
    displayValue(value: unknown): string {
      return value === undefined || value === null || value === ""
        ? "—"
        : String(value);
    },
    numberValue(value: unknown): number | null {
      if (typeof value === "number" && Number.isFinite(value)) {
        return value;
      }

      if (typeof value === "string" && value.trim() !== "") {
        const number = Number(value);
        return Number.isFinite(number) ? number : null;
      }

      return null;
    },
    signedValue(value: unknown): string {
      const number = this.numberValue(value);

      if (number === null) {
        return "—";
      }

      return number >= 0 ? `+${number}` : `−${Math.abs(number)}`;
    },
    formatXp(value: number): string {
      return value.toLocaleString();
    },
    formatGoldValue,
    toggleMoneyCard(): void {
      this.moneyValueVisible = !this.moneyValueVisible;
      storeCoinDisplayMode(this.moneyValueVisible ? "value" : "pouch");
    },
    async load(): Promise<void> {
      try {
        this.campaign = await getCampaign(this.campaignId);
        this.character = this.campaign.characters.find(
          (item) => item.id === this.characterId,
        );
        if (!this.character) {
          this.error = "Character not found.";
          return;
        }
        this.creatureInput = this.character.dicecloud_creature_id ?? "";
        this.isActive = this.character.is_active;
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load DiceCloud character.";
      }
    },
    async connect(): Promise<void> {
      if (!this.character || !this.creatureInput.trim()) {
        return;
      }
      this.busy = true;
      this.error = "";
      try {
        await linkDiceCloudCharacter(
          this.campaignId,
          this.character.id,
          this.creatureInput.trim(),
        );
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to connect DiceCloud.";
      } finally {
        this.busy = false;
      }
    },
    async disconnect(): Promise<void> {
      if (!this.character) {
        return;
      }
      this.busy = true;
      this.error = "";
      try {
        await unlinkDiceCloudCharacter(this.campaignId, this.character.id);
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to disconnect DiceCloud.";
      } finally {
        this.busy = false;
      }
    },
    async saveActive(): Promise<void> {
      if (!this.character) {
        return;
      }
      this.busy = true;
      this.error = "";
      try {
        await setCharacterActive(this.campaignId, this.character.id, this.isActive);
        await this.load();
      } catch (exception) {
        this.isActive = this.character.is_active;
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to update active status.";
      } finally {
        this.busy = false;
      }
    },
  },
});
</script>

<style scoped>
.money-card-flip-enter-active,
.money-card-flip-leave-active {
  transition:
    transform 140ms ease,
    opacity 140ms ease;
  transform-origin: center;
}

.money-card-flip-enter-from {
  opacity: 0;
  transform: rotateY(90deg);
}

.money-card-flip-leave-to {
  opacity: 0;
  transform: rotateY(-90deg);
}

@media (prefers-reduced-motion: reduce) {
  .money-card-flip-enter-active,
  .money-card-flip-leave-active {
    transition: none;
  }
}
</style>
