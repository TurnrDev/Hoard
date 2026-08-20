<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  archiveCharacter,
  commitCahImport,
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  getCampaign,
  getCharacters,
  getItems,
  getMyCharacters,
  getTransactions,
  previewCahImport,
  updateCharacter,
  type CahPreview,
  type Campaign,
  type Character,
  type Item,
  type LedgerTransaction,
} from "../api";
import { useCampaignRefresh } from "../realtime";
import { exchangedCoinAmount } from "../coinExchange";
import CoinAmountPicker from "../components/CoinAmountPicker.vue";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
import type { PickerCandidate } from "../itemPicker";
import { formatGoldValue } from "../money";

const route = useRoute();
const router = useRouter();
const campaignId = Number(route.params.id);
const characterId = Number(route.params.characterId);
const campaign = ref<Campaign>();
const character = ref<Character>();
const ownCharacter = ref(false);
const characters = ref<Character[]>([]);
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");
const grantItemId = ref<number>();
const grantQuantity = ref(1);
const itemAction = ref<"use" | "destroy" | "transfer">();
const selectedInventoryItem = ref<{
  item_id: number;
  name: string;
  quantity: number;
}>();
const itemActionQuantity = ref(1);
const itemActionDestination = ref<number>();
const itemActionDescription = ref("");
const moneyAction = ref<"spend" | "transfer" | "exchange">("spend");
const moneyDialog = ref(false);
const denomination = ref("gp");
const amount = ref(1);
const moneyAmounts = ref<Record<string, number>>({
  pp: 0,
  gp: 0,
  ep: 0,
  sp: 0,
  cp: 0,
});
const moneyDestination = ref<number>();
const exchangeTargetDenomination = ref("sp");
const moneyDescription = ref("");
const editOpen = ref(false);
const importOpen = ref(false);
const addItemOpen = ref(false);
const activity = ref<LedgerTransaction[]>([]);
const importFile = ref<File>();
const importPreview = ref<CahPreview>();
const editName = ref("");
const editRace = ref("");
const editClass = ref("");
const editBaseHp = ref(1);
const editProficiencyAdjustment = ref(0);
const editAbilities = ref({
  strength: 10,
  dexterity: 10,
  constitution: 10,
  intelligence: 10,
  wisdom: 10,
  charisma: 10,
});
const denominations = ["cp", "sp", "ep", "gp", "pp"];
const xpThresholds = [
  0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000,
  140000, 165000, 195000, 225000, 265000, 305000, 355000,
];
const allItemCandidates = computed<PickerCandidate[]>(() =>
  items.value.map((item) => ({ item })),
);
const inventoryRows = computed(() =>
  (character.value?.inventory ?? []).map((entry) => ({
    ...entry,
    item: items.value.find((item) => item.id === entry.item_id),
  })),
);
const destinationOptions = computed(() => [
  ...characters.value
    .filter(
      (candidate) =>
        candidate.id !== character.value?.id &&
        candidate.is_active &&
        !candidate.is_archived,
    )
    .map((candidate) => ({ title: candidate.name, value: candidate.id })),
]);
const exchangeAmount = computed(() =>
  exchangedCoinAmount(
    denomination.value,
    exchangeTargetDenomination.value,
    amount.value,
  ),
);
const submittedMoneyAmounts = computed(() =>
  Object.fromEntries(
    Object.entries(moneyAmounts.value).filter(
      ([, value]) => Number.isInteger(value) && value > 0,
    ),
  ),
);
const hasInvalidMoneyAmounts = computed(() =>
  Object.values(moneyAmounts.value).some(
    (value) => !Number.isInteger(value) || value < 0,
  ),
);
const hasMoneyAmounts = computed(
  () => Object.keys(submittedMoneyAmounts.value).length > 0,
);
const selectedInventoryQuantity = computed(
  () => selectedInventoryItem.value?.quantity ?? 0,
);
const itemActionInvalid = computed(
  () =>
    itemActionQuantity.value < 1 ||
    itemActionQuantity.value > selectedInventoryQuantity.value ||
    (itemAction.value === "transfer" && !itemActionDestination.value),
);
const canAct = computed(
  () =>
    ownCharacter.value && character.value?.is_active && !character.value.is_archived,
);
const canEdit = computed(() => ownCharacter.value || campaign.value?.is_game_master);
const skillAbilities: Record<string, string> = {
  acrobatics: "dexterity",
  animal_handling: "wisdom",
  arcana: "intelligence",
  athletics: "strength",
  deception: "charisma",
  history: "intelligence",
  insight: "wisdom",
  intimidation: "charisma",
  investigation: "intelligence",
  medicine: "wisdom",
  nature: "intelligence",
  perception: "wisdom",
  performance: "charisma",
  persuasion: "charisma",
  religion: "intelligence",
  sleight_of_hand: "dexterity",
  stealth: "dexterity",
  survival: "wisdom",
};
const abilityGroups = computed(() => {
  if (!character.value) return [];
  return [
    ["strength", "Strength", "STR"],
    ["dexterity", "Dexterity", "DEX"],
    ["constitution", "Constitution", "CON"],
    ["intelligence", "Intelligence", "INT"],
    ["wisdom", "Wisdom", "WIS"],
    ["charisma", "Charisma", "CHA"],
  ].map(([key, label, abbreviation]) => ({
    key,
    label,
    abbreviation,
    score: {
      strength: character.value!.strength,
      dexterity: character.value!.dexterity,
      constitution: character.value!.constitution,
      intelligence: character.value!.intelligence,
      wisdom: character.value!.wisdom,
      charisma: character.value!.charisma,
    }[key],
    modifier: character.value!.sheet.abilities[key].modifier,
    save: character.value!.sheet.saves[key],
    skills: Object.entries(character.value!.sheet.skills)
      .filter(([name]) => skillAbilities[name] === key)
      .map(([name, skill]) => ({ name, ...skill })),
  }));
});
const skillGroups = computed(() => {
  const order = ["strength", "wisdom", "dexterity", "charisma", "intelligence"];
  return abilityGroups.value
    .filter((ability) => ability.skills.length)
    .sort((left, right) => order.indexOf(left.key) - order.indexOf(right.key));
});
const skillColumns = computed(() => [
  skillGroups.value.filter((ability) =>
    ["strength", "dexterity", "intelligence"].includes(ability.key),
  ),
  skillGroups.value.filter((ability) => ["wisdom", "charisma"].includes(ability.key)),
]);
const displayName = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const signed = (value: number) => (value >= 0 ? `+${value}` : `${value}`);
const formatXp = (value: number) => `${value.toLocaleString()} XP`;
const activityAmount = (transaction: LedgerTransaction) =>
  transaction.entries
    .filter((entry) => entry.account_name === character.value?.name)
    .map(
      (entry) =>
        `${entry.amount > 0 ? "+" : ""}${entry.amount} ${
          entry.item_name ?? entry.denomination ?? "XP"
        }`,
    )
    .join(" · ");
const experienceProgress = computed(() => {
  const level = character.value?.sheet.level ?? 1;
  const current = character.value?.experience ?? 0;
  const minimum = xpThresholds[level - 1] ?? 0;
  const maximum = xpThresholds[level];
  const progress = maximum
    ? Math.min(100, Math.max(0, ((current - minimum) / (maximum - minimum)) * 100))
    : 100;
  return { current, level, maximum, minimum, progress };
});
const proficiencyLabel = (proficiency: string) =>
  ({ half: "Half", proficient: "Proficient", expertise: "Expertise" })[proficiency] ??
  "";
const proficiencyClass = (proficiency: string) =>
  `proficiency-bonus proficiency-bonus--${proficiency}`;
const importChanges = computed(() => {
  if (!character.value || !importPreview.value) return [];
  const current: Record<string, unknown> = {
    name: character.value.name,
    race: character.value.race,
    base_hp: character.value.sheet.base_hp,
    proficiency_bonus_adjustment: character.value.sheet.proficiency_bonus_adjustment,
    strength: character.value.strength,
    dexterity: character.value.dexterity,
    constitution: character.value.constitution,
    intelligence: character.value.intelligence,
    wisdom: character.value.wisdom,
    charisma: character.value.charisma,
  };
  const labels: Record<string, string> = {
    name: "Name",
    race: "Race",
    base_hp: "Base HP",
    proficiency_bonus_adjustment: "Proficiency adjustment",
    strength: "Strength",
    dexterity: "Dexterity",
    constitution: "Constitution",
    intelligence: "Intelligence",
    wisdom: "Wisdom",
    charisma: "Charisma",
  };
  for (const ability of [
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
  ]) {
    const label = labels[ability];
    current[`${ability}_modifier_adjustment`] =
      character.value.sheet.abilities[ability]?.adjustment ?? 0;
    current[`${ability}_save_proficient`] =
      character.value.sheet.saves[ability]?.proficient ?? false;
    current[`${ability}_save_adjustment`] =
      character.value.sheet.saves[ability]?.adjustment ?? 0;
    labels[`${ability}_modifier_adjustment`] = `${label} adjustment`;
    labels[`${ability}_save_proficient`] = `${label} save proficiency`;
    labels[`${ability}_save_adjustment`] = `${label} save adjustment`;
  }
  const changes = Object.entries(importPreview.value.fields).flatMap(
    ([field, next]) => {
      if (field === "skill_proficiencies") {
        return Object.entries(next as Record<string, string>)
          .filter(
            ([skill, proficiency]) =>
              character.value?.sheet.skills[skill]?.proficiency !== proficiency,
          )
          .map(([skill, proficiency]) => ({
            label: skill.replaceAll("_", " "),
            current: character.value?.sheet.skills[skill]?.proficiency ?? "none",
            next: proficiency,
          }));
      }
      if (!(field in current) || current[field] === next) return [];
      return [{ label: labels[field] ?? field, current: current[field], next }];
    },
  );
  return changes;
});

async function load(): Promise<void> {
  try {
    const [nextCampaign, visible, own, nextItems, recent] = await Promise.all([
      getCampaign(campaignId),
      getCharacters(campaignId),
      getMyCharacters(campaignId),
      getItems(campaignId),
      getTransactions(campaignId, "all", 1, characterId),
    ]);
    campaign.value = nextCampaign;
    characters.value = visible;
    character.value =
      visible.find((candidate) => candidate.id === characterId) ??
      own.find((candidate) => candidate.id === characterId);
    ownCharacter.value = own.some((candidate) => candidate.id === characterId);
    items.value = nextItems;
    activity.value = recent.results.slice(0, 5);
    if (!character.value) await router.replace(`/c/${campaignId}/characters`);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load character profile.";
  }
}

async function grantItem(): Promise<void> {
  if (!character.value || !grantItemId.value) return;
  try {
    await createInventoryTransaction(campaignId, {
      from_character_id: null,
      to_character_id: character.value.id,
      item_id: grantItemId.value,
      quantity: grantQuantity.value,
      description: "Self-granted item",
    });
    notice.value = "Saved to the ledger.";
    closeAddItemDialog();
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to complete this action.";
  }
}

function openItemAction(
  action: "use" | "destroy" | "transfer",
  entry: { item_id: number; name: string; quantity: number },
): void {
  itemAction.value = action;
  selectedInventoryItem.value = entry;
  itemActionQuantity.value = 1;
  itemActionDestination.value = undefined;
  itemActionDescription.value = "";
}

function closeItemAction(): void {
  itemAction.value = undefined;
  selectedInventoryItem.value = undefined;
  itemActionQuantity.value = 1;
  itemActionDestination.value = undefined;
  itemActionDescription.value = "";
}

function closeAddItemDialog(): void {
  addItemOpen.value = false;
  grantItemId.value = undefined;
  grantQuantity.value = 1;
}

function closeMoneyDialog(): void {
  moneyDialog.value = false;
  moneyAction.value = "spend";
  denomination.value = "gp";
  amount.value = 1;
  exchangeTargetDenomination.value = "sp";
  moneyAmounts.value = { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 };
  moneyDestination.value = undefined;
  moneyDescription.value = "";
}

function closeEditDialog(): void {
  editOpen.value = false;
  editName.value = "";
  editRace.value = "";
  editClass.value = "";
  editBaseHp.value = 1;
  editProficiencyAdjustment.value = 0;
  editAbilities.value = {
    strength: 10,
    dexterity: 10,
    constitution: 10,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
  };
}

function closeImportDialog(): void {
  importOpen.value = false;
  importFile.value = undefined;
  importPreview.value = undefined;
}

async function submitItemAction(): Promise<void> {
  if (!character.value || !selectedInventoryItem.value || !itemAction.value) return;
  if (
    itemActionQuantity.value < 1 ||
    itemActionQuantity.value > selectedInventoryQuantity.value ||
    (itemAction.value === "transfer" && !itemActionDestination.value)
  )
    return;
  try {
    await createInventoryTransaction(campaignId, {
      from_character_id: character.value.id,
      to_character_id:
        itemAction.value === "transfer" ? itemActionDestination.value! : null,
      item_id: selectedInventoryItem.value.item_id,
      quantity: itemActionQuantity.value,
      description:
        itemActionDescription.value ||
        `${itemAction.value === "use" ? "Used" : itemAction.value === "destroy" ? "Destroyed" : "Transferred"} ${selectedInventoryItem.value.name}`,
    });
    notice.value = "Saved to the ledger.";
    closeItemAction();
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update inventory.";
  }
}

async function submitMoneyAction(): Promise<void> {
  if (!character.value) return;
  try {
    if (moneyAction.value === "exchange") {
      if (!exchangeAmount.value) return;
      await createMoneyExchange(campaignId, {
        character_id: character.value.id,
        given: { [denomination.value]: amount.value },
        received: { [exchangeTargetDenomination.value]: exchangeAmount.value },
        description: moneyDescription.value,
      });
    } else {
      if (!hasMoneyAmounts.value || hasInvalidMoneyAmounts.value) return;
      await createMoneyTransfer(campaignId, {
        from_character_id: character.value.id,
        to_character_id:
          moneyAction.value === "transfer" ? (moneyDestination.value ?? null) : null,
        amounts: submittedMoneyAmounts.value,
        description: moneyDescription.value,
      });
    }
    notice.value = "Saved to the ledger.";
    closeMoneyDialog();
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update money.";
  }
}

function openMoneyDialog(action: "spend" | "transfer" | "exchange"): void {
  closeMoneyDialog();
  moneyAction.value = action;
  moneyDialog.value = true;
}

function openEdit(): void {
  if (!character.value) return;
  editName.value = character.value.name;
  editRace.value = character.value.race;
  editClass.value = character.value.class;
  editBaseHp.value = character.value.sheet.base_hp;
  editProficiencyAdjustment.value = character.value.sheet.proficiency_bonus_adjustment;
  editAbilities.value = {
    strength: character.value.strength,
    dexterity: character.value.dexterity,
    constitution: character.value.constitution,
    intelligence: character.value.intelligence,
    wisdom: character.value.wisdom,
    charisma: character.value.charisma,
  };
  editOpen.value = true;
}

async function saveProfile(): Promise<void> {
  if (!character.value || !editName.value.trim()) return;
  try {
    await updateCharacter(campaignId, character.value.id, {
      name: editName.value.trim(),
      race: editRace.value,
      class: editClass.value,
      base_hp: editBaseHp.value,
      proficiency_bonus_adjustment: editProficiencyAdjustment.value,
      ...editAbilities.value,
    });
    closeEditDialog();
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update character.";
  }
}

async function archive(): Promise<void> {
  if (!character.value) return;
  try {
    await archiveCharacter(campaignId, character.value.id);
    await router.replace(`/c/${campaignId}/characters`);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to archive character.";
  }
}

async function previewImport(): Promise<void> {
  if (!importFile.value) return;
  try {
    importPreview.value = await previewCahImport(campaignId, importFile.value);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to read CAH file.";
  }
}

async function commitImport(): Promise<void> {
  if (!character.value || !importPreview.value) return;
  try {
    await commitCahImport(campaignId, importPreview.value.token, character.value.id);
    closeImportDialog();
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to import character.";
  }
}

onMounted(load);
useCampaignRefresh(load);
</script>

<template>
  <v-container
    class="page-shell"
    v-if="character"
  >
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Character profile</div>
        <h1>{{ character.name }}</h1>
        <p>{{ character.race }} · {{ character.class }}</p>
      </div>
      <div class="d-flex ga-2">
        <v-btn
          v-if="canEdit"
          @click="openEdit"
        >
          Edit
        </v-btn>
        <v-btn
          v-if="ownCharacter"
          variant="tonal"
          @click="importOpen = true"
        >
          Import CAH
        </v-btn>
        <v-btn
          :to="`/c/${campaignId}/characters`"
          prepend-icon="mdi-account-group-outline"
        >
          Roster
        </v-btn>
      </div>
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
    <v-alert
      v-if="notice"
      type="success"
      closable
      class="mb-4"
      @click:close="notice = ''"
    >
      {{ notice }}
    </v-alert>
    <v-row
      dense
      class="profile-overview"
    >
      <v-col
        cols="12"
        md="5"
      >
        <v-card class="profile-card h-100">
          <v-card-text>
            <div class="text-overline">Level {{ experienceProgress.level }}</div>
            <v-progress-linear
              class="mt-2"
              color="primary"
              :model-value="experienceProgress.progress"
              height="8"
              rounded
              :aria-label="`Level ${experienceProgress.level} experience progress`"
            />
            <div class="xp-progress-labels">
              <span>{{ formatXp(experienceProgress.minimum) }}</span>
              <strong>{{ formatXp(experienceProgress.current) }}</strong>
              <span v-if="experienceProgress.maximum">
                {{ formatXp(experienceProgress.maximum) }}
              </span>
              <span v-else>Maximum level</span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="7"
      >
        <v-card class="profile-card h-100 coin-summary-card">
          <v-row
            no-gutters
            class="h-100"
          >
            <v-col
              cols="12"
              sm="7"
            >
              <v-card-text>
                <div class="text-overline">Coin pouch</div>
                <div class="money-line mt-3">
                  {{ character.money.pp }} pp · {{ character.money.gp }} gp ·
                  {{ character.money.ep }} ep · {{ character.money.sp }} sp ·
                  {{ character.money.cp }} cp
                </div>
              </v-card-text>
            </v-col>
            <v-col
              cols="12"
              sm="5"
              class="coin-value-pane"
            >
              <v-card-text>
                <div class="text-overline">Coin value</div>
                <div class="d-flex align-center justify-space-between mt-3">
                  <div class="text-h4">
                    {{ formatGoldValue(character.money.gold_value) }} ¤
                  </div>
                  <v-menu v-if="canAct">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon="mdi-dots-horizontal"
                        size="small"
                        variant="text"
                        aria-label="Coin actions"
                      />
                    </template>
                    <v-list density="compact">
                      <v-list-item
                        title="Spend coins"
                        prepend-icon="mdi-cash-minus"
                        @click="openMoneyDialog('spend')"
                      />
                      <v-list-item
                        title="Transfer coins"
                        prepend-icon="mdi-cash-fast"
                        @click="openMoneyDialog('transfer')"
                      />
                      <v-list-item
                        title="Exchange coins"
                        prepend-icon="mdi-swap-horizontal"
                        @click="openMoneyDialog('exchange')"
                      />
                    </v-list>
                  </v-menu>
                </div>
              </v-card-text>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
      <v-col cols="12">
        <v-row
          dense
          class="profile-stat-row"
        >
          <v-col
            cols="12"
            sm="4"
          >
            <v-card class="profile-card">
              <v-card-text>
                <div class="text-overline">HP</div>
                <div class="text-h5">{{ character.sheet.max_hp }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col
            cols="12"
            sm="4"
          >
            <v-card class="profile-card">
              <v-card-text>
                <div class="text-overline">Initiative bonus</div>
                <div class="text-h5">
                  {{ signed(character.sheet.abilities.dexterity.modifier) }}
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col
            cols="12"
            sm="4"
          >
            <v-card class="profile-card">
              <v-card-text>
                <div class="text-overline">Proficiency bonus</div>
                <div class="text-h5">
                  {{ signed(character.sheet.proficiency_bonus) }}
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="12">
        <v-card class="ability-save-card">
          <v-card-text>
            <v-row dense>
              <v-col
                v-for="ability in abilityGroups"
                :key="ability.key"
                class="ability-save-cell"
                cols="12"
                sm="6"
                md="2"
              >
                <div class="ability-save">
                  <div class="ability-save-heading">
                    <span class="ability-save-name">{{ ability.abbreviation }}</span>
                    <strong>{{ signed(ability.modifier) }}</strong>
                    <span class="ability-save-score">{{ ability.score }}</span>
                  </div>
                  <v-divider class="my-3" />
                  <div class="ability-save-row">
                    <span>SAVE</span>
                    <v-tooltip
                      v-if="ability.save.proficient"
                      :text="proficiencyLabel('proficient')"
                      location="top"
                    >
                      <template #activator="{ props }">
                        <strong
                          v-bind="props"
                          :class="proficiencyClass('proficient')"
                        >
                          {{ signed(ability.save.bonus) }}
                        </strong>
                      </template>
                    </v-tooltip>
                    <strong v-else>{{ signed(ability.save.bonus) }}</strong>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
        <v-card class="mt-4 inventory-card">
          <v-card-title class="d-flex align-center">
            Inventory
            <span class="text-caption text-medium-emphasis ml-3">
              {{ character.inventory.length }} items
            </span>
            <v-spacer />
            <v-btn
              v-if="canAct"
              size="small"
              prepend-icon="mdi-plus"
              @click="addItemOpen = true"
            >
              Add item
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-table
              v-if="character.inventory.length"
              density="compact"
            >
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Quantity</th>
                  <th>Weight</th>
                  <th>Value</th>
                  <th class="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="entry in inventoryRows"
                  :key="entry.item_id"
                >
                  <td>{{ entry.name }}</td>
                  <td>{{ entry.quantity }}</td>
                  <td>
                    {{
                      entry.item?.equipment.weight_amount
                        ? `${entry.item.equipment.weight_amount} ${entry.item.equipment.weight_unit}`
                        : "—"
                    }}
                  </td>
                  <td>
                    {{
                      entry.item?.equipment.cost_amount
                        ? `${entry.item.equipment.cost_amount} ${entry.item.equipment.cost_currency}`
                        : "—"
                    }}
                  </td>
                  <td class="text-right">
                    <v-menu v-if="canAct">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          icon="mdi-dots-horizontal"
                          size="small"
                          variant="text"
                        />
                      </template>
                      <v-list density="compact">
                        <v-list-item
                          title="Use"
                          @click="openItemAction('use', entry)"
                        />
                        <v-list-item
                          title="Transfer"
                          @click="openItemAction('transfer', entry)"
                        />
                        <v-list-item
                          title="Destroy"
                          base-color="error"
                          @click="openItemAction('destroy', entry)"
                        />
                      </v-list>
                    </v-menu>
                  </td>
                </tr>
              </tbody>
            </v-table>
            <span
              v-else
              class="text-medium-emphasis"
            >
              No inventory recorded.
            </span>
          </v-card-text>
        </v-card>
        <v-expansion-panels
          class="mt-4 skills-panel"
          variant="accordion"
        >
          <v-expansion-panel title="Skills">
            <v-expansion-panel-text>
              <v-row dense>
                <v-col
                  v-for="(column, columnIndex) in skillColumns"
                  :key="columnIndex"
                  cols="12"
                  sm="6"
                >
                  <div
                    v-for="ability in column"
                    :key="ability.key"
                    class="skill-group"
                  >
                    <div class="skill-group-title">{{ ability.label }}</div>
                    <div
                      v-for="skill in ability.skills"
                      :key="skill.name"
                      class="skill-row"
                    >
                      <strong
                        :class="
                          skill.proficiency !== 'none'
                            ? proficiencyClass(skill.proficiency)
                            : ''
                        "
                      >
                        {{ signed(skill.bonus) }}
                      </strong>
                      <span>{{ displayName(skill.name) }}</span>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
        <v-card class="mt-4 activity-card">
          <v-card-title class="d-flex align-center">
            Recent activity
            <v-spacer />
            <v-btn
              :to="`/c/${campaignId}/ledger`"
              size="small"
              variant="text"
            >
              View full ledger
            </v-btn>
          </v-card-title>
          <v-card-text>
            <template v-if="activity.length">
              <div
                v-for="transaction in activity"
                :key="`${transaction.ledger}-${transaction.id}`"
                class="activity-row"
              >
                <span>{{ new Date(transaction.created_at).toLocaleString() }}</span>
                <strong>{{ activityAmount(transaction) }}</strong>
                <span>{{ transaction.description || transaction.ledger }}</span>
                <span>{{ transaction.actor ? `by ${transaction.actor}` : "—" }}</span>
              </div>
            </template>
            <span
              v-else
              class="text-medium-emphasis"
            >
              No recent activity.
            </span>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-dialog
      v-model="addItemOpen"
      max-width="560"
      @update:model-value="(open) => !open && closeAddItemDialog()"
    >
      <v-card title="Add item">
        <v-card-text>
          <ItemPickerDialog
            v-model="grantItemId"
            :candidates="allItemCandidates"
            label="Item"
            no-data-text="No campaign items available."
          />
          <v-text-field
            v-model.number="grantQuantity"
            type="number"
            min="1"
            label="Quantity"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeAddItemDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!grantItemId || grantQuantity < 1"
            @click="grantItem"
          >
            Add item
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="moneyDialog"
      max-width="620"
      @update:model-value="(open) => !open && closeMoneyDialog()"
    >
      <v-card
        :title="
          moneyAction === 'spend'
            ? 'Spend coins'
            : moneyAction === 'transfer'
              ? 'Transfer coins'
              : 'Exchange coins'
        "
      >
        <v-card-text>
          <template v-if="moneyAction === 'spend'">
            <CoinAmountPicker v-model="moneyAmounts" />
            <div class="text-caption text-medium-emphasis mb-3">
              Coins will be transferred to the campaign system.
            </div>
          </template>
          <template v-else-if="moneyAction === 'transfer'">
            <v-select
              v-model="moneyDestination"
              :items="destinationOptions"
              label="Transfer to"
            />
            <CoinAmountPicker v-model="moneyAmounts" />
          </template>
          <template v-else>
            <v-row>
              <v-col>
                <v-select
                  v-model="denomination"
                  :items="denominations"
                  label="Source denomination"
                />
                <v-text-field
                  v-model.number="amount"
                  type="number"
                  min="1"
                  label="Source coins"
                />
              </v-col>
              <v-col>
                <v-select
                  v-model="exchangeTargetDenomination"
                  :items="denominations"
                  label="Target denomination"
                />
                <v-text-field
                  :model-value="exchangeAmount ?? ''"
                  readonly
                  label="Target coins"
                />
              </v-col>
            </v-row>
            <v-alert
              v-if="!exchangeAmount"
              type="warning"
              variant="tonal"
              density="compact"
            >
              Choose different denominations and an exactly convertible quantity.
            </v-alert>
          </template>
          <v-textarea
            v-if="moneyAction !== 'exchange'"
            v-model="moneyDescription"
            label="Note (optional)"
            rows="2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeMoneyDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="
              moneyAction === 'transfer'
                ? !moneyDestination || !hasMoneyAmounts || hasInvalidMoneyAmounts
                : moneyAction === 'exchange'
                  ? !exchangeAmount
                  : !hasMoneyAmounts || hasInvalidMoneyAmounts
            "
            @click="submitMoneyAction"
          >
            {{
              moneyAction === "spend"
                ? "Spend coins"
                : moneyAction === "transfer"
                  ? "Transfer coins"
                  : "Exchange coins"
            }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      :model-value="Boolean(itemAction)"
      max-width="560"
      @update:model-value="(value) => !value && closeItemAction()"
    >
      <v-card
        :title="
          itemAction === 'use'
            ? 'Use item'
            : itemAction === 'destroy'
              ? 'Destroy item'
              : 'Transfer item'
        "
      >
        <v-card-text v-if="selectedInventoryItem">
          <div class="mb-4">
            {{ selectedInventoryItem.name }} · {{ selectedInventoryItem.quantity }} held
          </div>
          <v-select
            v-if="itemAction === 'transfer'"
            v-model="itemActionDestination"
            :items="destinationOptions"
            label="Transfer to"
          />
          <v-text-field
            v-model.number="itemActionQuantity"
            type="number"
            min="1"
            :max="selectedInventoryItem.quantity"
            label="Quantity"
          />
          <v-textarea
            v-model="itemActionDescription"
            label="Note (optional)"
            rows="2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeItemAction">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="itemActionInvalid"
            @click="submitItemAction"
          >
            {{
              itemAction === "use"
                ? "Use item"
                : itemAction === "destroy"
                  ? "Destroy item"
                  : "Transfer item"
            }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="editOpen"
      max-width="720"
      @update:model-value="(open) => !open && closeEditDialog()"
    >
      <v-card title="Edit character">
        <v-card-text>
          <v-row>
            <v-col
              cols="12"
              sm="4"
            >
              <v-text-field
                v-model="editName"
                label="Name"
              />
            </v-col>
            <v-col
              cols="12"
              sm="4"
            >
              <v-text-field
                v-model="editRace"
                label="Race"
              />
            </v-col>
            <v-col
              cols="12"
              sm="4"
            >
              <v-text-field
                v-model="editClass"
                label="Class"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col
              cols="12"
              sm="4"
            >
              <v-text-field
                v-model.number="editBaseHp"
                type="number"
                min="1"
                label="Base HP"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col
              v-for="(_, ability) in editAbilities"
              :key="ability"
              cols="6"
              sm="4"
            >
              <v-text-field
                v-model.number="editAbilities[ability]"
                type="number"
                min="1"
                max="30"
                :label="ability[0].toUpperCase() + ability.slice(1)"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn
            color="error"
            variant="text"
            @click="archive"
          >
            Archive
          </v-btn>
          <v-spacer />
          <v-btn @click="closeEditDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="saveProfile"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="importOpen"
      max-width="560"
      @update:model-value="(open) => !open && closeImportDialog()"
    >
      <v-card title="Import 5e Companion character">
        <v-card-text>
          <v-file-input
            v-model="importFile"
            accept=".cah,application/json"
            label="CAH export"
            @update:model-value="importPreview = undefined"
          />
          <v-btn
            :disabled="!importFile"
            @click="previewImport"
          >
            Preview import
          </v-btn>
          <template v-if="importPreview">
            <v-card
              variant="tonal"
              class="mt-4"
            >
              <v-card-title class="text-subtitle-1">Changes to apply</v-card-title>
              <v-list density="compact">
                <v-list-item
                  v-for="change in importChanges"
                  :key="change.label"
                  :title="change.label"
                  :subtitle="`${change.current} → ${change.next}`"
                />
                <v-list-item
                  v-if="!importChanges.length"
                  title="No supported values would change."
                />
              </v-list>
            </v-card>
            <v-alert
              v-if="importPreview.warnings.length"
              type="warning"
              class="mt-4"
            >
              <div
                v-for="warning in importPreview.warnings"
                :key="warning"
              >
                {{ warning }}
              </div>
            </v-alert>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeImportDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!importPreview"
            @click="commitImport"
          >
            Replace reference sheet
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
