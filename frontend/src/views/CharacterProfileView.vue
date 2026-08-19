<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
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
  previewCahImport,
  updateCharacter,
  type CahPreview,
  type Campaign,
  type Character,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";

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
const action = ref("item");
const itemId = ref<number>();
const destinationId = ref<number | null>(null);
const quantity = ref(1);
const denomination = ref("gp");
const amount = ref(1);
const receivedDenomination = ref("sp");
const receivedAmount = ref(10);
const description = ref("");
const editOpen = ref(false);
const importOpen = ref(false);
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
  0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000,
  120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
];
const inventoryCandidates = computed<PickerCandidate[]>(
  () =>
    character.value?.inventory.flatMap((entry) => {
      const item = items.value.find(
        (candidate) => candidate.id === entry.item_id,
      );
      return item ? [{ item, quantity: entry.quantity }] : [];
    }) ?? [],
);
const destinationOptions = computed(() => [
  { title: "Campaign store", value: null },
  ...characters.value
    .filter((candidate) => candidate.is_active && !candidate.is_archived)
    .map((candidate) => ({ title: candidate.name, value: candidate.id })),
]);
const canAct = computed(
  () =>
    ownCharacter.value &&
    character.value?.is_active &&
    !character.value.is_archived,
);
const canEdit = computed(
  () => ownCharacter.value || campaign.value?.is_game_master,
);
const abilityScores = computed<[string, number, number][]>(() =>
  character.value
    ? [
        [
          "STR",
          character.value.strength,
          character.value.sheet.abilities.strength.modifier,
        ],
        [
          "DEX",
          character.value.dexterity,
          character.value.sheet.abilities.dexterity.modifier,
        ],
        [
          "CON",
          character.value.constitution,
          character.value.sheet.abilities.constitution.modifier,
        ],
        [
          "INT",
          character.value.intelligence,
          character.value.sheet.abilities.intelligence.modifier,
        ],
        [
          "WIS",
          character.value.wisdom,
          character.value.sheet.abilities.wisdom.modifier,
        ],
        [
          "CHA",
          character.value.charisma,
          character.value.sheet.abilities.charisma.modifier,
        ],
      ]
    : [],
);
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
  skillGroups.value.filter((ability) =>
    ["wisdom", "charisma"].includes(ability.key),
  ),
]);
const displayName = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const signed = (value: number) => (value >= 0 ? `+${value}` : `${value}`);
const formatXp = (value: number) => `${value.toLocaleString()} XP`;
const experienceProgress = computed(() => {
  const level = character.value?.sheet.level ?? 1;
  const current = character.value?.experience ?? 0;
  const minimum = xpThresholds[level - 1] ?? 0;
  const maximum = xpThresholds[level];
  const progress = maximum
    ? Math.min(
        100,
        Math.max(0, ((current - minimum) / (maximum - minimum)) * 100),
      )
    : 100;
  return { current, level, maximum, minimum, progress };
});
const proficiencyLabel = (proficiency: string) =>
  ({ half: "Half", proficient: "Proficient", expertise: "Expertise" })[
    proficiency
  ] ?? "";
const proficiencyClass = (proficiency: string) =>
  `proficiency-bonus proficiency-bonus--${proficiency}`;
const importChanges = computed(() => {
  if (!character.value || !importPreview.value) return [];
  const current: Record<string, unknown> = {
    name: character.value.name,
    race: character.value.race,
    base_hp: character.value.sheet.base_hp,
    proficiency_bonus_adjustment:
      character.value.sheet.proficiency_bonus_adjustment,
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
            current:
              character.value?.sheet.skills[skill]?.proficiency ?? "none",
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
    const [nextCampaign, visible, own, nextItems] = await Promise.all([
      getCampaign(campaignId),
      getCharacters(campaignId),
      getMyCharacters(campaignId),
      getItems(campaignId),
    ]);
    campaign.value = nextCampaign;
    characters.value = visible;
    character.value =
      visible.find((candidate) => candidate.id === characterId) ??
      own.find((candidate) => candidate.id === characterId);
    ownCharacter.value = own.some((candidate) => candidate.id === characterId);
    items.value = nextItems;
    if (!character.value) await router.replace(`/c/${campaignId}/characters`);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load character profile.";
  }
}

watch(inventoryCandidates, (candidates) => {
  if (!candidates.some((candidate) => candidate.item.id === itemId.value))
    itemId.value = undefined;
});

async function submit(): Promise<void> {
  if (!character.value) return;
  try {
    if (action.value === "item" && itemId.value)
      await createInventoryTransaction(campaignId, {
        from_character_id: character.value.id,
        to_character_id: destinationId.value,
        item_id: itemId.value,
        quantity: quantity.value,
        description: description.value,
      });
    if (action.value === "money")
      await createMoneyTransfer(campaignId, {
        from_character_id: character.value.id,
        to_character_id: destinationId.value,
        amounts: { [denomination.value]: amount.value },
        description: description.value,
      });
    if (action.value === "exchange")
      await createMoneyExchange(campaignId, {
        character_id: character.value.id,
        given: { [denomination.value]: amount.value },
        received: { [receivedDenomination.value]: receivedAmount.value },
        description: description.value,
      });
    notice.value = "Saved to the ledger.";
    description.value = "";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to complete this action.";
  }
}

function scrollToActions(): void {
  document
    .getElementById("character-actions")
    ?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function openEdit(): void {
  if (!character.value) return;
  editName.value = character.value.name;
  editRace.value = character.value.race;
  editClass.value = character.value.class;
  editBaseHp.value = character.value.sheet.base_hp;
  editProficiencyAdjustment.value =
    character.value.sheet.proficiency_bonus_adjustment;
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
    editOpen.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to update character.";
  }
}

async function archive(): Promise<void> {
  if (!character.value) return;
  try {
    await archiveCharacter(campaignId, character.value.id);
    await router.replace(`/c/${campaignId}/characters`);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to archive character.";
  }
}

async function previewImport(): Promise<void> {
  if (!importFile.value) return;
  try {
    importPreview.value = await previewCahImport(campaignId, importFile.value);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to read CAH file.";
  }
}

async function commitImport(): Promise<void> {
  if (!character.value || !importPreview.value) return;
  try {
    await commitCahImport(
      campaignId,
      importPreview.value.token,
      character.value.id,
    );
    importOpen.value = false;
    importPreview.value = undefined;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to import character.";
  }
}

onMounted(load);
</script>

<template>
  <v-container class="page-shell" v-if="character">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Character profile</div>
        <h1>{{ character.name }}</h1>
        <p>{{ character.race }} · {{ character.class }}</p>
      </div>
      <div class="d-flex ga-2">
        <v-btn v-if="canEdit" @click="openEdit">Edit</v-btn>
        <v-btn v-if="ownCharacter" variant="tonal" @click="importOpen = true"
          >Import CAH</v-btn
        >
        <v-btn
          :to="`/c/${campaignId}/characters`"
          prepend-icon="mdi-account-group-outline"
          >Roster</v-btn
        >
      </div>
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
      >{{ error }}</v-alert
    >
    <v-alert
      v-if="notice"
      type="success"
      closable
      class="mb-4"
      @click:close="notice = ''"
      >{{ notice }}</v-alert
    >
    <v-row
      ><v-col cols="12" :lg="canAct ? 7 : 12"
        ><v-card
          ><v-card-text
            ><v-row
              ><v-col cols="12" sm="7"
                ><div class="text-overline">
                  Level {{ experienceProgress.level }}
                </div>
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
                  <span v-if="experienceProgress.maximum">{{
                    formatXp(experienceProgress.maximum)
                  }}</span
                  ><span v-else>Maximum level</span>
                </div></v-col
              ><v-col cols="12" sm="5"
                ><div class="text-overline">Total wealth</div>
                <div class="text-h4">
                  {{ character.money.gold_value }} ¤
                </div></v-col
              ></v-row
            ><v-divider class="my-4" />
            <div class="money-line">
              {{ character.money.pp }} pp · {{ character.money.gp }} gp ·
              {{ character.money.ep }} ep · {{ character.money.sp }} sp ·
              {{ character.money.cp }} cp
            </div>
            <v-divider class="my-4" />
            <v-row>
              <v-col cols="6"
                ><div class="text-overline">Max HP</div>
                <div class="text-h5">{{ character.sheet.max_hp }}</div></v-col
              >
              <v-col cols="6"
                ><div class="text-overline">Proficiency</div>
                <div class="text-h5">
                  +{{ character.sheet.proficiency_bonus }}
                </div></v-col
              >
            </v-row>
            <v-divider class="my-4" /><v-row
              ><v-col
                v-for="[label, score, modifier] in abilityScores"
                :key="label"
                cols="4"
                sm="2"
                ><div class="ability">
                  <strong>{{ signed(modifier) }}</strong
                  ><span>{{ label }} · {{ score }}</span>
                </div></v-col
              ></v-row
            ></v-card-text
          ></v-card
        >
        <v-card class="mt-4"
          ><v-card-title>Saving throws</v-card-title
          ><v-card-text
            ><v-row dense
              ><v-col
                v-for="ability in abilityGroups"
                :key="ability.key"
                cols="4"
                sm="2"
                ><div class="ability">
                  <v-tooltip
                    v-if="ability.save.proficient"
                    :text="proficiencyLabel('proficient')"
                    location="top"
                  >
                    <template #activator="{ props }">
                      <span
                        v-bind="props"
                        :class="proficiencyClass('proficient')"
                      >
                        {{ signed(ability.save.bonus) }}
                      </span>
                    </template>
                  </v-tooltip>
                  <strong v-else>{{ signed(ability.save.bonus) }}</strong>
                  <span>{{ ability.abbreviation }} save</span>
                </div></v-col
              ></v-row
            ></v-card-text
          ></v-card
        >
        <v-card class="mt-4"
          ><v-card-title>Skills</v-card-title
          ><v-card-text
            ><v-row dense
              ><v-col
                v-for="(column, columnIndex) in skillColumns"
                :key="columnIndex"
                cols="12"
                sm="6"
                ><div
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
                    <v-tooltip
                      v-if="skill.proficiency !== 'none'"
                      :text="proficiencyLabel(skill.proficiency)"
                      location="top"
                    >
                      <template #activator="{ props }">
                        <span
                          v-bind="props"
                          :class="proficiencyClass(skill.proficiency)"
                          ><span
                            v-if="skill.proficiency === 'expertise'"
                            class="expertise-sparkle"
                            aria-hidden="true"
                            >✦</span
                          >{{ signed(skill.bonus) }}</span
                        >
                      </template>
                    </v-tooltip>
                    <strong v-else>{{ signed(skill.bonus) }}</strong>
                    <span>{{ displayName(skill.name) }}</span>
                  </div>
                </div></v-col
              ></v-row
            ></v-card-text
          ></v-card
        ><v-card class="mt-4"
          ><v-card-title>Inventory</v-card-title
          ><v-card-text
            ><v-chip
              v-for="entry in character.inventory"
              :key="entry.item_id"
              class="mr-2 mb-2"
              >{{ entry.quantity }} × {{ entry.name }}</v-chip
            ><span
              v-if="!character.inventory.length"
              class="text-medium-emphasis"
              >No inventory recorded.</span
            ></v-card-text
          ></v-card
        ></v-col
      >
      <v-col id="character-actions" cols="12" lg="5" v-if="canAct"
        ><v-card
          ><v-card-title>Actions</v-card-title
          ><v-card-text
            ><v-tabs v-model="action" grow
              ><v-tab value="item">Move</v-tab><v-tab value="money">Send</v-tab
              ><v-tab value="exchange">Exchange</v-tab></v-tabs
            ><v-window v-model="action" class="pt-4"
              ><v-window-item value="item"
                ><ItemPickerDialog
                  v-model="itemId"
                  :candidates="inventoryCandidates"
                  label="Item to move"
                  no-data-text="No recorded items." /><v-select
                  v-model="destinationId"
                  :items="destinationOptions"
                  label="Move to" /><v-text-field
                  v-model.number="quantity"
                  type="number"
                  min="1"
                  label="Quantity" /></v-window-item
              ><v-window-item value="money"
                ><v-select
                  v-model="destinationId"
                  :items="destinationOptions"
                  label="Send to" /><v-row
                  ><v-col
                    ><v-select
                      v-model="denomination"
                      :items="denominations"
                      label="Denomination" /></v-col
                  ><v-col
                    ><v-text-field
                      v-model.number="amount"
                      type="number"
                      min="1"
                      label="Amount" /></v-col></v-row></v-window-item
              ><v-window-item value="exchange"
                ><v-row
                  ><v-col
                    ><v-select
                      v-model="denomination"
                      :items="denominations"
                      label="Give" /><v-text-field
                      v-model.number="amount"
                      type="number"
                      min="1"
                      label="Amount" /></v-col
                  ><v-col
                    ><v-select
                      v-model="receivedDenomination"
                      :items="denominations"
                      label="Receive" /><v-text-field
                      v-model.number="receivedAmount"
                      type="number"
                      min="1"
                      label="Amount" /></v-col></v-row></v-window-item></v-window
            ><v-textarea
              v-model="description"
              label="Note (optional)"
              rows="2"
            /><v-btn
              block
              color="primary"
              :disabled="
                (action === 'item' && !itemId) ||
                (action !== 'exchange' && destinationId === undefined)
              "
              @click="submit"
              >{{
                action === "item"
                  ? "Move item"
                  : action === "money"
                    ? "Send money"
                    : "Exchange money"
              }}</v-btn
            ></v-card-text
          ></v-card
        ></v-col
      ></v-row
    >
    <v-tooltip v-if="canAct" text="Jump to actions" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          class="actions-fab"
          color="primary"
          icon="mdi-arrow-down"
          size="large"
          aria-label="Jump to actions"
          @click="scrollToActions"
        />
      </template>
    </v-tooltip>
    <v-dialog v-model="editOpen" max-width="720">
      <v-card title="Edit character">
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="4"
              ><v-text-field v-model="editName" label="Name"
            /></v-col>
            <v-col cols="12" sm="4"
              ><v-text-field v-model="editRace" label="Race"
            /></v-col>
            <v-col cols="12" sm="4"
              ><v-text-field v-model="editClass" label="Class"
            /></v-col>
          </v-row>
          <v-row>
            <v-col cols="12" sm="4"
              ><v-text-field
                v-model.number="editBaseHp"
                type="number"
                min="1"
                label="Base HP"
            /></v-col>
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
          <v-btn color="error" variant="text" @click="archive">Archive</v-btn>
          <v-spacer />
          <v-btn @click="editOpen = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveProfile">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="importOpen" max-width="560">
      <v-card title="Import 5e Companion character">
        <v-card-text>
          <v-file-input
            v-model="importFile"
            accept=".cah,application/json"
            label="CAH export"
            @update:model-value="importPreview = undefined"
          />
          <v-btn :disabled="!importFile" @click="previewImport"
            >Preview import</v-btn
          >
          <template v-if="importPreview">
            <v-card variant="tonal" class="mt-4">
              <v-card-title class="text-subtitle-1"
                >Changes to apply</v-card-title
              >
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
              <div v-for="warning in importPreview.warnings" :key="warning">
                {{ warning }}
              </div>
            </v-alert>
          </template>
        </v-card-text>
        <v-card-actions
          ><v-spacer /><v-btn @click="importOpen = false">Cancel</v-btn
          ><v-btn
            color="primary"
            :disabled="!importPreview"
            @click="commitImport"
            >Replace reference sheet</v-btn
          ></v-card-actions
        >
      </v-card>
    </v-dialog>
  </v-container>
</template>
