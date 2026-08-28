<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  archiveCharacter,
  castCharacterSpell,
  changeCharacterSheetRecord,
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  getCampaign,
  getCharacters,
  getItems,
  getMyCharacters,
  getTransactions,
  postHealth,
  restCharacter,
  setCharacterInspiration,
  type Campaign,
  type Character,
  type Item,
  type LedgerTransaction,
} from "../api";
import { useCampaignRefresh } from "../realtime";
import { exchangedCoinAmount } from "../coinExchange";
import CoinAmountPicker from "../components/CoinAmountPicker.vue";
import CalculationBreakdown from "../components/CalculationBreakdown.vue";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
import type { PickerCandidate } from "../itemPicker";
import { formatGoldValue } from "../money";
import { displayCoin, displayIdentifier, formatCoinPouch } from "../display";

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
if (typeof route.query.level_up_error === "string") {
  error.value = route.query.level_up_error;
}
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
const addItemOpen = ref(false);
const activity = ref<LedgerTransaction[]>([]);
const healthOpen = ref(false);
const hpAdjustmentOpen = ref(false);
const healthReason = ref<"damage" | "healing" | "temporary" | "correction">("damage");
const healthAmount = ref(1);
const healthCurrent = ref(0);
const healthTemporary = ref(0);
const healthDescription = ref("");
const shortRestOpen = ref(false);
const shortRestHp = ref(0);
const spellCastOpen = ref(false);
const castingSpell = ref<Character["spells"][number]>();
const castingSlot = ref<string>();
const effectOpen = ref(false);
const effectName = ref("");
const effectSource = ref("");
const effectDuration = ref("");
const effectReminder = ref("");
const effectTarget = ref("ac");
const effectValue = ref(0);
const healthPreview = computed(() => {
  if (!character.value) return "";
  const beforeCurrent = character.value.sheet.current_hp;
  const beforeTemporary = character.value.sheet.temporary_hp;
  if (healthReason.value === "correction") {
    return `Current ${beforeCurrent} → ${healthCurrent.value}; temporary ${beforeTemporary} → ${healthTemporary.value}`;
  }
  if (healthReason.value === "damage") {
    const damage = Math.abs(healthAmount.value);
    const absorbed = Math.min(beforeTemporary, damage);
    return `Damage ${damage}: temporary ${beforeTemporary} − ${absorbed} = ${beforeTemporary - absorbed}; current ${beforeCurrent} − ${damage - absorbed} = ${Math.max(0, beforeCurrent - (damage - absorbed))}`;
  }
  if (healthReason.value === "healing") {
    return `Current ${beforeCurrent} + ${Math.abs(healthAmount.value)} = ${Math.min(character.value.sheet.max_hp, beforeCurrent + Math.abs(healthAmount.value))} (maximum ${character.value.sheet.max_hp})`;
  }
  return `Temporary ${beforeTemporary} + ${healthAmount.value} = ${beforeTemporary + healthAmount.value}`;
});
const denominations = ["cp", "sp", "ep", "gp", "pp"].map((value) => ({
  title: displayCoin(value),
  value,
}));
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
const canDamage = computed(() => {
  const sheet = character.value?.sheet;
  return Boolean(sheet && (sheet.current_hp > 0 || sheet.temporary_hp > 0));
});
const canHeal = computed(() => {
  const sheet = character.value?.sheet;
  return Boolean(sheet && sheet.current_hp < sheet.max_hp);
});
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
const displayName = displayIdentifier;
const signed = (value: number) => (value >= 0 ? `+${value}` : `${value}`);
const formatXp = (value: number) => `${value.toLocaleString()} XP`;
const castingSlots = computed(() => {
  const spell = castingSpell.value;
  if (!spell || !character.value) return [];
  return Object.entries(character.value.sheet.spell_slot_pools)
    .filter(
      ([key, pool]) =>
        !key.startsWith("pact-") && Number(key) >= spell.level && pool.current > 0,
    )
    .map(([key, pool]) => ({
      title: `Level ${key} (${pool.current}/${pool.maximum})`,
      value: key,
    }));
});
const effectTargets = [
  "ac",
  "speed",
  "spell_attack",
  "spell_dc",
  "weapon_attack",
  "weapon_damage",
  "ability:strength",
  "ability:dexterity",
  "ability:constitution",
  "ability:intelligence",
  "ability:wisdom",
  "ability:charisma",
  "save:strength",
  "save:dexterity",
  "save:constitution",
  "save:intelligence",
  "save:wisdom",
  "save:charisma",
].map((value) => ({ title: displayIdentifier(value.replace(":", " ")), value }));
const activityAmount = (transaction: LedgerTransaction) =>
  transaction.entries
    .filter((entry) => entry.account_name === character.value?.name)
    .map(
      (entry) =>
        `${entry.amount > 0 ? "+" : ""}${entry.amount} ${
          entry.item_name ??
          (entry.denomination ? displayCoin(entry.denomination) : "XP")
        }`,
    )
    .join(" · ");
const activityDescription = (transaction: LedgerTransaction) =>
  transaction.description ||
  transaction.ledger_label ||
  displayIdentifier(transaction.ledger);
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
    if (ownCharacter.value && character.value && !character.value.is_build_complete) {
      await router.replace(`/c/${campaignId}/characters/${characterId}/build`);
      return;
    }
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

function openHealth(): void {
  if (!character.value) return;
  healthCurrent.value = character.value.sheet.current_hp;
  healthTemporary.value = character.value.sheet.temporary_hp;
  healthAmount.value = 1;
  healthDescription.value = "";
  healthOpen.value = true;
}

function openHealthFor(
  reason: "damage" | "healing" | "temporary" | "correction",
): void {
  healthReason.value = reason;
  openHealth();
}

function openHpAdjustment(): void {
  healthAmount.value = 1;
  hpAdjustmentOpen.value = true;
}

async function submitHpAdjustment(reason: "damage" | "healing"): Promise<void> {
  if (!character.value) return;
  try {
    await postHealth(campaignId, {
      character_id: character.value.id,
      reason,
      current_hp_delta:
        reason === "damage" ? -Math.abs(healthAmount.value) : healthAmount.value,
    });
    hpAdjustmentOpen.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update HP.";
  }
}

async function saveHealth(): Promise<void> {
  if (!character.value) return;
  try {
    await postHealth(campaignId, {
      character_id: character.value.id,
      reason: healthReason.value,
      ...(healthReason.value === "damage"
        ? { current_hp_delta: -Math.abs(healthAmount.value) }
        : {}),
      ...(healthReason.value === "healing"
        ? { current_hp_delta: Math.abs(healthAmount.value) }
        : {}),
      ...(healthReason.value === "temporary"
        ? { temporary_hp_delta: healthAmount.value }
        : {}),
      ...(healthReason.value === "correction"
        ? {
            current_hp: healthCurrent.value,
            temporary_hp: healthTemporary.value,
          }
        : {}),
      description: healthDescription.value,
    });
    healthOpen.value = false;
    healthDescription.value = "";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update HP.";
  }
}

async function toggleInspiration(): Promise<void> {
  if (!character.value) return;
  try {
    character.value = await setCharacterInspiration(
      campaignId,
      character.value.id,
      !character.value.has_inspiration,
    );
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update inspiration.";
  }
}

async function equipItem(entry: { item_id: number; name: string }): Promise<void> {
  if (!character.value) return;
  try {
    await changeCharacterSheetRecord(
      campaignId,
      character.value.id,
      "loadout",
      "create",
      {
        item_id: entry.item_id,
        equipped: true,
      },
    );
    notice.value = `${entry.name} equipped.`;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to equip item.";
  }
}

async function toggleEffect(effect: Character["effects"][number]): Promise<void> {
  if (!character.value) return;
  try {
    await changeCharacterSheetRecord(
      campaignId,
      character.value.id,
      "effects",
      "update",
      {
        enabled: !effect.enabled,
      },
      effect.id,
    );
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update effect.";
  }
}

function openEffect(): void {
  effectName.value = "";
  effectSource.value = "";
  effectDuration.value = "";
  effectReminder.value = "";
  effectTarget.value = "ac";
  effectValue.value = 0;
  effectOpen.value = true;
}

async function saveEffect(): Promise<void> {
  if (!character.value || !effectName.value.trim()) return;
  try {
    await changeCharacterSheetRecord(
      campaignId,
      character.value.id,
      "effects",
      "create",
      {
        name: effectName.value,
        source: effectSource.value,
        duration: effectDuration.value,
        reminder: effectReminder.value,
        modifiers: effectValue.value
          ? [{ target: effectTarget.value, value: effectValue.value }]
          : [],
      },
    );
    effectOpen.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to add effect.";
  }
}

async function deleteEffect(effect: Character["effects"][number]): Promise<void> {
  if (!character.value) return;
  try {
    await changeCharacterSheetRecord(
      campaignId,
      character.value.id,
      "effects",
      "delete",
      {},
      effect.id,
    );
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to remove effect.";
  }
}

function openShortRest(): void {
  if (!character.value) return;
  shortRestHp.value = character.value.sheet.current_hp;
  shortRestOpen.value = true;
}

async function takeRest(kind: "short" | "long"): Promise<void> {
  if (!character.value) return;
  try {
    character.value = await restCharacter(
      campaignId,
      character.value.id,
      kind,
      kind === "short" ? shortRestHp.value : undefined,
    );
    shortRestOpen.value = false;
    notice.value = `${kind === "short" ? "Short" : "Long"} rest recorded.`;
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to record rest.";
  }
}

function openSpellCast(spell: Character["spells"][number]): void {
  castingSpell.value = spell;
  castingSlot.value = undefined;
  if (spell.level === 0) void confirmSpellCast();
  else spellCastOpen.value = true;
}

async function confirmSpellCast(): Promise<void> {
  if (!character.value || !castingSpell.value) return;
  try {
    character.value = await castCharacterSpell(
      campaignId,
      character.value.id,
      castingSpell.value.id,
      castingSpell.value.level === 0 ? undefined : castingSlot.value,
    );
    spellCastOpen.value = false;
    notice.value = `${castingSpell.value.name} recorded.`;
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to record spell casting.";
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

onMounted(load);
useCampaignRefresh(load);
</script>

<template>
  <v-container
    class="page-shell"
    v-if="character"
  >
    <header class="page-heading character-profile-heading">
      <div class="character-profile-heading__details">
        <div class="text-overline text-secondary">Character profile</div>
        <h1>{{ character.name }}</h1>
        <p>{{ character.race }} · {{ character.class }}</p>
      </div>
      <div class="d-flex ga-2 character-profile-heading__actions">
        <v-menu v-if="canEdit">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon="mdi-dots-vertical"
              variant="text"
              aria-label="Character actions"
            />
          </template>
          <v-list density="compact">
            <v-list-item
              :to="`/c/${campaignId}/characters/${characterId}/build?mode=edit`"
              prepend-icon="mdi-pencil"
              title="Edit character"
            />
            <v-list-item
              base-color="error"
              prepend-icon="mdi-archive"
              title="Archive character"
              @click="archive"
            />
          </v-list>
        </v-menu>
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
      v-if="character && !character.level_up_complete"
      type="error"
      variant="tonal"
      class="mb-4"
      title="Level-up incomplete"
    >
      The GM has approved level {{ character.sheet.level }}, but this character still
      has unfinished choices.
      <template #append>
        <v-btn
          color="error"
          :to="'/c/' + campaignId + '/characters/' + characterId + '/level-up'"
        >
          Complete level-up
        </v-btn>
      </template>
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
          <div
            v-if="canAct"
            class="coin-summary-card__actions"
          >
            <v-menu location="bottom end">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-dots-vertical"
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
                  {{ formatCoinPouch(character.money) }}
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
                <div class="text-h4 mt-3">
                  {{ formatGoldValue(character.money.gold_value) }} ¤
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
            sm="6"
            lg="3"
          >
            <v-card
              v-ripple="canEdit"
              class="profile-card hp-card"
              :class="{ 'hp-card--interactive': canEdit }"
              :role="canEdit ? 'button' : undefined"
              :tabindex="canEdit ? 0 : undefined"
              @click="canEdit && openHpAdjustment()"
              @keydown.enter="canEdit && openHpAdjustment()"
              @keydown.space.prevent="canEdit && openHpAdjustment()"
            >
              <v-card-text>
                <div class="text-overline">HP</div>
                <div class="hp-summary mt-3">
                  <div class="text-h5 hp-value">
                    {{ character.sheet.current_hp }}
                    <template v-if="character.sheet.temporary_hp">
                      + {{ character.sheet.temporary_hp }}
                    </template>
                    <span aria-hidden="true">/</span>
                    <CalculationBreakdown
                      label="Maximum HP"
                      :calculation="character.sheet.hp_calculation"
                      :activator-label="String(character.sheet.max_hp)"
                    />
                  </div>
                </div>
                <div
                  v-if="canEdit"
                  class="hp-actions"
                  @click.stop
                  @keydown.stop
                >
                  <v-menu>
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon="mdi-dots-vertical"
                        size="small"
                        variant="text"
                        aria-label="More HP options"
                      />
                    </template>
                    <v-list density="compact">
                      <v-list-item
                        prepend-icon="mdi-shield-plus-outline"
                        title="Add temporary HP"
                        @click="openHealthFor('temporary')"
                      />
                      <v-list-item
                        prepend-icon="mdi-tune-variant"
                        title="Advanced HP adjustment"
                        @click="openHealthFor('damage')"
                      />
                    </v-list>
                  </v-menu>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col
            cols="12"
            sm="6"
            lg="3"
          >
            <v-card class="profile-card">
              <v-card-text>
                <div class="text-overline">Armor class</div>
                <div class="text-h5 mt-3">
                  <CalculationBreakdown
                    label="Armor class"
                    :calculation="character.sheet.armor_class_calculation"
                    :activator-label="
                      String(character.sheet.armor_class_calculation.value)
                    "
                  />
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col
            cols="12"
            sm="6"
            lg="3"
          >
            <v-card class="profile-card">
              <v-card-text>
                <div class="text-overline">Initiative bonus</div>
                <div class="text-h5">
                  <CalculationBreakdown
                    label="Initiative bonus"
                    :calculation="character.sheet.initiative"
                    :activator-label="signed(character.sheet.initiative.value)"
                  />
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col
            cols="12"
            sm="6"
            lg="3"
          >
            <v-card class="profile-card">
              <v-card-text>
                <div class="text-overline">Proficiency bonus</div>
                <div class="text-h5">
                  <CalculationBreakdown
                    label="Proficiency bonus"
                    :calculation="character.sheet.proficiency_bonus_calculation"
                    :activator-label="signed(character.sheet.proficiency_bonus)"
                  />
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="12">
        <v-card class="mb-4">
          <v-card-title class="d-flex align-center">
            Resources
            <v-spacer />
            <v-btn
              v-if="canEdit"
              size="small"
              :prepend-icon="
                character.has_inspiration ? 'mdi-star' : 'mdi-star-outline'
              "
              @click="toggleInspiration"
            >
              {{
                character.has_inspiration ? "Spend inspiration" : "Award inspiration"
              }}
            </v-btn>
            <v-btn
              v-if="canEdit"
              class="ml-2"
              size="small"
              @click="openShortRest"
            >
              Short rest
            </v-btn>
            <v-btn
              v-if="canEdit"
              class="ml-2"
              size="small"
              @click="takeRest('long')"
            >
              Long rest
            </v-btn>
          </v-card-title>
          <v-card-text>
            <p class="mb-3">
              Inspiration:
              <strong>
                {{ character.has_inspiration ? "Available" : "Not available" }}
              </strong>
              <span class="ml-4">
                Spell attack:
                <strong>{{ signed(character.sheet.spell_attack) }}</strong>
              </span>
              <span class="ml-4">
                Spell save DC:
                <strong>{{ character.sheet.spell_save_dc }}</strong>
              </span>
            </p>
            <v-table
              density="compact"
              class="a11y-table"
            >
              <caption class="visually-hidden">Spell slot availability</caption>
              <thead>
                <tr>
                  <th scope="col">Slot</th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    Current
                  </th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    Maximum
                  </th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(pool, level) in character.sheet.spell_slot_pools"
                  :key="level"
                >
                  <th scope="row">
                    {{
                      String(level).startsWith("pact-")
                        ? `Pact level ${String(level).slice(5)}`
                        : `Level ${level}`
                    }}
                  </th>
                  <td class="a11y-number">{{ pool.current }}</td>
                  <td class="a11y-number">{{ pool.maximum }}</td>
                  <td>
                    {{
                      pool.adjustment
                        ? `Class ${pool.calculated}, adjustment ${signed(pool.adjustment)}`
                        : `Class ${pool.calculated}`
                    }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
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
              class="a11y-table"
            >
              <caption class="visually-hidden">{{ character.name }} inventory</caption>
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    Quantity
                  </th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    Weight
                  </th>
                  <th
                    scope="col"
                    class="a11y-number"
                  >
                    Value
                  </th>
                  <th
                    scope="col"
                    class="text-right"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="entry in inventoryRows"
                  :key="entry.item_id"
                >
                  <th scope="row">{{ entry.name }}</th>
                  <td class="a11y-number">{{ entry.quantity.toLocaleString() }}</td>
                  <td class="a11y-number">
                    {{
                      entry.item?.equipment.weight_amount
                        ? `${entry.item.equipment.weight_amount} ${entry.item.equipment.weight_unit}`
                        : "—"
                    }}
                  </td>
                  <td class="a11y-number">
                    {{
                      entry.item?.equipment.cost_amount
                        ? `${entry.item.equipment.cost_amount} ${displayCoin(entry.item.equipment.cost_currency)}`
                        : "—"
                    }}
                  </td>
                  <td class="text-right">
                    <v-menu v-if="canAct">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          icon="mdi-dots-vertical"
                          size="small"
                          variant="text"
                          :aria-label="`Actions for ${entry.name}`"
                        />
                      </template>
                      <v-list density="compact">
                        <v-list-item
                          v-if="
                            entry.item?.equipment.category === 'weapon' ||
                            entry.item?.equipment.category === 'armor'
                          "
                          title="Equip"
                          @click="equipItem(entry)"
                        />
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
        <v-card class="mt-4">
          <v-card-title class="d-flex align-center">
            Equipment &amp; active effects
            <v-spacer />
            <v-btn
              v-if="canEdit"
              size="small"
              prepend-icon="mdi-plus"
              @click="openEffect"
            >
              Add effect
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-table
              v-if="character.loadout.length"
              density="compact"
              class="a11y-table mb-4"
            >
              <caption class="visually-hidden">Character equipment</caption>
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th scope="col">Slot</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in character.loadout"
                  :key="item.id"
                >
                  <th scope="row">{{ item.name }}</th>
                  <td>{{ displayName(item.slot) }}</td>
                  <td>{{ item.equipped ? "Equipped" : "Carried" }}</td>
                </tr>
              </tbody>
            </v-table>
            <v-table
              v-if="character.effects.length"
              density="compact"
              class="a11y-table"
            >
              <caption class="visually-hidden">Character active effects</caption>
              <thead>
                <tr>
                  <th scope="col">Effect</th>
                  <th scope="col">Duration</th>
                  <th scope="col">Modifiers and reminder</th>
                  <th
                    v-if="canEdit"
                    scope="col"
                  >
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="effect in character.effects"
                  :key="effect.id"
                >
                  <th scope="row">
                    {{ effect.name }}
                    <span v-if="effect.source">· {{ effect.source }}</span>
                  </th>
                  <td>{{ effect.duration || displayName(effect.expires_on_rest) }}</td>
                  <td>
                    {{
                      effect.modifiers
                        .map(
                          (modifier) =>
                            `${modifier.label || displayName(modifier.target)} ${signed(modifier.value)}`,
                        )
                        .join(" · ") ||
                      effect.reminder ||
                      "—"
                    }}
                  </td>
                  <td v-if="canEdit">
                    <v-btn
                      size="small"
                      variant="text"
                      :aria-label="`${effect.enabled ? 'Deactivate' : 'Activate'} ${effect.name}`"
                      @click="toggleEffect(effect)"
                    >
                      {{ effect.enabled ? "Deactivate" : "Activate" }}
                    </v-btn>
                    <v-btn
                      size="small"
                      variant="text"
                      color="error"
                      :aria-label="`Remove ${effect.name}`"
                      @click="deleteEffect(effect)"
                    >
                      Remove
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </v-table>
            <span
              v-if="!character.loadout.length && !character.effects.length"
              class="text-medium-emphasis"
            >
              No equipment is equipped and no effects are tracked.
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
        <v-expansion-panels
          class="mt-4"
          variant="accordion"
        >
          <v-expansion-panel :title="`Notes (${character.notes.length})`">
            <v-expansion-panel-text>
              <v-list density="compact">
                <v-list-item
                  v-for="note in character.notes"
                  :key="note.id"
                  :title="note.title || 'Note'"
                  :subtitle="note.body"
                />
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel :title="`Features & feats (${character.features.length})`">
            <v-expansion-panel-text>
              <v-list density="compact">
                <v-list-item
                  v-for="feature in character.features"
                  :key="feature.id"
                  :title="feature.name"
                  :subtitle="feature.description || feature.notes"
                />
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel :title="`Spells (${character.spells.length})`">
            <v-expansion-panel-text>
              <v-list density="compact">
                <v-list-item
                  v-for="spell in character.spells"
                  :key="spell.id"
                  :title="`${spell.name} · level ${spell.level}`"
                  :subtitle="spell.description || spell.notes"
                >
                  <template #append>
                    <v-btn
                      v-if="canEdit"
                      size="small"
                      variant="text"
                      :disabled="spell.level > 0 && !spell.prepared"
                      :aria-label="`Record casting ${spell.name}`"
                      @click="openSpellCast(spell)"
                    >
                      Cast
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel :title="`Companions (${character.companions.length})`">
            <v-expansion-panel-text>
              <v-list density="compact">
                <v-list-item
                  v-for="companion in character.companions"
                  :key="companion.id"
                  :title="companion.name"
                  :subtitle="`AC ${companion.armor_class} · HP ${companion.current_hp}/${companion.max_hp} · ${companion.speed}`"
                />
              </v-list>
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
                <span>{{ activityDescription(transaction) }}</span>
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
          <v-number-input
            v-model.number="grantQuantity"
            control-variant="split"
            :min="1"
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
              <v-col
                cols="12"
                sm="6"
              >
                <v-select
                  v-model="denomination"
                  :items="denominations"
                  label="Source denomination"
                />
                <v-number-input
                  v-model.number="amount"
                  control-variant="split"
                  :min="1"
                  label="Source coins"
                />
              </v-col>
              <v-col
                cols="12"
                sm="6"
              >
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
      v-model="effectOpen"
      max-width="560"
    >
      <v-card title="Add active effect">
        <v-card-text>
          <v-text-field
            v-model="effectName"
            label="Effect name"
          />
          <v-text-field
            v-model="effectSource"
            label="Source (optional)"
          />
          <v-text-field
            v-model="effectDuration"
            label="Duration or expiry reminder"
          />
          <v-select
            v-model="effectTarget"
            :items="effectTargets"
            label="Modifier target"
          />
          <v-number-input
            v-model.number="effectValue"
            control-variant="split"
            :min="-99"
            :max="99"
            :step="1"
            label="Numeric modifier (0 for reminder only)"
          />
          <v-textarea
            v-model="effectReminder"
            label="Reminder (conditional or dice effects)"
            rows="2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="effectOpen = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!effectName.trim()"
            @click="saveEffect"
          >
            Add effect
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="shortRestOpen"
      max-width="460"
    >
      <v-card title="Short rest">
        <v-card-text>
          <p class="mb-4">
            Enter current HP after spending Hit Dice. Hoard does not roll Hit Dice.
          </p>
          <v-number-input
            v-model.number="shortRestHp"
            control-variant="split"
            :min="0"
            :max="character?.sheet.max_hp ?? 1"
            label="Current HP after rest"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="shortRestOpen = false">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="takeRest('short')"
          >
            Record short rest
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="spellCastOpen"
      max-width="460"
    >
      <v-card :title="castingSpell ? `Cast ${castingSpell.name}` : 'Cast spell'">
        <v-card-text>
          <v-select
            v-model="castingSlot"
            :items="castingSlots"
            label="Spell slot"
            no-data-text="No eligible spell slots available"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="spellCastOpen = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!castingSlot"
            @click="confirmSpellCast"
          >
            Record casting
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
          <v-number-input
            v-model.number="itemActionQuantity"
            control-variant="split"
            :min="1"
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
      v-model="hpAdjustmentOpen"
      max-width="420"
    >
      <v-card title="Adjust HP">
        <v-card-text>
          <div class="text-body-1 mb-4">
            Current HP: {{ character.sheet.current_hp }} / {{ character.sheet.max_hp }}
          </div>
          <v-number-input
            v-model.number="healthAmount"
            control-variant="split"
            :min="1"
            label="Hit points"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="hpAdjustmentOpen = false">Cancel</v-btn>
          <v-btn
            color="error"
            :disabled="healthAmount < 1 || !canDamage"
            @click="submitHpAdjustment('damage')"
          >
            Damage
          </v-btn>
          <v-btn
            color="primary"
            :disabled="healthAmount < 1 || !canHeal"
            @click="submitHpAdjustment('healing')"
          >
            Heal
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="healthOpen"
      max-width="520"
    >
      <v-card title="Record HP change">
        <v-card-text>
          <v-select
            v-model="healthReason"
            label="Action"
            :items="[
              { title: 'Damage', value: 'damage' },
              { title: 'Healing', value: 'healing' },
              { title: 'Temporary HP change', value: 'temporary' },
              { title: 'Correction', value: 'correction' },
            ]"
          />
          <v-number-input
            v-if="healthReason !== 'correction'"
            v-model.number="healthAmount"
            control-variant="split"
            :min="1"
            label="Amount"
          />
          <template v-else>
            <v-number-input
              v-model.number="healthCurrent"
              control-variant="split"
              :min="0"
              label="Correct current HP"
            />
            <v-number-input
              v-model.number="healthTemporary"
              control-variant="split"
              :min="0"
              label="Correct temporary HP"
            />
          </template>
          <v-alert
            type="info"
            variant="tonal"
            class="mb-4"
          >
            {{ healthPreview }}
          </v-alert>
          <v-textarea
            v-model="healthDescription"
            label="Reason (optional)"
            rows="2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="healthOpen = false">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="saveHealth"
          >
            Record transaction
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
