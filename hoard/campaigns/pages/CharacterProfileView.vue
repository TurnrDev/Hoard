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
            {{ character.race || "No race" }}
            <span aria-hidden="true">·</span>
            {{ character.class || "No class" }}
            <template v-if="character.profile.details.alignment">
              <span aria-hidden="true">·</span>
              {{ character.profile.details.alignment }}
            </template>
            <template v-if="character.profile.details.gender">
              <span aria-hidden="true">·</span>
              {{ character.profile.details.gender }}
            </template>
          </p>
          <section
            v-if="experienceProgress"
            class="xp-progress mt-2"
            aria-label="Party experience progress"
          >
            <div class="d-flex justify-content-between gap-2 small tabular-nums">
              <span>Level {{ profileLevel }} party XP</span>
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
      <div class="d-flex align-items-center gap-2">
        <Button
          :as="'router-link'"
          :to="`/c/${campaignId}/characters`"
          icon="mdi mdi-account-group-outline"
          label="Party roster"
          outlined
        />
        <ActionMenu
          v-if="canManage"
          label="Character actions"
          :items="characterActionItems"
        />
      </div>
    </header>

    <Message
      v-if="error"
      severity="error"
      closable
      @close="error = ''"
    >
      {{ error }}
    </Message>

    <Dialog
      v-model:visible="connectionDialogVisible"
      modal
      :style="{ width: 'min(42rem, calc(100vw - 2rem))' }"
      :header="
        character?.is_connected ? 'Replace DiceCloud sheet' : 'Connect DiceCloud sheet'
      "
    >
      <p class="text-body-secondary">
        Hoard reads this public sheet live. Character details, hit points, currency, and
        resources cannot be edited here.
      </p>
      <form
        class="d-grid gap-3"
        @submit.prevent="connect"
      >
        <label
          class="form-label mb-0"
          for="dicecloud-creature"
        >
          DiceCloud character
        </label>
        <InputText
          id="dicecloud-creature"
          v-model="creatureInput"
          placeholder="Creature ID or https://dicecloud.com/character/..."
        />
        <footer class="d-flex justify-content-end gap-2">
          <Button
            type="button"
            label="Cancel"
            severity="secondary"
            outlined
            :disabled="busy"
            @click="connectionDialogVisible = false"
          />
          <Button
            type="submit"
            :loading="busy"
            :label="character?.is_connected ? 'Replace sheet' : 'Connect sheet'"
          />
        </footer>
      </form>
    </Dialog>

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

      <section
        class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xxl-6 g-3 mb-4"
        aria-label="Combat statistics"
      >
        <div
          v-for="stat in headlineStats"
          :key="stat.key"
          class="col"
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
                v-if="hitPointValues !== null"
                class="mt-3"
                :current="hitPointValues.current"
                :maximum="hitPointValues.maximum"
                :temporary="temporaryHitPoints"
              />
            </template>
            <template v-else-if="stat.key === 'initiative'">
              <span class="d-inline-flex align-items-center gap-1">
                <span
                  v-if="proficiencyIcon(stat.proficiency)"
                  :class="[
                    'mdi',
                    proficiencyIcon(stat.proficiency),
                    proficiencyClass(stat.proficiency),
                  ]"
                  role="img"
                  :aria-label="proficiencyLabel(stat.proficiency)"
                  :title="proficiencyLabel(stat.proficiency)"
                />
                <span :class="proficiencyClass(stat.proficiency)">
                  {{ stat.summary }}
                </span>
              </span>
            </template>
            <template v-else>{{ stat.summary }}</template>
          </DiceCloudStatCard>
        </div>
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
        v-if="skillColumns.length"
        class="mb-4"
        aria-labelledby="skills-title"
      >
        <header class="mb-3">
          <h2
            id="skills-title"
            class="h3 mb-1"
          >
            Skills
          </h2>
          <p class="small text-body-secondary mb-0">
            Bonuses are grouped by the ability used for each check.
          </p>
        </header>
        <div class="border rounded-3 p-2">
          <div class="row g-0">
            <div
              v-for="(column, columnIndex) in skillColumns"
              :key="columnIndex"
              class="col-12 col-md-6"
            >
              <section
                class="h-100"
                :class="columnIndex === 0 ? 'pe-md-2' : 'ps-md-2 border-md-start'"
              >
                <div
                  v-for="(group, groupIndex) in column"
                  :key="group.ability"
                  :class="{ 'mt-4': groupIndex > 0 }"
                >
                  <h3 class="h6 text-uppercase text-body-secondary mb-1">
                    {{ group.label }}
                  </h3>
                  <ul class="list-group list-group-flush">
                    <li
                      v-for="skill in group.skills"
                      :key="skill.key"
                      class="list-group-item bg-transparent px-0 py-2 d-flex align-items-center justify-content-between gap-3"
                    >
                      <span>{{ skill.name }}</span>
                      <span
                        class="d-inline-flex flex-shrink-0 align-items-center gap-1 tabular-nums"
                      >
                        <span
                          v-if="proficiencyIcon(skill.proficiency)"
                          :class="[
                            'mdi',
                            proficiencyIcon(skill.proficiency),
                            proficiencyClass(skill.proficiency),
                          ]"
                          role="img"
                          :aria-label="proficiencyLabel(skill.proficiency)"
                          :title="proficiencyLabel(skill.proficiency)"
                        />
                        <strong :class="proficiencyClass(skill.proficiency)">
                          {{ signedValue(skill.value) }}
                        </strong>
                      </span>
                    </li>
                  </ul>
                </div>
              </section>
            </div>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import type { MenuItem } from "primevue/menuitem";
import { defineComponent } from "vue";
import AbilityCard from "@/campaigns/components/AbilityCard.vue";
import ActionMenu from "@/campaigns/components/ActionMenu.vue";
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
  type DiceCloudSave,
  type DiceCloudSkill,
} from "@/api";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: {
    ActionMenu,
    AbilityCard,
    Button,
    CharacterAvatar,
    DiceCloudStatCard,
    Dialog,
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
      connectionDialogVisible: false,
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
    characterActionItems(): MenuItem[] {
      if (!this.character) {
        return [];
      }

      const diceCloudItems: MenuItem[] = [
        {
          label: this.character.is_connected ? "Replace sheet" : "Connect sheet",
          icon: "mdi mdi-link-variant",
          command: () => this.openConnectionDialog(),
        },
      ];

      if (this.character.is_connected) {
        diceCloudItems.push({
          label: "View on DiceCloud",
          icon: "mdi mdi-open-in-new",
          url: this.dicecloudCharacterUrl,
          target: "_blank",
        });
        diceCloudItems.push({
          label: this.isActive ? "Set inactive" : "Set active",
          icon: this.isActive
            ? "mdi mdi-account-off-outline"
            : "mdi mdi-account-check-outline",
          disabled: this.busy,
          command: () => void this.toggleActive(),
        });
        diceCloudItems.push({
          separator: true,
        });
        diceCloudItems.push({
          label: "Disconnect",
          icon: "mdi mdi-link-off",
          disabled: this.busy,
          command: () => void this.disconnect(),
        });
      }

      return [
        {
          label: "DiceCloud",
          icon: "mdi mdi-dice-d20-outline",
          items: diceCloudItems,
        },
      ];
    },
    dicecloudCharacterUrl(): string {
      const creatureId = this.character?.dicecloud_creature_id;

      return creatureId ? `https://dicecloud.com/character/${creatureId}` : "";
    },
    headlineStats(): Array<{
      key: string;
      label: string;
      summary: string;
      proficiency: number | null;
    }> {
      const stats = this.character?.profile?.stats ?? {};
      const currency = this.character?.profile?.currency ?? {};

      return [
        {
          key: "currency",
          label: "Coin pouch",
          summary: formatCoinPouch(currency),
          proficiency: null,
        },
        {
          key: "hitPoints",
          label: "Hit points",
          summary: this.hitPointSummary,
          proficiency: null,
        },
        {
          key: "armor",
          label: "Armor class",
          summary: this.displayValue(stats.armor),
          proficiency: null,
        },
        {
          key: "initiative",
          label: "Initiative bonus",
          summary: this.signedValue(stats.initiative),
          proficiency: this.numberValue(stats.initiativeProficiency),
        },
        {
          key: "proficiency",
          label: "Proficiency bonus",
          summary: this.signedValue(stats.proficiencyBonus),
          proficiency: null,
        },
        {
          key: "movement",
          label: "Movement speed",
          summary: this.displayValue(stats.movementSpeed ?? stats.speed),
          proficiency: null,
        },
      ];
    },
    hitPointSummary(): string {
      const stats = this.character?.profile?.stats ?? {};
      const current = this.displayValue(stats.hitPoints);
      const maximum = this.displayValue(stats.maxHitPoints ?? stats.hitPoints);
      const temporary = this.temporaryHitPoints;

      if (temporary > 0) {
        return `${current} / ${maximum} + ${temporary} temporary`;
      }

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
    hitPointValues(): { current: number; maximum: number } | null {
      const stats = this.character?.profile?.stats ?? {};
      const current = this.numberValue(stats.hitPoints);
      const maximum = this.numberValue(stats.maxHitPoints ?? stats.hitPoints);

      if (current === null || maximum === null || maximum <= 0) {
        return null;
      }

      return { current, maximum };
    },
    temporaryHitPoints(): number {
      return Math.max(0, this.numberValue(this.character?.profile?.stats.tempHP) ?? 0);
    },
    currencyGoldValue(): string | number {
      return this.character?.profile?.currency.gold_value ?? 0;
    },
    abilityCards(): Array<{
      key: string;
      label: string;
      abbreviation: string;
      score: string | number | null;
      save: DiceCloudSave | null;
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
    skillColumns(): Array<
      Array<{ ability: string; label: string; skills: DiceCloudSkill[] }>
    > {
      const skills = this.character?.profile?.skills ?? [];
      const abilityOrder = [
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
      ];
      const groupedSkills = new Map<string, DiceCloudSkill[]>();

      for (const skill of skills) {
        const ability = skill.ability || "other";
        const existingSkills = groupedSkills.get(ability) ?? [];

        existingSkills.push(skill);
        groupedSkills.set(ability, existingSkills);
      }

      const groups = Array.from(groupedSkills.entries())
        .map(([ability, grouped]) => ({
          ability,
          label: this.formatLabel(ability),
          skills: [...grouped].sort((left, right) => left.order - right.order),
          order: abilityOrder.indexOf(ability),
          firstSkillOrder: Math.min(...grouped.map((skill) => skill.order)),
        }))
        .sort((left, right) => {
          const leftOrder = left.order === -1 ? abilityOrder.length : left.order;
          const rightOrder = right.order === -1 ? abilityOrder.length : right.order;

          if (leftOrder !== rightOrder) {
            return leftOrder - rightOrder;
          }

          return left.firstSkillOrder - right.firstSkillOrder;
        })
        .map((group) => ({
          ability: group.ability,
          label: group.label,
          skills: group.skills,
        }));

      const splitIndex = Math.ceil(groups.length / 2);

      return [groups.slice(0, splitIndex), groups.slice(splitIndex)].filter(
        (column) => column.length,
      );
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
    formatLabel(value: string): string {
      return value
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
    },
    displayValue(value: unknown): string {
      return value === undefined || value === null || value === ""
        ? "Not available from DiceCloud"
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
    proficiencyIcon(value: number | null): string | null {
      if (value === null || value <= 0) {
        return null;
      }

      if (value < 1) {
        return "mdi-shield-half-full";
      }

      return "mdi-shield-check";
    },
    proficiencyLabel(value: number | null): string {
      if (value === null || value <= 0) {
        return "No proficiency";
      }

      if (value < 1) {
        return "Partial proficiency";
      }

      if (value > 1) {
        return "Expertise";
      }

      return "Proficient";
    },
    proficiencyClass(value: number | null): string | undefined {
      if (value === null || value <= 0) {
        return undefined;
      }

      if (value < 1) {
        return "proficiency-bonus proficiency-bonus--half";
      }

      if (value > 1) {
        return "proficiency-bonus proficiency-bonus--expertise";
      }

      return "proficiency-bonus";
    },
    formatXp(value: number): string {
      return value.toLocaleString();
    },
    formatGoldValue,
    toggleMoneyCard(): void {
      this.moneyValueVisible = !this.moneyValueVisible;
      storeCoinDisplayMode(this.moneyValueVisible ? "value" : "pouch");
    },
    openConnectionDialog(): void {
      this.connectionDialogVisible = true;
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
        this.connectionDialogVisible = false;
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
    async toggleActive(): Promise<void> {
      this.isActive = !this.isActive;
      await this.saveActive();
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

.xp-progress {
  width: min(22rem, 100%);
}

@media (prefers-reduced-motion: reduce) {
  .money-card-flip-enter-active,
  .money-card-flip-leave-active {
    transition: none;
  }
}
</style>
