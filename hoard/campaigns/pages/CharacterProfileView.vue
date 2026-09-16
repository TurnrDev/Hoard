<template>
  <section
    v-if="character && campaign"
    aria-labelledby="character-title"
  >
    <header
      class="position-relative mb-4"
      :class="{ 'pe-5': canEdit }"
    >
      <div class="d-flex align-items-center gap-3">
        <CharacterAvatar
          :character="character"
          size="profile"
        />
        <div>
          <p class="text-uppercase fw-semibold small text-body-secondary mb-1">
            {{ character.kind === "pc" ? "Player character" : "Non-player character" }}
          </p>
          <h1
            id="character-title"
            class="display-5 mb-1"
          >
            {{ character.name }}
          </h1>
          <p class="mb-0 text-body-secondary">
            {{ character.race || "Race not set" }} ·
            {{ character.class || "Class not set" }}
          </p>
          <p class="mb-0 text-body-secondary tabular-nums">
            Level {{ experienceProgress.level }} ·
            {{ formatXp(experienceProgress.current) }} ·
            <template v-if="experienceProgress.remaining !== null">
              <span :class="{ 'level-up-near': experienceProgress.isNearLevelUp }">
                {{ formatXp(experienceProgress.remaining) }}
              </span>
              to level up
            </template>
            <span v-else>Maximum level</span>
          </p>
        </div>
      </div>
      <div
        v-if="canEdit"
        class="position-absolute top-0 end-0"
      >
        <ActionMenu
          label="Character actions"
          :items="characterActionItems"
        />
        <input
          ref="portraitInput"
          class="d-none"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          @change="uploadPortrait"
        />
      </div>
    </header>

    <Message
      v-if="error"
      severity="error"
      closable
      class="mb-4"
      @close="error = ''"
    >
      {{ error }}
    </Message>

    <section
      class="coin-pouch-card border rounded-3 p-3 p-md-4 mb-5"
      aria-label="Personal money"
    >
      <div
        v-if="canAct"
        class="d-none d-md-block float-end"
      >
        <ActionMenu
          label="Coin actions"
          :items="coinActionItems"
        />
      </div>
      <div class="d-md-none">
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
              <div class="d-flex align-items-center gap-1">
                <Button
                  icon="mdi mdi-rotate-3d-variant"
                  text
                  rounded
                  size="small"
                  aria-label="Show coin value"
                  @click="toggleMoneyCard"
                />
                <ActionMenu
                  v-if="canAct"
                  label="Coin actions"
                  :items="coinActionItems"
                />
              </div>
            </header>
            <div class="fs-5 tabular-nums mt-3">
              {{ formatCoinPouch(character.money) }}
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
              <div class="d-flex align-items-center gap-1">
                <Button
                  icon="mdi mdi-rotate-3d-variant"
                  text
                  rounded
                  size="small"
                  aria-label="Show coin pouch"
                  @click="toggleMoneyCard"
                />
                <ActionMenu
                  v-if="canAct"
                  label="Coin actions"
                  :items="coinActionItems"
                />
              </div>
            </header>
            <div class="h3 mt-3 mb-0">
              {{ formatGoldValue(character.money.gold_value) }} ¤
            </div>
          </div>
        </Transition>
      </div>

      <div class="row g-0 h-100 d-none d-md-flex">
        <div class="col-12 col-md-7">
          <div>
            <div class="text-uppercase fw-semibold small text-body-secondary">
              Coin pouch
            </div>
            <div class="fs-5 tabular-nums mt-3">
              {{ formatCoinPouch(character.money) }}
            </div>
          </div>
        </div>
        <div class="col-12 col-md-5 border-top coin-value-column p-3">
          <div>
            <div class="text-uppercase fw-semibold small text-body-secondary">
              Coin value
            </div>
            <div class="h3 mt-3">
              {{ formatGoldValue(character.money.gold_value) }} ¤
            </div>
          </div>
        </div>
      </div>
    </section>

    <Dialog
      v-model:visible="moneyDialog"
      modal
      :style="{ width: 'min(39rem, calc(100vw - 2rem))' }"
      @update:visible="closeMoneyDialogWhenClosed"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="money-action-heading"
      >
        <h2
          id="money-action-heading"
          class="h3 mb-0"
        >
          {{ moneyActionTitle }}
        </h2>
        <div class="d-grid gap-3">
          <template v-if="moneyAction === 'spend'">
            <CoinAmountPicker v-model="moneyAmounts" />
            <div class="small text-body-secondary mb-3">
              Coins will be transferred to the campaign system.
            </div>
          </template>
          <template v-else-if="moneyAction === 'transfer'">
            <label class="form-label mb-0">
              Transfer to
              <Select
                v-model="moneyDestination"
                :options="destinationOptions"
                option-label="title"
                option-value="value"
                class="w-100"
                fluid
              />
            </label>
            <CoinAmountPicker v-model="moneyAmounts" />
          </template>
          <template v-else>
            <div class="row g-3">
              <div class="col-md-6 d-grid gap-3">
                <label class="form-label mb-0">
                  Source denomination
                  <Select
                    v-model="denomination"
                    :options="denominations"
                    option-label="title"
                    option-value="value"
                    fluid
                  />
                </label>
                <label class="form-label mb-0">
                  Source coins
                  <InputNumber
                    v-model.number="amount"
                    :min="1"
                    :step="1"
                    show-buttons
                    fluid
                  />
                </label>
              </div>
              <div class="col-md-6 d-grid gap-3">
                <label class="form-label mb-0">
                  Target denomination
                  <Select
                    v-model="exchangeTargetDenomination"
                    :options="denominations"
                    option-label="title"
                    option-value="value"
                    fluid
                  />
                </label>
                <label class="form-label mb-0">
                  Target coins
                  <InputText
                    :model-value="exchangeAmount === null ? '' : String(exchangeAmount)"
                    readonly
                    fluid
                  />
                </label>
              </div>
            </div>
            <Message
              v-if="!exchangeAmount"
              severity="warn"
            >
              Choose different denominations and an exactly convertible quantity.
            </Message>
          </template>
          <label
            v-if="moneyAction !== 'exchange'"
            class="form-label mb-0"
          >
            Note (optional)
            <Textarea
              v-model="moneyDescription"
              rows="2"
              fluid
            />
          </label>
        </div>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="closeMoneyDialog"
          />
          <Button
            :label="moneyActionTitle"
            :disabled="moneyActionDisabled"
            :loading="moneyBusy"
            @click="submitMoneyAction"
          />
        </footer>
      </section>
    </Dialog>

    <Message
      severity="info"
      :closable="false"
      class="mb-3"
    >
      The detailed character sheet—including health, abilities, equipment, spells,
      rests, combat, and level-up—is coming soon.
    </Message>

    <BlockUI
      :blocked="true"
      aria-label="Character sheet preview"
    >
      <section aria-label="Detailed character sheet preview">
        <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xl-5 g-3">
          <div
            v-for="stat in deferredSummaryStats"
            :key="stat"
            class="col"
          >
            <article class="border rounded-3 p-3 p-md-4 h-100">
              <div class="text-uppercase fw-semibold small text-body-secondary">
                {{ stat }}
              </div>
              <Skeleton
                width="4.5rem"
                height="2rem"
                class="mt-3"
              />
            </article>
          </div>
        </div>

        <section class="mt-4 mb-4">
          <header class="mb-3">Resources</header>
          <div class="table-responsive">
            <table class="table table-striped">
              <caption class="visually-hidden">Spell slot availability preview</caption>
              <thead>
                <tr>
                  <th scope="col">Slot</th>
                  <th
                    scope="col"
                    class="text-end"
                  >
                    Current
                  </th>
                  <th
                    scope="col"
                    class="text-end"
                  >
                    Maximum
                  </th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in 3"
                  :key="row"
                >
                  <th scope="row"><Skeleton width="5rem" /></th>
                  <td>
                    <Skeleton
                      class="ms-auto"
                      width="2rem"
                    />
                  </td>
                  <td>
                    <Skeleton
                      class="ms-auto"
                      width="2rem"
                    />
                  </td>
                  <td><Skeleton width="8rem" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="abilities-heading">
          <header class="mb-3">
            <h2
              id="abilities-heading"
              class="h4 mb-1"
            >
              Abilities and saving throws
            </h2>
            <p class="small text-body-secondary mb-0">
              Flip a card to see how its totals are calculated.
            </p>
          </header>
          <div class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3">
            <div
              v-for="ability in deferredAbilities"
              :key="ability"
              class="col"
            >
              <article class="border rounded-3 p-3 h-100 text-center">
                <header class="mb-3">
                  <h3 class="h5 mb-0">{{ ability }}</h3>
                  <Skeleton
                    width="4rem"
                    class="mx-auto mt-1"
                  />
                </header>
                <div class="row row-cols-2 g-2 align-items-start">
                  <div class="col d-flex flex-column align-items-center">
                    <span class="small text-body-secondary d-block mb-1">Modifier</span>
                    <Skeleton
                      width="3rem"
                      height="2rem"
                    />
                  </div>
                  <div class="col d-flex flex-column align-items-center">
                    <span class="small text-body-secondary d-block mb-1">Save</span>
                    <Skeleton
                      width="3rem"
                      height="2rem"
                    />
                  </div>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section
          class="mt-4"
          aria-labelledby="skills-heading"
        >
          <header class="mb-3">
            <h2
              id="skills-heading"
              class="h4 mb-1"
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
                v-for="column in 2"
                :key="column"
                class="col-6"
              >
                <section
                  class="h-100"
                  :class="column === 1 ? 'pe-2' : 'ps-2 border-start'"
                >
                  <div
                    v-for="group in 3"
                    :key="group"
                    :class="{ 'mt-4': group > 1 }"
                  >
                    <Skeleton
                      width="5rem"
                      class="mb-2"
                    />
                    <Skeleton
                      v-for="row in 3"
                      :key="row"
                      :width="`${92 - row * 8}%`"
                      height="1.25rem"
                      class="mb-2"
                    />
                  </div>
                </section>
              </div>
            </div>
          </div>
        </section>

        <section class="mt-4 border rounded-3 p-3 p-md-4">
          <header class="d-flex align-items-center gap-2 flex-wrap mb-3">
            Inventory
          </header>
          <div class="table-responsive">
            <table class="table table-striped mb-0">
              <caption class="visually-hidden">Character inventory preview</caption>
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th
                    scope="col"
                    class="text-end"
                  >
                    Quantity
                  </th>
                  <th
                    scope="col"
                    class="text-end"
                  >
                    Weight
                  </th>
                  <th
                    scope="col"
                    class="text-end"
                  >
                    Value
                  </th>
                  <th
                    scope="col"
                    class="text-end"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row"><Skeleton width="8rem" /></th>
                  <td>
                    <Skeleton
                      class="ms-auto"
                      width="2rem"
                    />
                  </td>
                  <td>
                    <Skeleton
                      class="ms-auto"
                      width="4rem"
                    />
                  </td>
                  <td>
                    <Skeleton
                      class="ms-auto"
                      width="4rem"
                    />
                  </td>
                  <td>
                    <Skeleton
                      class="ms-auto"
                      width="2rem"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section
          class="mt-4 border rounded-3 p-3 p-md-4"
          aria-labelledby="equipment-heading"
        >
          <header class="mb-3">
            <h2
              id="equipment-heading"
              class="h4 mb-0"
            >
              Equipment and effects
            </h2>
          </header>
          <div class="row g-4">
            <section class="col-12 col-lg-6">
              <h3 class="h6 mb-2">Equipment</h3>
              <Skeleton
                width="85%"
                height="3rem"
              />
            </section>
            <section class="col-12 col-lg-6">
              <h3 class="h6 mb-2">Active effects</h3>
              <Skeleton
                width="85%"
                height="3rem"
              />
            </section>
          </div>
        </section>

        <section
          class="mt-4"
          aria-labelledby="character-reference-heading"
        >
          <h2
            id="character-reference-heading"
            class="h4 mb-3"
          >
            Character details
          </h2>
          <div class="d-grid gap-2">
            <SheetDisclosure
              v-for="detail in deferredDetails"
              :key="detail"
              :title="detail"
            >
              <Skeleton
                width="75%"
                height="1.25rem"
              />
            </SheetDisclosure>
          </div>
        </section>
      </section>
    </BlockUI>

    <section
      class="mt-4 border rounded-3 p-3 p-md-4"
      aria-labelledby="activity-heading"
    >
      <header class="d-flex align-items-center gap-2 flex-wrap mb-3">
        <h2
          id="activity-heading"
          class="h4 mb-0"
        >
          Recent activity
        </h2>
        <span class="flex-grow-1" />
        <Button
          :as="'router-link'"
          :to="`/c/${campaignId}/ledger`"
          size="small"
          text
          label="View full ledger"
        />
      </header>
      <div
        v-if="activity.length"
        class="table-responsive"
        tabindex="0"
        aria-label="Recent character activity table"
      >
        <table class="table table-striped mb-0">
          <caption class="visually-hidden">
            Recent activity for {{ character.name }}
          </caption>
          <thead>
            <tr>
              <th scope="col">When</th>
              <th
                scope="col"
                class="text-end"
              >
                Change
              </th>
              <th scope="col">Details</th>
              <th scope="col">By</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="transaction in activity"
              :key="`${transaction.ledger}-${transaction.id}`"
            >
              <td class="text-nowrap">
                <RelativeTime :value="transaction.occurred_at" />
              </td>
              <td class="text-end text-nowrap tabular-nums fw-semibold">
                {{ activityAmount(transaction) }}
              </td>
              <td>{{ activityDescription(transaction) }}</td>
              <td>{{ transaction.actor || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p
        v-else
        class="text-body-secondary mb-0"
      >
        No recent activity.
      </p>
    </section>

    <Dialog
      v-model:visible="editorOpen"
      modal
      header="Edit character profile"
      :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
    >
      <form
        class="d-grid gap-3"
        @submit.prevent="saveProfile"
      >
        <label class="d-grid gap-2">
          <span class="fw-semibold">Name</span>
          <InputText
            v-model="draft.name"
            required
            maxlength="200"
            fluid
          />
        </label>
        <label class="d-grid gap-2">
          <span class="fw-semibold">Race</span>
          <InputText
            v-model="draft.race"
            maxlength="100"
            fluid
          />
        </label>
        <label class="d-grid gap-2">
          <span class="fw-semibold">Class</span>
          <InputText
            v-model="draft.characterClass"
            maxlength="100"
            fluid
          />
        </label>
        <footer class="d-flex justify-content-end gap-2 mt-2">
          <Button
            type="button"
            label="Cancel"
            severity="secondary"
            outlined
            @click="editorOpen = false"
          />
          <Button
            type="submit"
            label="Save profile"
            :loading="busy"
          />
        </footer>
      </form>
    </Dialog>
  </section>

  <ProgressBar
    v-else-if="!error"
    indeterminate
    aria-label="Loading character profile"
  />
</template>

<script lang="ts">
import BlockUI from "primevue/blockui";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import type { MenuItem } from "primevue/menuitem";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";
import Textarea from "primevue/textarea";
import { defineComponent } from "vue";
import {
  archiveCharacter,
  createMoneyExchange,
  createMoneyTransfer,
  getCampaign,
  getTransactions,
  removeCharacterPortrait,
  updateCharacter,
  uploadCharacterPortrait,
  type Campaign,
  type Character,
  type LedgerTransaction,
} from "@/api";
import { exchangedCoinAmount } from "@/campaigns/coinExchange";
import ActionMenu from "@/campaigns/components/ActionMenu.vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import CoinAmountPicker from "@/campaigns/components/CoinAmountPicker.vue";
import SheetDisclosure from "@/campaigns/components/SheetDisclosure.vue";
import {
  readCoinDisplayMode,
  storeCoinDisplayMode,
} from "@/campaigns/coinDisplayPreference";
import { displayCoin, displayIdentifier, formatCoinPouch } from "@/campaigns/display";
import { nearLevelUpXpThreshold } from "@/campaigns/experience";
import { formatGoldValue } from "@/campaigns/money";
import RelativeTime from "@/components/RelativeTime.vue";
import { campaignRefreshRevision } from "@/realtime";

const xpThresholds = [
  0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000,
  140000, 165000, 195000, 225000, 265000, 305000, 355000,
];

const denominationOptions = ["cp", "sp", "ep", "gp", "pp"].map((value) => ({
  title: displayCoin(value),
  value,
}));

export default defineComponent({
  components: {
    ActionMenu,
    BlockUI,
    Button,
    CharacterAvatar,
    CoinAmountPicker,
    Dialog,
    InputNumber,
    InputText,
    Message,
    ProgressBar,
    RelativeTime,
    Select,
    SheetDisclosure,
    Skeleton,
    Textarea,
  },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      character: undefined as Character | undefined,
      editorOpen: false,
      moneyValueVisible: readCoinDisplayMode() === "value",
      moneyAction: "spend" as "spend" | "transfer" | "exchange",
      moneyDialog: false,
      moneyBusy: false,
      denomination: "gp",
      amount: 1,
      moneyAmounts: { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 } as Record<string, number>,
      moneyDestination: undefined as number | undefined,
      exchangeTargetDenomination: "sp",
      moneyDescription: "",
      denominations: denominationOptions,
      activity: [] as LedgerTransaction[],
      busy: false,
      error: "",
      draft: {
        name: "",
        race: "",
        characterClass: "",
      },
      deferredSummaryStats: [
        "HP",
        "Armor class",
        "Initiative bonus",
        "Proficiency bonus",
        "Movement speed",
      ],
      deferredAbilities: [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
      ],
      deferredDetails: [
        "Background and personality",
        "Languages and proficiencies",
        "Notes",
        "Features and feats",
        "Spells",
        "Companions",
      ],
    };
  },
  computed: {
    campaignId(): number {
      return Number(this.$route.params.id);
    },
    characterId(): number {
      return Number(this.$route.params.characterId);
    },
    canEdit(): boolean {
      return Boolean(
        this.character &&
        (this.campaign?.is_game_master ||
          this.character.context_id === this.campaignId),
      );
    },
    canAct(): boolean {
      return Boolean(
        this.character &&
        this.character.context_id === this.campaignId &&
        this.character.is_active,
      );
    },
    characterActionItems(): MenuItem[] {
      const items: MenuItem[] = [
        {
          label: "Edit profile",
          icon: "mdi mdi-pencil-outline",
          command: () => this.openEditor(),
        },
        {
          label: "Change portrait",
          icon: "mdi mdi-image-edit-outline",
          command: () => this.choosePortrait(),
        },
      ];

      if (this.character?.portrait_url) {
        items.push({
          label: "Remove portrait",
          icon: "mdi mdi-image-remove-outline",
          command: () => void this.removePortrait(),
        });
      }

      items.push(
        { separator: true },
        {
          label: "Archive character",
          icon: "mdi mdi-archive-outline",
          class: "text-danger",
          command: () => void this.archive(),
        },
      );

      return items;
    },
    coinActionItems(): MenuItem[] {
      return [
        {
          label: "Spend coins",
          icon: "mdi mdi-cash-minus",
          command: () => this.openMoneyDialog("spend"),
        },
        {
          label: "Transfer coins",
          icon: "mdi mdi-swap-horizontal",
          command: () => this.openMoneyDialog("transfer"),
        },
        {
          label: "Exchange coins",
          icon: "mdi mdi-currency-exchange",
          command: () => this.openMoneyDialog("exchange"),
        },
      ];
    },
    destinationOptions() {
      return (this.campaign?.characters ?? [])
        .filter(
          (candidate) => candidate.id !== this.character?.id && candidate.is_active,
        )
        .map((candidate) => ({ title: candidate.name, value: candidate.id }));
    },
    exchangeAmount(): number | null {
      return exchangedCoinAmount(
        this.denomination,
        this.exchangeTargetDenomination,
        this.amount,
      );
    },
    submittedMoneyAmounts(): Record<string, number> {
      return Object.fromEntries(
        Object.entries(this.moneyAmounts).filter(
          ([, value]) => Number.isInteger(value) && value > 0,
        ),
      );
    },
    hasInvalidMoneyAmounts(): boolean {
      return Object.values(this.moneyAmounts).some(
        (value) => !Number.isInteger(value) || value < 0,
      );
    },
    hasMoneyAmounts(): boolean {
      return Object.keys(this.submittedMoneyAmounts).length > 0;
    },
    moneyActionTitle(): string {
      if (this.moneyAction === "spend") {
        return "Spend coins";
      }

      if (this.moneyAction === "transfer") {
        return "Transfer coins";
      }

      return "Exchange coins";
    },
    moneyActionDisabled(): boolean {
      if (this.moneyAction === "transfer") {
        return (
          !this.moneyDestination || !this.hasMoneyAmounts || this.hasInvalidMoneyAmounts
        );
      }

      if (this.moneyAction === "exchange") {
        return !this.exchangeAmount;
      }

      return !this.hasMoneyAmounts || this.hasInvalidMoneyAmounts;
    },
    experienceProgress() {
      const level = this.campaign?.level ?? 1;
      const current = this.campaign?.shared_experience ?? 0;
      const minimum = xpThresholds[level - 1] ?? 0;
      const maximum = xpThresholds[level];
      const progress = maximum
        ? Math.min(100, Math.max(0, ((current - minimum) / (maximum - minimum)) * 100))
        : 100;
      const remaining = maximum === undefined ? null : Math.max(0, maximum - current);
      const levelXpRequirement = maximum === undefined ? null : maximum - minimum;
      const nearLevelUpThreshold =
        levelXpRequirement === null ? null : nearLevelUpXpThreshold(levelXpRequirement);
      const isNearLevelUp =
        remaining !== null &&
        nearLevelUpThreshold !== null &&
        remaining <= nearLevelUpThreshold;

      return {
        current,
        isNearLevelUp,
        level,
        maximum,
        minimum,
        progress,
        remaining,
      };
    },
    campaignRefresh(): number {
      return campaignRefreshRevision.value;
    },
  },
  watch: {
    campaignRefresh(): void {
      void this.load();
    },
  },
  mounted() {
    void this.load();
  },
  methods: {
    formatCoinPouch,
    formatGoldValue,
    formatXp(value: number): string {
      return `${value.toLocaleString()} XP`;
    },
    activityAmount(transaction: LedgerTransaction): string {
      return transaction.entries
        .filter((entry) => entry.account_name === this.character?.name)
        .map(
          (entry) =>
            `${entry.amount > 0 ? "+" : ""}${entry.amount} ${
              entry.denomination ? displayCoin(entry.denomination) : "XP"
            }`,
        )
        .join(" · ");
    },
    activityDescription(transaction: LedgerTransaction): string {
      return (
        transaction.description ||
        transaction.ledger_label ||
        displayIdentifier(transaction.ledger)
      );
    },
    toggleMoneyCard(): void {
      this.moneyValueVisible = !this.moneyValueVisible;
      storeCoinDisplayMode(this.moneyValueVisible ? "value" : "pouch");
    },
    closeMoneyDialog(): void {
      this.moneyDialog = false;
      this.moneyAction = "spend";
      this.denomination = "gp";
      this.amount = 1;
      this.exchangeTargetDenomination = "sp";
      this.moneyAmounts = { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 };
      this.moneyDestination = undefined;
      this.moneyDescription = "";
    },
    closeMoneyDialogWhenClosed(open: boolean): void {
      if (!open) {
        this.closeMoneyDialog();
      }
    },
    openMoneyDialog(action: "spend" | "transfer" | "exchange"): void {
      this.closeMoneyDialog();
      this.moneyAction = action;
      this.moneyDialog = true;
    },
    async submitMoneyAction(): Promise<void> {
      if (!this.character) {
        return;
      }

      this.moneyBusy = true;

      try {
        if (this.moneyAction === "exchange") {
          if (!this.exchangeAmount) {
            return;
          }

          await createMoneyExchange(this.campaignId, {
            character_id: this.character.id,
            given: { [this.denomination]: this.amount },
            received: { [this.exchangeTargetDenomination]: this.exchangeAmount },
            description: this.moneyDescription,
          });
        } else {
          if (!this.hasMoneyAmounts || this.hasInvalidMoneyAmounts) {
            return;
          }

          await createMoneyTransfer(this.campaignId, {
            from_character_id: this.character.id,
            to_character_id:
              this.moneyAction === "transfer" ? (this.moneyDestination ?? null) : null,
            amounts: this.submittedMoneyAmounts,
            description: this.moneyDescription,
          });
        }

        this.$toast.add({
          severity: "success",
          summary: "Saved to the ledger.",
          life: 4_000,
        });
        this.closeMoneyDialog();
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update money.";
      } finally {
        this.moneyBusy = false;
      }
    },
    async load(): Promise<void> {
      try {
        const [campaign, recentActivity] = await Promise.all([
          getCampaign(this.campaignId),
          getTransactions(this.campaignId, "all", 1, this.characterId),
        ]);
        const character = campaign.characters.find(
          (candidate) => candidate.id === this.characterId,
        );

        if (!character) {
          this.error = "Character not found.";
          return;
        }

        this.campaign = campaign;
        this.character = character;
        this.activity = recentActivity.results.slice(0, 5);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load the character profile.";
      }
    },
    openEditor(): void {
      if (!this.character) {
        return;
      }

      this.draft = {
        name: this.character.name,
        race: this.character.race,
        characterClass: this.character.class,
      };
      this.editorOpen = true;
    },
    async saveProfile(): Promise<void> {
      if (!this.character || !this.draft.name.trim()) {
        return;
      }

      this.busy = true;

      try {
        await updateCharacter(this.campaignId, this.character.id, {
          name: this.draft.name.trim(),
          race: this.draft.race.trim(),
          class: this.draft.characterClass.trim(),
        });
        this.editorOpen = false;
        this.$toast.add({
          severity: "success",
          summary: "Character profile updated.",
          life: 4_000,
        });
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update profile.";
      } finally {
        this.busy = false;
      }
    },
    choosePortrait(): void {
      const input = this.$refs.portraitInput as HTMLInputElement | undefined;
      input?.click();
    },
    async archive(): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await archiveCharacter(this.campaignId, this.character.id);
        await this.$router.replace(`/c/${this.campaignId}/characters`);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to archive character.";
      }
    },
    async uploadPortrait(event: Event): Promise<void> {
      const input = event.target as HTMLInputElement;
      const file = input.files?.[0];

      if (!file || !this.character) {
        return;
      }

      try {
        await uploadCharacterPortrait(this.campaignId, this.character.id, file);
        this.$toast.add({
          severity: "success",
          summary: "Portrait updated.",
          life: 4_000,
        });
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to upload portrait.";
      } finally {
        input.value = "";
      }
    },
    async removePortrait(): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await removeCharacterPortrait(this.campaignId, this.character.id);
        this.$toast.add({
          severity: "success",
          summary: "Portrait removed.",
          life: 4_000,
        });
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to remove portrait.";
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

@media (min-width: 768px) {
  .coin-pouch-card {
    max-width: 64rem;
  }

  .coin-value-column {
    border-top: 0 !important;
    border-left: var(--bs-border-width) var(--bs-border-style) var(--bs-border-color) !important;
  }
}
</style>
