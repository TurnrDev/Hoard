<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import ItemPickerDialog from '../components/ItemPickerDialog.vue'
import { createItem, getCampaign, getItems, getTransactions, postAction, reverseTransaction, type Campaign, type EquipmentMetadata, type Item, type LedgerTransaction } from '../api'
import { itemSummary, type PickerCandidate } from '../itemPicker'

const route = useRoute()
const campaignId = Number(route.params.id)
const campaign = ref<Campaign>()
const items = ref<Item[]>([])
const transactions = ref<LedgerTransaction[]>([])
const error = ref('')
const notice = ref('')
const tab = ref('characters')
const catalogueSearch = ref('')
const actionDialog = ref(false)
const action = ref('grant-loot')
const selectedCharacter = ref<number>()
const selectedRecipient = ref<number>()
const selectedItem = ref<number>()
const quantity = ref(1)
const denomination = ref('gp')
const coinAmount = ref(1)
const receivedDenomination = ref('sp')
const receivedCoinAmount = ref(10)
const xpAmount = ref(10)
const description = ref('')
const itemDialog = ref(false)
const itemName = ref('')
const itemDescription = ref('')
const itemMetadata = ref<Partial<EquipmentMetadata>>({})
const reverseDialog = ref(false)
const transactionToReverse = ref<LedgerTransaction>()

const isGM = computed(() => campaign.value?.is_game_master ?? false)
const characterOptions = computed(() => campaign.value?.characters.map((character) => ({ title: character.name, value: character.id })) ?? [])
const catalogueCandidates = computed<PickerCandidate[]>(() => items.value.map((item) => ({ item })))
const sourceInventoryCandidates = computed<PickerCandidate[]>(() => {
  const character = campaign.value?.characters.find((candidate) => candidate.id === selectedCharacter.value)
  return character?.inventory.flatMap((entry) => {
    const item = items.value.find((candidate) => candidate.id === entry.item_id)
    return item ? [{ item, quantity: entry.quantity }] : []
  }) ?? []
})
const actionCandidates = computed(() => action.value === 'transfer-item' ? sourceInventoryCandidates.value : catalogueCandidates.value)
const filteredCatalogue = computed(() => {
  const query = catalogueSearch.value.trim().toLocaleLowerCase()
  if (!query) return items.value
  return items.value.filter((item) => [item.name, item.description, item.source_system, item.equipment.source_book, item.equipment.category, item.equipment.item_type]
    .filter((value): value is string => Boolean(value)).join(' ').toLocaleLowerCase().includes(query))
})
const actions = [
  { title: 'Grant loot', value: 'grant-loot' }, { title: 'Transfer item', value: 'transfer-item' },
  { title: 'Grant coins', value: 'grant-coins' }, { title: 'Spend coins', value: 'spend-coins' },
  { title: 'Exchange coins', value: 'exchange-coins' }, { title: 'Preview shared XP', value: 'preview-shared-xp' },
  { title: 'Award shared XP', value: 'award-shared-xp' },
]

function uniqueAccountNames(transaction: LedgerTransaction, direction: 'from' | 'to'): string {
  const isFrom = direction === 'from'
  return [...new Set(transaction.entries.filter((entry) => isFrom ? entry.amount < 0 : entry.amount > 0).map((entry) => entry.account_name))].join(', ')
}

function transactionAmount(transaction: LedgerTransaction): string {
  const positiveEntries = transaction.entries.filter((entry) => entry.amount > 0)
  return positiveEntries.map((entry) => `${entry.amount} ${entry.item_name ?? entry.denomination ?? 'XP'}`).join(' · ')
}

async function refresh(): Promise<void> {
  error.value = ''
  try {
    const [nextCampaign, nextItems, history] = await Promise.all([getCampaign(campaignId), getItems(campaignId), getTransactions(campaignId)])
    campaign.value = nextCampaign
    items.value = nextItems
    transactions.value = history.results
  } catch (exception) { error.value = exception instanceof Error ? exception.message : 'Unable to load campaign.' }
}

onMounted(refresh)

function openAction(): void {
  selectedCharacter.value = campaign.value?.characters[0]?.id
  selectedRecipient.value = campaign.value?.characters[0]?.id
  selectedItem.value = undefined
  description.value = ''
  actionDialog.value = true
}

async function submitAction(): Promise<void> {
  try {
    const coins = { [denomination.value]: coinAmount.value }
    let payload: object
    if (action.value === 'grant-loot') payload = { recipient_id: selectedRecipient.value, item_id: selectedItem.value, quantity: quantity.value, description: description.value }
    else if (action.value === 'transfer-item') payload = { source_id: selectedCharacter.value, recipient_id: selectedRecipient.value, item_id: selectedItem.value, quantity: quantity.value, description: description.value }
    else if (action.value === 'grant-coins' || action.value === 'spend-coins') payload = { character_id: selectedCharacter.value, coins, description: description.value }
    else if (action.value === 'exchange-coins') payload = { character_id: selectedCharacter.value, given: coins, received: { [receivedDenomination.value]: receivedCoinAmount.value }, description: description.value }
    else payload = { amount: xpAmount.value, description: description.value }
    const result = await postAction(campaignId, action.value, payload) as { per_character?: number; dry_run?: boolean }
    notice.value = result.per_character ? `${result.dry_run ? 'Preview:' : 'Awarded'} ${result.per_character} XP per character.` : 'Transaction posted.'
    actionDialog.value = false
    await refresh()
  } catch (exception) { error.value = exception instanceof Error ? exception.message : 'Action failed.' }
}

async function submitItem(): Promise<void> {
  try {
    await createItem(campaignId, itemName.value, itemDescription.value, itemMetadata.value)
    itemDialog.value = false
    itemName.value = ''
    itemDescription.value = ''
    itemMetadata.value = {}
    await refresh()
  } catch (exception) { error.value = exception instanceof Error ? exception.message : 'Could not create item.' }
}

async function reverse(): Promise<void> {
  if (!transactionToReverse.value) return
  try { await reverseTransaction(campaignId, transactionToReverse.value, description.value); reverseDialog.value = false; await refresh() }
  catch (exception) { error.value = exception instanceof Error ? exception.message : 'Could not reverse transaction.' }
}
</script>

<template>
  <v-container fluid class="pa-md-8">
    <v-alert v-if="error" type="error" closable class="mb-4" @click:close="error = ''">{{ error }}</v-alert><v-alert v-if="notice" type="success" closable class="mb-4" @click:close="notice = ''">{{ notice }}</v-alert>
    <template v-if="campaign">
      <div class="d-flex flex-wrap align-center justify-space-between mb-6 ga-4"><div><div class="text-overline text-secondary">Campaign</div><h1 class="text-h3">{{ campaign.name }}</h1></div><div class="d-flex ga-2"><v-btn v-if="isGM" color="primary" prepend-icon="mdi-controller" :to="`/campaigns/${campaignId}/gm`">GM controls</v-btn><v-btn v-if="isGM" prepend-icon="mdi-plus" @click="openAction">Post action</v-btn><v-btn prepend-icon="mdi-package-variant-plus" @click="itemDialog = true">New item</v-btn></div></div>
      <v-row class="mb-2"><v-col cols="12" md="4"><v-card><v-card-text><div class="text-overline">Shared XP</div><div class="text-h3">{{ campaign.shared_experience }}</div><div class="text-caption">per active player character</div></v-card-text></v-card></v-col><v-col cols="12" md="4"><v-card><v-card-text><div class="text-overline">Characters</div><div class="text-h3">{{ campaign.characters.length }}</div></v-card-text></v-card></v-col><v-col cols="12" md="4"><v-card><v-card-text><div class="text-overline">Role</div><div class="text-h5">{{ isGM ? 'Game master' : 'Player' }}</div></v-card-text></v-card></v-col></v-row>
      <v-tabs v-model="tab" color="primary"><v-tab value="characters">Characters</v-tab><v-tab value="items">Equipment</v-tab><v-tab value="history">Ledger</v-tab></v-tabs>
      <v-window v-model="tab" class="pt-4">
        <v-window-item value="characters"><v-row><v-col v-for="character in campaign.characters" :key="character.id" cols="12" md="6"><v-card><v-card-title>{{ character.name }} <v-chip size="small" class="ml-2">{{ character.race }} {{ character.class }}</v-chip></v-card-title><v-card-text><v-row dense><v-col cols="4"><strong>{{ character.experience }}</strong><br><span class="text-caption">XP</span></v-col><v-col cols="8"><strong>{{ character.money.gp }} gp</strong> · {{ character.money.sp }} sp · {{ character.money.cp }} cp<br><span class="text-caption">{{ character.money.gold_value }} gp total</span></v-col></v-row><v-divider class="my-3"/><div v-if="character.inventory.length"><v-chip v-for="entry in character.inventory" :key="entry.item_id" class="mr-2 mb-2">{{ entry.quantity }} × {{ entry.name }}</v-chip></div><span v-else class="text-medium-emphasis">No inventory recorded.</span></v-card-text></v-card></v-col></v-row></v-window-item>
        <v-window-item value="items"><v-text-field v-model="catalogueSearch" prepend-inner-icon="mdi-magnify" label="Search equipment" clearable/><div class="text-caption mb-3">{{ filteredCatalogue.length }} matching items</div><v-virtual-scroll :items="filteredCatalogue" :item-height="210" height="700"><template #default="{ item }"><v-card class="ma-2"><v-card-title>{{ item.name }}</v-card-title><v-card-subtitle>{{ itemSummary(item) || 'Campaign custom item' }}</v-card-subtitle><v-card-text><p class="catalogue-description">{{ item.description || 'No description.' }}</p><v-chip v-if="item.equipment.category" size="small" class="mr-1 mb-1">{{ item.equipment.category }}</v-chip><v-chip v-if="item.equipment.item_type" size="small" class="mr-1 mb-1">{{ item.equipment.item_type }}</v-chip><v-chip v-if="item.equipment.rarity" size="small" class="mr-1 mb-1">{{ item.equipment.rarity }}</v-chip><v-chip v-if="item.equipment.is_magic" size="small" class="mr-1 mb-1">magic</v-chip><v-chip v-if="item.equipment.requires_attunement" size="small" class="mr-1 mb-1">attunement</v-chip><div v-if="item.created_by_username" class="text-caption mt-2">Created by {{ item.created_by_username }}</div></v-card-text></v-card></template></v-virtual-scroll></v-window-item>
        <v-window-item value="history"><v-table><thead><tr><th>When</th><th>Ledger</th><th>From</th><th>To</th><th>Amount</th><th>Description</th><th></th></tr></thead><tbody><tr v-for="transaction in transactions" :key="`${transaction.ledger}-${transaction.id}`"><td>{{ new Date(transaction.created_at).toLocaleString() }}</td><td><v-chip size="small">{{ transaction.ledger }}</v-chip></td><td class="ledger-amount-negative">{{ uniqueAccountNames(transaction, 'from') }}</td><td class="ledger-amount-positive">{{ uniqueAccountNames(transaction, 'to') }}</td><td>{{ transactionAmount(transaction) }}</td><td>{{ transaction.description || '—' }} <span v-if="transaction.is_reversed" class="text-error">(reversed)</span></td><td><v-btn v-if="isGM && !transaction.is_reversed && !transaction.reversal_of_id" icon="mdi-undo" size="small" @click="transactionToReverse = transaction; description = ''; reverseDialog = true" /></td></tr></tbody></v-table></v-window-item>
      </v-window>
    </template><v-progress-circular v-else indeterminate color="primary" />

    <v-dialog v-model="itemDialog" max-width="700"><v-card title="Create campaign item"><v-card-text><v-text-field v-model="itemName" label="Name"/><v-textarea v-model="itemDescription" label="Description"/><v-row dense><v-col cols="6"><v-text-field v-model="itemMetadata.category" label="Category"/></v-col><v-col cols="6"><v-text-field v-model="itemMetadata.item_type" label="Type"/></v-col><v-col cols="6"><v-text-field v-model="itemMetadata.source_book" label="Source book"/></v-col><v-col cols="6"><v-text-field v-model="itemMetadata.rarity" label="Rarity"/></v-col><v-col cols="6"><v-text-field v-model="itemMetadata.cost_amount" label="Cost amount" type="number"/></v-col><v-col cols="6"><v-select v-model="itemMetadata.cost_currency" :items="['cp','sp','ep','gp','pp']" label="Cost currency" clearable/></v-col><v-col cols="6"><v-text-field v-model="itemMetadata.weight_amount" label="Weight" type="number"/></v-col><v-col cols="6"><v-text-field v-model="itemMetadata.weight_unit" label="Weight unit" placeholder="pounds"/></v-col><v-col cols="6"><v-select v-model="itemMetadata.is_magic" :items="[{title:'Unknown',value:null},{title:'Magic',value:true},{title:'Non-magic',value:false}]" label="Magic"/></v-col><v-col cols="6"><v-select v-model="itemMetadata.requires_attunement" :items="[{title:'Unknown',value:null},{title:'Required',value:true},{title:'Not required',value:false}]" label="Attunement"/></v-col></v-row></v-card-text><v-card-actions><v-spacer/><v-btn @click="itemDialog = false">Cancel</v-btn><v-btn color="primary" @click="submitItem">Create</v-btn></v-card-actions></v-card></v-dialog>
    <v-dialog v-model="actionDialog" max-width="700"><v-card title="Post campaign action"><v-card-text><v-select v-model="action" :items="actions" label="Action"/><v-select v-if="!action.includes('shared-xp')" v-model="selectedCharacter" :items="characterOptions" label="Character"/><v-select v-if="action === 'grant-loot' || action === 'transfer-item'" v-model="selectedRecipient" :items="characterOptions" label="Recipient"/><ItemPickerDialog v-if="action === 'grant-loot' || action === 'transfer-item'" v-model="selectedItem" :candidates="actionCandidates" :label="action === 'transfer-item' ? 'Item held by source character' : 'Item to grant'" :no-data-text="action === 'transfer-item' ? 'This character has no recorded items.' : 'No campaign items match.'"/><v-text-field v-if="action === 'grant-loot' || action === 'transfer-item'" v-model.number="quantity" type="number" min="1" label="Quantity"/><template v-if="action.includes('coins')"><v-select v-model="denomination" :items="['cp','sp','ep','gp','pp']" label="Given denomination"/><v-text-field v-model.number="coinAmount" type="number" min="1" label="Given amount"/><template v-if="action === 'exchange-coins'"><v-select v-model="receivedDenomination" :items="['cp','sp','ep','gp','pp']" label="Receive denomination"/><v-text-field v-model.number="receivedCoinAmount" type="number" min="1" label="Receive amount"/></template></template><v-text-field v-if="action.includes('shared-xp')" v-model.number="xpAmount" type="number" min="1" label="Total XP"/><v-textarea v-model="description" label="Description"/></v-card-text><v-card-actions><v-spacer/><v-btn @click="actionDialog = false">Cancel</v-btn><v-btn color="primary" :disabled="(action === 'grant-loot' || action === 'transfer-item') && !selectedItem" @click="submitAction">{{ action === 'preview-shared-xp' ? 'Preview' : 'Post' }}</v-btn></v-card-actions></v-card></v-dialog>
    <v-dialog v-model="reverseDialog" max-width="520"><v-card title="Reverse transaction"><v-card-text><v-textarea v-model="description" label="Reason"/></v-card-text><v-card-actions><v-spacer/><v-btn @click="reverseDialog = false">Cancel</v-btn><v-btn color="error" @click="reverse">Reverse</v-btn></v-card-actions></v-card></v-dialog>
  </v-container>
</template>

<style scoped>
.catalogue-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
