<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { createItem, getCampaign, getItems, getTransactions, postAction, reverseTransaction, type Campaign, type Item, type LedgerTransaction } from '../api'

const route = useRoute()
const campaignId = Number(route.params.id)
const campaign = ref<Campaign>()
const items = ref<Item[]>([])
const transactions = ref<LedgerTransaction[]>([])
const error = ref('')
const notice = ref('')
const tab = ref('characters')
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
const reverseDialog = ref(false)
const transactionToReverse = ref<LedgerTransaction>()

const isGM = computed(() => campaign.value?.is_game_master ?? false)
const characterOptions = computed(() => campaign.value?.characters.map((character) => ({ title: character.name, value: character.id })) ?? [])
const itemOptions = computed(() => items.value.map((item) => ({ title: item.name, value: item.id })))
const actions = [
  { title: 'Grant loot', value: 'grant-loot' }, { title: 'Transfer item', value: 'transfer-item' },
  { title: 'Grant coins', value: 'grant-coins' }, { title: 'Spend coins', value: 'spend-coins' },
  { title: 'Exchange coins', value: 'exchange-coins' }, { title: 'Preview shared XP', value: 'preview-shared-xp' },
  { title: 'Award shared XP', value: 'award-shared-xp' },
]

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
  selectedItem.value = items.value[0]?.id
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
  try { await createItem(campaignId, itemName.value, itemDescription.value); itemDialog.value = false; itemName.value = ''; itemDescription.value = ''; await refresh() }
  catch (exception) { error.value = exception instanceof Error ? exception.message : 'Could not create item.' }
}

async function reverse(): Promise<void> {
  if (!transactionToReverse.value) return
  try { await reverseTransaction(campaignId, transactionToReverse.value, description.value); reverseDialog.value = false; await refresh() }
  catch (exception) { error.value = exception instanceof Error ? exception.message : 'Could not reverse transaction.' }
}
</script>

<template>
  <v-container fluid class="pa-md-8">
    <v-alert v-if="error" type="error" closable class="mb-4" @click:close="error = ''">{{ error }}</v-alert>
    <v-alert v-if="notice" type="success" closable class="mb-4" @click:close="notice = ''">{{ notice }}</v-alert>
    <template v-if="campaign">
      <div class="d-flex flex-wrap align-center justify-space-between mb-6 ga-4">
        <div><div class="text-overline text-secondary">Campaign</div><h1 class="text-h3">{{ campaign.name }}</h1></div>
        <div class="d-flex ga-2"><v-btn v-if="isGM" color="primary" prepend-icon="mdi-plus" @click="openAction">Post action</v-btn><v-btn prepend-icon="mdi-package-variant-plus" @click="itemDialog = true">New item</v-btn></div>
      </div>
      <v-row class="mb-2"><v-col cols="12" md="4"><v-card><v-card-text><div class="text-overline">Shared XP</div><div class="text-h3">{{ campaign.shared_experience }}</div><div class="text-caption">per active player character</div></v-card-text></v-card></v-col><v-col cols="12" md="4"><v-card><v-card-text><div class="text-overline">Characters</div><div class="text-h3">{{ campaign.characters.length }}</div></v-card-text></v-card></v-col><v-col cols="12" md="4"><v-card><v-card-text><div class="text-overline">Role</div><div class="text-h5">{{ isGM ? 'Game master' : 'Player' }}</div></v-card-text></v-card></v-col></v-row>
      <v-tabs v-model="tab" color="primary"><v-tab value="characters">Characters</v-tab><v-tab value="items">Items</v-tab><v-tab value="history">Ledger</v-tab></v-tabs>
      <v-window v-model="tab" class="pt-4">
        <v-window-item value="characters"><v-row><v-col v-for="character in campaign.characters" :key="character.id" cols="12" md="6"><v-card><v-card-title>{{ character.name }} <v-chip size="small" class="ml-2">{{ character.race }} {{ character.class }}</v-chip></v-card-title><v-card-text><v-row dense><v-col cols="4"><strong>{{ character.experience }}</strong><br><span class="text-caption">XP</span></v-col><v-col cols="8"><strong>{{ character.money.gp }} gp</strong> · {{ character.money.sp }} sp · {{ character.money.cp }} cp<br><span class="text-caption">{{ character.money.gold_value }} gp total</span></v-col></v-row><v-divider class="my-3"/><div v-if="character.inventory.length"><v-chip v-for="entry in character.inventory" :key="entry.item_id" class="mr-2 mb-2">{{ entry.quantity }} × {{ entry.name }}</v-chip></div><span v-else class="text-medium-emphasis">No inventory recorded.</span></v-card-text></v-card></v-col></v-row></v-window-item>
        <v-window-item value="items"><v-data-table :headers="[{title:'Item',key:'name'},{title:'Source',key:'source_system'},{title:'Creator',key:'created_by_id'}]" :items="items"><template #item.source_system="{ item }"><v-chip size="small">{{ item.source_system ?? 'Campaign custom' }}</v-chip></template><template #item.created_by_id="{ item }">{{ item.created_by_id ?? 'Upstream' }}</template></v-data-table></v-window-item>
        <v-window-item value="history"><v-table><thead><tr><th>When</th><th>Ledger</th><th>Description</th><th>Entries</th><th></th></tr></thead><tbody><tr v-for="transaction in transactions" :key="`${transaction.ledger}-${transaction.id}`"><td>{{ new Date(transaction.created_at).toLocaleString() }}</td><td><v-chip size="small">{{ transaction.ledger }}</v-chip></td><td>{{ transaction.description || '—' }} <span v-if="transaction.is_reversed" class="text-error">(reversed)</span></td><td><span v-for="entry in transaction.entries" :key="entry.account_id + String(entry.amount)" class="mr-2" :class="entry.amount > 0 ? 'ledger-amount-positive' : 'ledger-amount-negative'">{{ entry.amount > 0 ? '+' : '' }}{{ entry.amount }} {{ entry.item_name ?? entry.denomination ?? 'XP' }}</span></td><td><v-btn v-if="isGM && !transaction.is_reversed && !transaction.reversal_of_id" icon="mdi-undo" size="small" @click="transactionToReverse = transaction; description = ''; reverseDialog = true" /></td></tr></tbody></v-table></v-window-item>
      </v-window>
    </template>
    <v-progress-circular v-else indeterminate color="primary" />

    <v-dialog v-model="itemDialog" max-width="520"><v-card title="Create campaign item"><v-card-text><v-text-field v-model="itemName" label="Name"/><v-textarea v-model="itemDescription" label="Description"/></v-card-text><v-card-actions><v-spacer/><v-btn @click="itemDialog = false">Cancel</v-btn><v-btn color="primary" @click="submitItem">Create</v-btn></v-card-actions></v-card></v-dialog>
    <v-dialog v-model="actionDialog" max-width="620"><v-card title="Post campaign action"><v-card-text><v-select v-model="action" :items="actions" label="Action"/><v-select v-if="!action.includes('shared-xp')" v-model="selectedCharacter" :items="characterOptions" label="Character"/><v-select v-if="action === 'grant-loot' || action === 'transfer-item'" v-model="selectedRecipient" :items="characterOptions" label="Recipient"/><v-select v-if="action === 'grant-loot' || action === 'transfer-item'" v-model="selectedItem" :items="itemOptions" label="Item"/><v-text-field v-if="action === 'grant-loot' || action === 'transfer-item'" v-model.number="quantity" type="number" min="1" label="Quantity"/><template v-if="action.includes('coins')"><v-select v-model="denomination" :items="['cp','sp','ep','gp','pp']" label="Given denomination"/><v-text-field v-model.number="coinAmount" type="number" min="1" label="Given amount"/><template v-if="action === 'exchange-coins'"><v-select v-model="receivedDenomination" :items="['cp','sp','ep','gp','pp']" label="Receive denomination"/><v-text-field v-model.number="receivedCoinAmount" type="number" min="1" label="Receive amount"/></template></template><v-text-field v-if="action.includes('shared-xp')" v-model.number="xpAmount" type="number" min="1" label="Total XP"/><v-textarea v-model="description" label="Description"/></v-card-text><v-card-actions><v-spacer/><v-btn @click="actionDialog = false">Cancel</v-btn><v-btn color="primary" @click="submitAction">{{ action === 'preview-shared-xp' ? 'Preview' : 'Post' }}</v-btn></v-card-actions></v-card></v-dialog>
    <v-dialog v-model="reverseDialog" max-width="520"><v-card title="Reverse transaction"><v-card-text><v-textarea v-model="description" label="Reason"/></v-card-text><v-card-actions><v-spacer/><v-btn @click="reverseDialog = false">Cancel</v-btn><v-btn color="error" @click="reverse">Reverse</v-btn></v-card-actions></v-card></v-dialog>
  </v-container>
</template>
