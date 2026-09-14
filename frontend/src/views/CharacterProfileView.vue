<template>
  <section
    class="container-fluid px-0"
    v-if="character"
  >
    <PlayerEncounterActions
      v-if="ownCharacter && campaign?.encounter"
      :context-id="campaignId"
      :character-id="character.id"
      :current-combatant-id="campaign.encounter.current_combatant_id"
      :combatants="campaign.encounter.combatants"
    />

    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-4"
    >
      <div class="d-flex flex-wrap align-items-center gap-3">
        <CharacterAvatar
          :character="character"
          size="profile"
        />
        <div>
          <h1>{{ character.name }}</h1>
          <p class="mb-1">{{ character.race }} · {{ character.class }}</p>
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
      <div class="d-flex gap-2">
        <ActionMenu
          v-if="canEdit"
          label="Character actions"
          :items="characterActionItems"
        />
        <input
          v-if="canEdit"
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
    <Message
      v-if="character && !character.level_up_complete"
      severity="error"
      class="mb-4"
      title="Level-up incomplete"
    >
      The GM has approved level {{ character.sheet.level }}, but this character still
      has unfinished choices.
      <template>
        <Button
          :as="'router-link'"
          severity="danger"
          :to="'/c/' + campaignId + '/characters/' + characterId + '/level-up'"
          label="Complete level-up"
        />
      </template>
    </Message>
    <div class="row g-3 mb-4">
      <div class="col-12">
        <section class="border rounded-3 p-3 p-md-4 h-100">
          <div
            v-if="canAct"
            class="float-end"
          >
            <ActionMenu
              label="Coin actions"
              :items="coinActionItems"
            />
          </div>
          <div class="row g-0 h-100">
            <div class="col-12 col-sm-7">
              <div>
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Coin pouch
                </div>
                <div class="fs-5 tabular-nums mt-3">
                  {{ formatCoinPouch(character.money) }}
                </div>
              </div>
            </div>
            <div class="col-12 col-sm-5 border-top coin-value-column p-3">
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
      </div>
      <div class="col-12">
        <div class="row g-3">
          <div class="col-12 col-sm-6 col-lg-3">
            <section
              class="border rounded-3 p-3 p-md-4 h-100"
              :class="{ 'hp-card--interactive': canEdit }"
              :role="canEdit ? 'button' : undefined"
              :tabindex="canEdit ? 0 : undefined"
              @click="canEdit && openHpAdjustment()"
              @keydown.enter="canEdit && openHpAdjustment()"
              @keydown.space.prevent="canEdit && openHpAdjustment()"
            >
              <div>
                <div class="d-flex align-items-start justify-content-between gap-2">
                  <div class="text-uppercase fw-semibold small text-body-secondary">
                    HP
                  </div>
                  <div
                    v-if="canEdit"
                    class="hp-actions"
                    @click.stop
                    @keydown.stop
                  >
                    <ActionMenu
                      label="More HP options"
                      :items="hpActionItems"
                    />
                  </div>
                </div>
                <div class="hp-summary mt-3">
                  <div class="h4 hp-value">
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
              </div>
            </section>
          </div>
          <div class="col-12 col-sm-6 col-lg-3">
            <section class="border rounded-3 p-3 p-md-4 h-100">
              <div>
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Armor class
                </div>
                <div class="h4 mt-3">
                  <CalculationBreakdown
                    label="Armor class"
                    :calculation="character.sheet.armor_class_calculation"
                    :activator-label="
                      String(character.sheet.armor_class_calculation.value)
                    "
                  />
                </div>
              </div>
            </section>
          </div>
          <div class="col-12 col-sm-6 col-lg-3">
            <section class="border rounded-3 p-3 p-md-4 h-100">
              <div>
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Initiative bonus
                </div>
                <div class="h4">
                  <CalculationBreakdown
                    label="Initiative bonus"
                    :calculation="character.sheet.initiative"
                    :activator-label="signed(character.sheet.initiative.value)"
                  />
                </div>
              </div>
            </section>
          </div>
          <div class="col-12 col-sm-6 col-lg-3">
            <section class="border rounded-3 p-3 p-md-4 h-100">
              <div>
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Proficiency bonus
                </div>
                <div class="h4">
                  <CalculationBreakdown
                    label="Proficiency bonus"
                    :calculation="character.sheet.proficiency_bonus_calculation"
                    :activator-label="signed(character.sheet.proficiency_bonus)"
                  />
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
      <div class="col-12">
        <ConditionManager
          :conditions="character.conditions"
          :target-name="character.name"
          :target-id="`character-${character.id}`"
          :can-edit="canEdit"
          @apply="applyCondition"
          @remove="removeCondition"
        />
      </div>
      <div class="col-12">
        <section class="mb-4">
          <header class="d-flex align-items-center gap-2 flex-wrap">
            Resources
            <span class="flex-grow-1" />
            <Button
              v-if="canEdit"
              size="small"
              :icon="
                character.has_inspiration ? 'mdi mdi-star' : 'mdi mdi-star-outline'
              "
              @click="toggleInspiration"
            >
              {{
                character.has_inspiration ? "Spend inspiration" : "Award inspiration"
              }}
            </Button>
            <Button
              v-if="canEdit"
              class="ms-2"
              size="small"
              @click="openShortRest"
            >
              Short rest
            </Button>
            <Button
              v-if="canEdit"
              class="ms-2"
              size="small"
              @click="takeRest('long')"
            >
              Long rest
            </Button>
          </header>
          <div>
            <p class="mb-3">
              Inspiration:
              <strong>
                {{ character.has_inspiration ? "Available" : "Not available" }}
              </strong>
              <span class="ms-4">
                Spell attack:
                <strong>{{ signed(character.sheet.spell_attack) }}</strong>
              </span>
              <span class="ms-4">
                Spell save DC:
                <strong>{{ character.sheet.spell_save_dc }}</strong>
              </span>
            </p>
            <div class="table-responsive">
              <table class="table table-striped">
                <caption class="visually-hidden">Spell slot availability</caption>
                <thead>
                  <tr>
                    <th scope="col">Slot</th>
                    <th
                      scope="col"
                      class="text-end tabular-nums"
                    >
                      Current
                    </th>
                    <th
                      scope="col"
                      class="text-end tabular-nums"
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
                    <td class="text-end tabular-nums">{{ pool.current }}</td>
                    <td class="text-end tabular-nums">{{ pool.maximum }}</td>
                    <td>
                      {{
                        pool.adjustment
                          ? `Class ${pool.calculated}, adjustment ${signed(pool.adjustment)}`
                          : `Class ${pool.calculated}`
                      }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
        <section class="border rounded-3 p-3 p-md-4">
          <div>
            <div class="row g-0">
              <div
                v-for="ability in abilityGroups"
                :key="ability.key"
                class="col-12 col-sm-6 col-md-4 col-lg-2 ability-save-cell"
              >
                <div class="ability-save">
                  <div class="ability-save-heading">
                    <span class="ability-save-name">{{ ability.abbreviation }}</span>
                    <strong>{{ signed(ability.modifier) }}</strong>
                    <span class="ability-save-score">{{ ability.score }}</span>
                  </div>
                  <Divider class="my-3" />
                  <div class="ability-save-row">
                    <span>SAVE</span>
                    <strong
                      v-if="ability.save.proficient"
                      :class="proficiencyClass('proficient')"
                      :title="proficiencyLabel('proficient')"
                    >
                      {{ signed(ability.save.bonus) }}
                    </strong>
                    <strong v-else>{{ signed(ability.save.bonus) }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        <section class="mt-4 border rounded-3 p-3 p-md-4">
          <header class="d-flex align-items-center gap-2 flex-wrap">
            Inventory
            <span class="small text-body-secondary ms-2">
              {{ character.inventory.length }} items
            </span>
            <span class="flex-grow-1" />
            <Button
              v-if="canAct"
              size="small"
              icon="mdi mdi-plus"
              @click="addItemOpen = true"
            >
              Add item
            </Button>
          </header>
          <div class="table-responsive">
            <table
              v-if="character.inventory.length"
              class="table table-striped"
            >
              <caption class="visually-hidden">{{ character.name }} inventory</caption>
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th
                    scope="col"
                    class="text-end tabular-nums"
                  >
                    Quantity
                  </th>
                  <th
                    scope="col"
                    class="text-end tabular-nums"
                  >
                    Weight
                  </th>
                  <th
                    scope="col"
                    class="text-end tabular-nums"
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
                <tr
                  v-for="entry in inventoryRows"
                  :key="entry.item_id"
                >
                  <th scope="row">{{ entry.name }}</th>
                  <td class="text-end tabular-nums">
                    {{ entry.quantity.toLocaleString() }}
                  </td>
                  <td class="text-end tabular-nums">
                    {{
                      entry.item?.equipment.weight_amount
                        ? `${entry.item.equipment.weight_amount} ${entry.item.equipment.weight_unit}`
                        : "—"
                    }}
                  </td>
                  <td class="text-end tabular-nums">
                    {{
                      entry.item?.equipment.cost_amount
                        ? `${formatMoneyValue(entry.item.equipment.cost_amount)} ${displayCoin(entry.item.equipment.cost_currency)}`
                        : "—"
                    }}
                  </td>
                  <td class="text-end">
                    <ActionMenu
                      v-if="canAct"
                      :label="`Actions for ${entry.name}`"
                      :items="inventoryActionItems(entry)"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
            <span
              v-else
              class="text-body-secondary"
            >
              No inventory recorded.
            </span>
          </div>
        </section>
        <section class="mt-4">
          <header class="d-flex align-items-center gap-2 flex-wrap">
            Equipment &amp; active effects
            <span class="flex-grow-1" />
            <Button
              v-if="canEdit"
              size="small"
              icon="mdi mdi-plus"
              @click="openEffect"
            >
              Add effect
            </Button>
          </header>
          <div>
            <div
              v-if="character.loadout.length"
              class="table-responsive"
            >
              <table class="table table-striped mb-4">
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
              </table>
            </div>
            <div
              v-if="character.effects.length"
              class="table-responsive"
            >
              <table class="table table-striped">
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
                    <td>
                      {{ effect.duration || displayName(effect.expires_on_rest) }}
                    </td>
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
                      <Button
                        size="small"
                        text
                        :aria-label="`${effect.enabled ? 'Deactivate' : 'Activate'} ${effect.name}`"
                        @click="toggleEffect(effect)"
                      >
                        {{ effect.enabled ? "Deactivate" : "Activate" }}
                      </Button>
                      <Button
                        size="small"
                        text
                        severity="danger"
                        :aria-label="`Remove ${effect.name}`"
                        @click="deleteEffect(effect)"
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <span
              v-if="!character.loadout.length && !character.effects.length"
              class="text-body-secondary"
            >
              No equipment is equipped and no effects are tracked.
            </span>
          </div>
        </section>
        <div class="mt-4 skills-panel">
          <details>
            <summary>Skills</summary>
            <div class="mt-3">
              <div class="row g-3">
                <div
                  v-for="(column, columnIndex) in skillColumns"
                  :key="columnIndex"
                  class="col-12 col-sm-6"
                >
                  <div
                    v-for="ability in column"
                    :key="ability.key"
                    class="mb-3"
                  >
                    <div class="fw-semibold border-bottom pb-1 mb-1">
                      {{ ability.label }}
                    </div>
                    <div
                      v-for="skill in ability.skills"
                      :key="skill.name"
                      class="d-flex justify-content-between gap-3 py-1"
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
                </div>
              </div>
            </div>
          </details>
        </div>
        <div class="mt-4">
          <details>
            <summary>Notes ({{ character.notes.length }})</summary>
            <div>
              <ul class="list-group list-group-flush">
                <li
                  v-for="note in character.notes"
                  :key="note.id"
                >
                  <strong>{{ note.title || "Note" }}</strong>
                  <span v-if="note.body">{{ note.body }}</span>
                </li>
              </ul>
            </div>
          </details>
          <details>
            <summary>Features &amp; feats ({{ character.features.length }})</summary>
            <div>
              <ul class="list-group list-group-flush">
                <li
                  v-for="feature in character.features"
                  :key="feature.id"
                >
                  <strong>{{ feature.name }}</strong>
                  <span v-if="feature.description || feature.notes">
                    {{ feature.description || feature.notes }}
                  </span>
                </li>
              </ul>
            </div>
          </details>
          <details>
            <summary>Spells ({{ character.spells.length }})</summary>
            <div>
              <ul class="list-group list-group-flush">
                <li
                  v-for="spell in character.spells"
                  :key="spell.id"
                >
                  <strong>{{ spell.name }} · level {{ spell.level }}</strong>
                  <span v-if="spell.description || spell.notes">
                    {{ spell.description || spell.notes }}
                  </span>
                  <Button
                    v-if="canEdit"
                    size="small"
                    text
                    :disabled="spell.level > 0 && !spell.prepared"
                    :aria-label="`Record casting ${spell.name}`"
                    @click="openSpellCast(spell)"
                  >
                    Cast
                  </Button>
                </li>
              </ul>
            </div>
          </details>
          <details>
            <summary>Companions ({{ character.companions.length }})</summary>
            <div>
              <ul class="list-group list-group-flush">
                <li
                  v-for="companion in character.companions"
                  :key="companion.id"
                >
                  <strong>{{ companion.name }}</strong>
                  <span>
                    AC {{ companion.armor_class }} · HP {{ companion.current_hp }}/{{
                      companion.max_hp
                    }}
                    · {{ companion.speed }}
                  </span>
                </li>
              </ul>
            </div>
          </details>
        </div>
        <section class="mt-4 activity-card">
          <header class="d-flex align-items-center gap-2 flex-wrap">
            Recent activity
            <span class="flex-grow-1" />
            <Button
              :as="'router-link'"
              :to="`/c/${campaignId}/ledger`"
              size="small"
              text
              label="View full ledger"
            />
          </header>
          <div>
            <template v-if="activity.length">
              <div
                v-for="transaction in activity"
                :key="`${transaction.ledger}-${transaction.id}`"
                class="row py-2 border-bottom"
              >
                <span>{{ new Date(transaction.created_at).toLocaleString() }}</span>
                <strong>{{ activityAmount(transaction) }}</strong>
                <span>{{ activityDescription(transaction) }}</span>
                <span>{{ transaction.actor ? `by ${transaction.actor}` : "—" }}</span>
              </div>
            </template>
            <span
              v-else
              class="text-body-secondary"
            >
              No recent activity.
            </span>
          </div>
        </section>
      </div>
    </div>
    <Dialog
      v-model:visible="addItemOpen"
      :style="{ width: 'min(35rem, calc(100vw - 2rem))' }"
      @update:visible="closeAddItemDialogWhenClosed"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="add-item-heading"
      >
        <h2
          id="add-item-heading"
          class="h3 mb-0"
        >
          Add item
        </h2>
        <div class="d-grid gap-3">
          <ItemPickerDialog
            v-model="grantItemId"
            :candidates="allItemCandidates"
            label="Item"
            no-data-text="No campaign items available."
          />
          <label class="form-label mb-0">
            Quantity
            <InputNumber
              v-model.number="grantQuantity"
              class="w-100"
              :min="1"
              :step="1"
              show-buttons
              fluid
            />
          </label>
        </div>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="closeAddItemDialog"
          />
          <Button
            label="Add item"
            :disabled="!grantItemId || grantQuantity < 1"
            @click="grantItem"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="moneyDialog"
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
          {{
            moneyAction === "spend"
              ? "Spend coins"
              : moneyAction === "transfer"
                ? "Transfer coins"
                : "Exchange coins"
          }}
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
                    :model-value="
                      exchangeAmount === undefined ? '' : String(exchangeAmount)
                    "
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
            :label="
              moneyAction === 'spend'
                ? 'Spend coins'
                : moneyAction === 'transfer'
                  ? 'Transfer coins'
                  : 'Exchange coins'
            "
            :disabled="
              moneyAction === 'transfer'
                ? !moneyDestination || !hasMoneyAmounts || hasInvalidMoneyAmounts
                : moneyAction === 'exchange'
                  ? !exchangeAmount
                  : !hasMoneyAmounts || hasInvalidMoneyAmounts
            "
            @click="submitMoneyAction"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="effectOpen"
      :style="{ width: 'min(35rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="add-effect-heading"
      >
        <h2
          id="add-effect-heading"
          class="h3 mb-0"
        >
          Add active effect
        </h2>
        <div class="d-grid gap-3">
          <label class="form-label mb-0">
            Effect name
            <InputText
              v-model="effectName"
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Source (optional)
            <InputText
              v-model="effectSource"
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Duration or expiry reminder
            <InputText
              v-model="effectDuration"
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Modifier target
            <Select
              v-model="effectTarget"
              :options="effectTargets"
              option-label="title"
              option-value="value"
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Numeric modifier (0 for reminder only)
            <InputNumber
              v-model.number="effectValue"
              :min="-99"
              :max="99"
              :step="1"
              show-buttons
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Reminder (conditional or dice effects)
            <Textarea
              v-model="effectReminder"
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
            @click="effectOpen = false"
          />
          <Button
            label="Add effect"
            :disabled="!effectName.trim()"
            @click="saveEffect"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="shortRestOpen"
      :style="{ width: 'min(29rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="short-rest-heading"
      >
        <h2
          id="short-rest-heading"
          class="h3 mb-0"
        >
          Short rest
        </h2>
        <div class="d-grid gap-3">
          <p class="mb-4">
            Enter current HP after spending Hit Dice. Hoard does not roll Hit Dice.
          </p>
          <label class="form-label mb-0">
            Current HP after rest
            <InputNumber
              v-model.number="shortRestHp"
              :min="0"
              :max="character?.sheet.max_hp ?? 1"
              :step="1"
              show-buttons
              fluid
            />
          </label>
        </div>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="shortRestOpen = false"
          />
          <Button
            label="Record short rest"
            @click="takeRest('short')"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="spellCastOpen"
      :style="{ width: 'min(29rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="cast-spell-heading"
      >
        <h2
          id="cast-spell-heading"
          class="h3 mb-0"
        >
          {{ castingSpell ? `Cast ${castingSpell.name}` : "Cast spell" }}
        </h2>
        <div>
          <label class="form-label mb-0">
            Spell slot
            <Select
              v-model="castingSlot"
              :options="castingSlots"
              option-label="title"
              option-value="value"
              empty-message="No eligible spell slots available"
              fluid
            />
          </label>
        </div>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="spellCastOpen = false"
          />
          <Button
            label="Record casting"
            :disabled="!castingSlot"
            @click="confirmSpellCast"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      :visible="Boolean(itemAction)"
      :style="{ width: 'min(35rem, calc(100vw - 2rem))' }"
      @update:visible="closeItemActionWhenClosed"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="item-action-heading"
      >
        <h2
          id="item-action-heading"
          class="h3 mb-0"
        >
          {{
            itemAction === "use"
              ? "Use item"
              : itemAction === "destroy"
                ? "Destroy item"
                : "Transfer item"
          }}
        </h2>
        <div
          v-if="selectedInventoryItem"
          class="d-grid gap-3"
        >
          <p class="mb-0">
            {{ selectedInventoryItem.name }} · {{ selectedInventoryItem.quantity }} held
          </p>
          <label
            v-if="itemAction === 'transfer'"
            class="form-label mb-0"
          >
            Transfer to
            <Select
              v-model="itemActionDestination"
              :options="destinationOptions"
              option-label="title"
              option-value="value"
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Quantity
            <InputNumber
              v-model.number="itemActionQuantity"
              :min="1"
              :max="selectedInventoryItem.quantity"
              :step="1"
              show-buttons
              fluid
            />
          </label>
          <label class="form-label mb-0">
            Note (optional)
            <Textarea
              v-model="itemActionDescription"
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
            @click="closeItemAction"
          />
          <Button
            :label="
              itemAction === 'use'
                ? 'Use item'
                : itemAction === 'destroy'
                  ? 'Destroy item'
                  : 'Transfer item'
            "
            :disabled="itemActionInvalid"
            @click="submitItemAction"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="hpAdjustmentOpen"
      :style="{ width: 'min(26rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="adjust-hp-heading"
      >
        <h2
          id="adjust-hp-heading"
          class="h3 mb-0"
        >
          Adjust HP
        </h2>
        <div class="d-grid gap-3">
          <p class="mb-0">
            Current HP: {{ character.sheet.current_hp }} / {{ character.sheet.max_hp }}
          </p>
          <label class="form-label mb-0">
            Hit points
            <InputNumber
              v-model.number="healthAmount"
              :min="1"
              :step="1"
              show-buttons
              fluid
            />
          </label>
        </div>
        <footer class="d-flex justify-content-end gap-2 flex-wrap">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="hpAdjustmentOpen = false"
          />
          <Button
            label="Damage"
            severity="danger"
            :disabled="healthAmount < 1 || !canDamage"
            @click="submitHpAdjustment('damage')"
          />
          <Button
            label="Heal"
            :disabled="healthAmount < 1 || !canHeal"
            @click="submitHpAdjustment('healing')"
          />
        </footer>
      </section>
    </Dialog>
    <Dialog
      v-model:visible="healthOpen"
      :style="{ width: 'min(33rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="record-hp-heading"
      >
        <h2
          id="record-hp-heading"
          class="h3 mb-0"
        >
          Record HP change
        </h2>
        <div class="d-grid gap-3">
          <label class="form-label mb-0">
            Action
            <Select
              v-model="healthReason"
              :options="[
                { title: 'Damage', value: 'damage' },
                { title: 'Healing', value: 'healing' },
                { title: 'Temporary HP change', value: 'temporary' },
                { title: 'Correction', value: 'correction' },
              ]"
              option-label="title"
              option-value="value"
              fluid
            />
          </label>
          <label
            v-if="healthReason !== 'correction'"
            class="form-label mb-0"
          >
            Amount
            <InputNumber
              v-model.number="healthAmount"
              :min="1"
              :step="1"
              show-buttons
              fluid
            />
          </label>
          <template v-else>
            <label class="form-label mb-0">
              Correct current HP
              <InputNumber
                v-model.number="healthCurrent"
                :min="0"
                :step="1"
                show-buttons
                fluid
              />
            </label>
            <label class="form-label mb-0">
              Correct temporary HP
              <InputNumber
                v-model.number="healthTemporary"
                :min="0"
                :step="1"
                show-buttons
                fluid
              />
            </label>
          </template>
          <Message severity="info">
            {{ healthPreview }}
          </Message>
          <label class="form-label mb-0">
            Reason (optional)
            <Textarea
              v-model="healthDescription"
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
            @click="healthOpen = false"
          />
          <Button
            label="Record transaction"
            @click="saveHealth"
          />
        </footer>
      </section>
    </Dialog>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Divider from "primevue/divider";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import type { MenuItem } from "primevue/menuitem";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { defineComponent } from "vue";
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
  removeCharacterCondition,
  removeCharacterPortrait,
  restCharacter,
  setCharacterCondition,
  setCharacterInspiration,
  uploadCharacterPortrait,
  type Campaign,
  type Character,
  type ConditionMutation,
  type Item,
  type LedgerTransaction,
} from "../api";
import { exchangedCoinAmount } from "../coinExchange";
import ActionMenu from "../components/ActionMenu.vue";
import CalculationBreakdown from "../components/CalculationBreakdown.vue";
import CharacterAvatar from "../components/CharacterAvatar.vue";
import CoinAmountPicker from "../components/CoinAmountPicker.vue";
import ConditionManager from "../components/ConditionManager.vue";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
import PlayerEncounterActions from "../components/PlayerEncounterActions.vue";
import { displayCoin, displayIdentifier, formatCoinPouch } from "../display";
import type { PickerCandidate } from "../itemPicker";
import { formatGoldValue, formatMoneyValue } from "../money";
import { campaignRefreshRevision } from "../realtime";

type InventoryRow = Character["inventory"][number] & {
  item?: Item;
};

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

const xpThresholds = [
  0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000,
  140000, 165000, 195000, 225000, 265000, 305000, 355000,
];

const NEAR_LEVEL_UP_XP_THRESHOLD = 1000;

const denominationOptions = ["cp", "sp", "ep", "gp", "pp"].map((value) => ({
  title: displayCoin(value),
  value,
}));

const effectTargetOptions = [
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

export default defineComponent({
  components: {
    ActionMenu,
    Button,
    Dialog,
    Divider,
    InputNumber,
    InputText,
    Message,
    Select,
    Textarea,
    CoinAmountPicker,
    ConditionManager,
    CalculationBreakdown,
    CharacterAvatar,
    ItemPickerDialog,
    PlayerEncounterActions,
  },
  data() {
    const levelUpError = this.$route.query.level_up_error;

    return {
      campaignId: Number(this.$route.params.id),
      characterId: Number(this.$route.params.characterId),
      campaign: undefined as Campaign | undefined,
      character: undefined as Character | undefined,
      ownCharacter: false,
      characters: [] as Character[],
      items: [] as Item[],
      error: typeof levelUpError === "string" ? levelUpError : "",
      grantItemId: undefined as number | undefined,
      grantQuantity: 1,
      itemAction: undefined as "use" | "destroy" | "transfer" | undefined,
      selectedInventoryItem: undefined as
        { item_id: number; name: string; quantity: number } | undefined,
      itemActionQuantity: 1,
      itemActionDestination: undefined as number | undefined,
      itemActionDescription: "",
      moneyAction: "spend" as "spend" | "transfer" | "exchange",
      moneyDialog: false,
      denomination: "gp",
      amount: 1,
      moneyAmounts: { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 } as Record<string, number>,
      moneyDestination: undefined as number | undefined,
      exchangeTargetDenomination: "sp",
      moneyDescription: "",
      addItemOpen: false,
      activity: [] as LedgerTransaction[],
      healthOpen: false,
      hpAdjustmentOpen: false,
      healthReason: "damage" as "damage" | "healing" | "temporary" | "correction",
      healthAmount: 1,
      healthCurrent: 0,
      healthTemporary: 0,
      healthDescription: "",
      shortRestOpen: false,
      shortRestHp: 0,
      spellCastOpen: false,
      castingSpell: undefined as Character["spells"][number] | undefined,
      castingSlot: undefined as string | undefined,
      effectOpen: false,
      effectName: "",
      effectSource: "",
      effectDuration: "",
      effectReminder: "",
      effectTarget: "ac",
      effectValue: 0,
      denominations: denominationOptions,
      xpThresholds,
      effectTargets: effectTargetOptions,
    };
  },
  computed: {
    characterActionItems(): MenuItem[] {
      const items: MenuItem[] = [
        {
          label: "Edit character",
          icon: "mdi mdi-pencil",
          command: () => {
            void this.$router.push(
              `/c/${this.campaignId}/characters/${this.characterId}/build?mode=edit`,
            );
          },
        },
        {
          label: "Change portrait",
          icon: "mdi mdi-image-edit",
          command: () => this.choosePortrait(),
        },
      ];

      if (this.character?.portrait_url) {
        items.push({
          label: "Remove portrait",
          icon: "mdi mdi-image-remove",
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
    hpActionItems(): MenuItem[] {
      return [
        {
          label: "Add temporary HP",
          icon: "mdi mdi-shield-plus-outline",
          command: () => this.openHealthFor("temporary"),
        },
        {
          label: "Advanced HP adjustment",
          icon: "mdi mdi-tune-variant",
          command: () => this.openHealthFor("damage"),
        },
      ];
    },
    refreshRevision(): number {
      return campaignRefreshRevision.value;
    },
    healthPreview(): string {
      if (!this.character) {
        return "";
      }

      const beforeCurrent = this.character.sheet.current_hp;
      const beforeTemporary = this.character.sheet.temporary_hp;

      if (this.healthReason === "correction") {
        return `Current ${beforeCurrent} → ${this.healthCurrent}; temporary ${beforeTemporary} → ${this.healthTemporary}`;
      }

      if (this.healthReason === "damage") {
        const damage = Math.abs(this.healthAmount);
        const absorbed = Math.min(beforeTemporary, damage);

        return `Damage ${damage}: temporary ${beforeTemporary} − ${absorbed} = ${beforeTemporary - absorbed}; current ${beforeCurrent} − ${damage - absorbed} = ${Math.max(0, beforeCurrent - (damage - absorbed))}`;
      }

      if (this.healthReason === "healing") {
        const healing = Math.abs(this.healthAmount);
        const result = Math.min(this.character.sheet.max_hp, beforeCurrent + healing);

        return `Current ${beforeCurrent} + ${healing} = ${result} (maximum ${this.character.sheet.max_hp})`;
      }

      return `Temporary ${beforeTemporary} + ${this.healthAmount} = ${beforeTemporary + this.healthAmount}`;
    },
    allItemCandidates(): PickerCandidate[] {
      return this.items.map((item) => ({ item }));
    },
    inventoryRows() {
      return (this.character?.inventory ?? []).map((entry) => ({
        ...entry,
        item: this.items.find((item) => item.id === entry.item_id),
      }));
    },
    destinationOptions() {
      return this.characters
        .filter(
          (candidate) =>
            candidate.id !== this.character?.id &&
            candidate.is_active &&
            !candidate.is_archived,
        )
        .map((candidate) => ({ title: candidate.name, value: candidate.id }));
    },
    exchangeAmount() {
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
    selectedInventoryQuantity(): number {
      return this.selectedInventoryItem?.quantity ?? 0;
    },
    itemActionInvalid(): boolean {
      return (
        this.itemActionQuantity < 1 ||
        this.itemActionQuantity > this.selectedInventoryQuantity ||
        (this.itemAction === "transfer" && !this.itemActionDestination)
      );
    },
    canAct(): boolean {
      return Boolean(
        this.ownCharacter && this.character?.is_active && !this.character.is_archived,
      );
    },
    canEdit(): boolean {
      return this.ownCharacter || Boolean(this.campaign?.is_game_master);
    },
    canDamage(): boolean {
      const sheet = this.character?.sheet;

      return Boolean(sheet && (sheet.current_hp > 0 || sheet.temporary_hp > 0));
    },
    canHeal(): boolean {
      const sheet = this.character?.sheet;

      return Boolean(sheet && sheet.current_hp < sheet.max_hp);
    },
    castingSlots() {
      const spell = this.castingSpell;

      if (!spell || !this.character) {
        return [];
      }

      return Object.entries(this.character.sheet.spell_slot_pools)
        .filter(
          ([key, pool]) =>
            !key.startsWith("pact-") && Number(key) >= spell.level && pool.current > 0,
        )
        .map(([key, pool]) => ({
          title: `Level ${key} (${pool.current}/${pool.maximum})`,
          value: key,
        }));
    },
    experienceProgress() {
      const level = this.character?.sheet.level ?? 1;
      const current = this.character?.experience ?? 0;
      const minimum = this.xpThresholds[level - 1] ?? 0;
      const maximum = this.xpThresholds[level];
      const progress = maximum
        ? Math.min(100, Math.max(0, ((current - minimum) / (maximum - minimum)) * 100))
        : 100;
      const remaining = maximum === undefined ? null : Math.max(0, maximum - current);
      const isNearLevelUp =
        remaining !== null && remaining < NEAR_LEVEL_UP_XP_THRESHOLD;

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
    abilityGroups() {
      if (!this.character) {
        return [];
      }

      const character = this.character;
      const scores: Record<string, number> = {
        strength: character.strength,
        dexterity: character.dexterity,
        constitution: character.constitution,
        intelligence: character.intelligence,
        wisdom: character.wisdom,
        charisma: character.charisma,
      };

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
        score: scores[key],
        modifier: character.sheet.abilities[key].modifier,
        save: character.sheet.saves[key],
        skills: Object.entries(character.sheet.skills)
          .filter(([name]) => skillAbilities[name] === key)
          .map(([name, skill]) => ({ name, ...skill })),
      }));
    },
    skillGroups() {
      const order = ["strength", "wisdom", "dexterity", "charisma", "intelligence"];

      return this.abilityGroups
        .filter((ability) => ability.skills.length)
        .sort((left, right) => order.indexOf(left.key) - order.indexOf(right.key));
    },
    skillColumns() {
      return [
        this.skillGroups.filter((ability) =>
          ["strength", "dexterity", "intelligence"].includes(ability.key),
        ),
        this.skillGroups.filter((ability) =>
          ["wisdom", "charisma"].includes(ability.key),
        ),
      ];
    },
  },
  watch: {
    refreshRevision(): void {
      void this.load();
    },
  },
  methods: {
    showSuccess(message: string): void {
      this.$toast.add({
        severity: "success",
        summary: message,
        life: 4_000,
      });
    },
    displayCoin,
    displayName: displayIdentifier,
    formatCoinPouch,
    formatGoldValue,
    formatMoneyValue,
    signed(value: number): string {
      return value >= 0 ? `+${value}` : `${value}`;
    },
    formatXp(value: number): string {
      return `${value.toLocaleString()} XP`;
    },
    activityAmount(transaction: LedgerTransaction): string {
      return transaction.entries
        .filter((entry) => entry.account_name === this.character?.name)
        .map(
          (entry) =>
            `${entry.amount > 0 ? "+" : ""}${entry.amount} ${
              entry.item_name ??
              (entry.denomination ? displayCoin(entry.denomination) : "XP")
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
    proficiencyLabel(proficiency: string): string {
      return (
        {
          half: "Half",
          proficient: "Proficient",
          expertise: "Expertise",
        }[proficiency] ?? ""
      );
    },
    proficiencyClass(proficiency: string): string {
      return `proficiency-bonus proficiency-bonus--${proficiency}`;
    },
    async applyCondition(condition: ConditionMutation): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await setCharacterCondition(this.campaignId, this.character.id, condition);
        await this.load();
        this.showSuccess(`${this.displayName(condition.identifier)} updated.`);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to apply the condition.";
      }
    },
    async removeCondition(conditionId: number): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await removeCharacterCondition(this.campaignId, this.character.id, conditionId);
        await this.load();
        this.showSuccess("Condition removed.");
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to remove the condition.";
      }
    },
    openShortRest(): void {
      if (!this.character) {
        return;
      }

      this.shortRestHp = this.character.sheet.current_hp;
      this.shortRestOpen = true;
    },
    async takeRest(kind: "short" | "long"): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        this.character = await restCharacter(
          this.campaignId,
          this.character.id,
          kind,
          kind === "short" ? this.shortRestHp : undefined,
        );
        this.shortRestOpen = false;
        this.showSuccess(`${kind === "short" ? "Short" : "Long"} rest recorded.`);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to record rest.";
      }
    },
    openSpellCast(spell: Character["spells"][number]): void {
      this.castingSpell = spell;
      this.castingSlot = undefined;

      if (spell.level === 0) {
        void this.confirmSpellCast();
      } else {
        this.spellCastOpen = true;
      }
    },
    async confirmSpellCast(): Promise<void> {
      if (!this.character || !this.castingSpell) {
        return;
      }

      try {
        this.character = await castCharacterSpell(
          this.campaignId,
          this.character.id,
          this.castingSpell.id,
          this.castingSpell.level === 0 ? undefined : this.castingSlot,
        );
        this.spellCastOpen = false;
        this.showSuccess(`${this.castingSpell.name} recorded.`);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to record spell casting.";
      }
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
    choosePortrait(): void {
      const input = this.$refs.portraitInput as HTMLInputElement;

      input.click();
    },
    async uploadPortrait(event: Event): Promise<void> {
      if (!this.character) {
        return;
      }

      const input = event.target as HTMLInputElement;
      const file = input.files?.[0];

      if (!file) {
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        this.error = "Portraits must be no larger than 5 MB.";
        input.value = "";

        return;
      }

      try {
        const result = await uploadCharacterPortrait(
          this.campaignId,
          this.character.id,
          file,
        );
        this.character = { ...this.character, portrait_url: result.portrait_url };
        this.showSuccess("Portrait updated.");
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update portrait.";
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
        this.character = { ...this.character, portrait_url: null };
        this.showSuccess("Portrait removed.");
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to remove portrait.";
      }
    },
    async load(): Promise<void> {
      try {
        const [nextCampaign, visible, own, nextItems, recent] = await Promise.all([
          getCampaign(this.campaignId),
          getCharacters(this.campaignId),
          getMyCharacters(this.campaignId),
          getItems(this.campaignId),
          getTransactions(this.campaignId, "all", 1, this.characterId),
        ]);

        this.campaign = nextCampaign;
        this.characters = visible;
        this.character =
          visible.find((candidate) => candidate.id === this.characterId) ??
          own.find((candidate) => candidate.id === this.characterId);
        this.ownCharacter = own.some((candidate) => candidate.id === this.characterId);

        if (this.ownCharacter && this.character && !this.character.is_build_complete) {
          await this.$router.replace(
            `/c/${this.campaignId}/characters/${this.characterId}/build`,
          );
          return;
        }

        this.items = nextItems;
        this.activity = recent.results.slice(0, 5);

        if (!this.character) {
          await this.$router.replace(`/c/${this.campaignId}/characters`);
        }
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load character profile.";
      }
    },
    async toggleInspiration(): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        this.character = await setCharacterInspiration(
          this.campaignId,
          this.character.id,
          !this.character.has_inspiration,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to update inspiration.";
      }
    },
    async equipItem(entry: { item_id: number; name: string }): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "loadout",
          "create",
          {
            item_id: entry.item_id,
            equipped: true,
          },
        );
        this.showSuccess(`${entry.name} equipped.`);
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to equip item.";
      }
    },
    async grantItem(): Promise<void> {
      if (!this.character || !this.grantItemId) {
        return;
      }

      try {
        await createInventoryTransaction(this.campaignId, {
          from_character_id: null,
          to_character_id: this.character.id,
          item_id: this.grantItemId,
          quantity: this.grantQuantity,
          description: "Self-granted item",
        });

        this.showSuccess("Saved to the ledger.");
        this.closeAddItemDialog();
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to complete this action.";
      }
    },
    closeAddItemDialog(): void {
      this.addItemOpen = false;
      this.grantItemId = undefined;
      this.grantQuantity = 1;
    },
    closeAddItemDialogWhenClosed(open: boolean): void {
      if (open) {
        return;
      }

      this.closeAddItemDialog();
    },
    openItemAction(
      action: "use" | "destroy" | "transfer",
      entry: { item_id: number; name: string; quantity: number },
    ): void {
      this.itemAction = action;
      this.selectedInventoryItem = entry;
      this.itemActionQuantity = 1;
      this.itemActionDestination = undefined;
      this.itemActionDescription = "";
    },
    inventoryActionItems(entry: InventoryRow): MenuItem[] {
      const items: MenuItem[] = [];
      const category = entry.item?.equipment.category;

      if (category === "weapon" || category === "armor") {
        items.push({
          label: "Equip",
          icon: "mdi mdi-shield-sword-outline",
          command: () => void this.equipItem(entry),
        });
      }

      items.push(
        {
          label: "Use",
          icon: "mdi mdi-play-outline",
          command: () => this.openItemAction("use", entry),
        },
        {
          label: "Transfer",
          icon: "mdi mdi-swap-horizontal",
          command: () => this.openItemAction("transfer", entry),
        },
        { separator: true },
        {
          label: "Destroy",
          icon: "mdi mdi-delete-outline",
          class: "text-danger",
          command: () => this.openItemAction("destroy", entry),
        },
      );

      return items;
    },
    closeItemAction(): void {
      this.itemAction = undefined;
      this.selectedInventoryItem = undefined;
      this.itemActionQuantity = 1;
      this.itemActionDestination = undefined;
      this.itemActionDescription = "";
    },
    closeItemActionWhenClosed(open: boolean): void {
      if (!open) {
        this.closeItemAction();
      }
    },
    async submitItemAction(): Promise<void> {
      if (!this.character || !this.selectedInventoryItem || !this.itemAction) {
        return;
      }

      if (this.itemActionInvalid) {
        return;
      }

      try {
        await createInventoryTransaction(this.campaignId, {
          from_character_id: this.character.id,
          to_character_id:
            this.itemAction === "transfer" ? this.itemActionDestination! : null,
          item_id: this.selectedInventoryItem.item_id,
          quantity: this.itemActionQuantity,
          description:
            this.itemActionDescription ||
            `${this.itemAction === "use" ? "Used" : this.itemAction === "destroy" ? "Destroyed" : "Transferred"} ${this.selectedInventoryItem.name}`,
        });

        this.showSuccess("Saved to the ledger.");
        this.closeItemAction();
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to update inventory.";
      }
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

        this.showSuccess("Saved to the ledger.");
        this.closeMoneyDialog();
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update money.";
      }
    },
    openHealth(): void {
      if (!this.character) {
        return;
      }

      this.healthCurrent = this.character.sheet.current_hp;
      this.healthTemporary = this.character.sheet.temporary_hp;
      this.healthAmount = 1;
      this.healthDescription = "";
      this.healthOpen = true;
    },
    openHealthFor(reason: "damage" | "healing" | "temporary" | "correction"): void {
      this.healthReason = reason;
      this.openHealth();
    },
    openHpAdjustment(): void {
      this.healthAmount = 1;
      this.hpAdjustmentOpen = true;
    },
    async submitHpAdjustment(reason: "damage" | "healing"): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await postHealth(this.campaignId, {
          character_id: this.character.id,
          reason,
          current_hp_delta:
            reason === "damage" ? -Math.abs(this.healthAmount) : this.healthAmount,
        });
        this.hpAdjustmentOpen = false;
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update HP.";
      }
    },
    async saveHealth(): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await postHealth(this.campaignId, {
          character_id: this.character.id,
          reason: this.healthReason,
          ...(this.healthReason === "damage"
            ? { current_hp_delta: -Math.abs(this.healthAmount) }
            : {}),
          ...(this.healthReason === "healing"
            ? { current_hp_delta: Math.abs(this.healthAmount) }
            : {}),
          ...(this.healthReason === "temporary"
            ? { temporary_hp_delta: this.healthAmount }
            : {}),
          ...(this.healthReason === "correction"
            ? {
                current_hp: this.healthCurrent,
                temporary_hp: this.healthTemporary,
              }
            : {}),
          description: this.healthDescription,
        });
        this.healthOpen = false;
        this.healthDescription = "";
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update HP.";
      }
    },
    openEffect(): void {
      this.effectName = "";
      this.effectSource = "";
      this.effectDuration = "";
      this.effectReminder = "";
      this.effectTarget = "ac";
      this.effectValue = 0;
      this.effectOpen = true;
    },
    async toggleEffect(effect: Character["effects"][number]): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "effects",
          "update",
          { enabled: !effect.enabled },
          effect.id,
        );
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update effect.";
      }
    },
    async saveEffect(): Promise<void> {
      if (!this.character || !this.effectName.trim()) {
        return;
      }

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "effects",
          "create",
          {
            name: this.effectName,
            source: this.effectSource,
            duration: this.effectDuration,
            reminder: this.effectReminder,
            modifiers: this.effectValue
              ? [{ target: this.effectTarget, value: this.effectValue }]
              : [],
          },
        );
        this.effectOpen = false;
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to add effect.";
      }
    },
    async deleteEffect(effect: Character["effects"][number]): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "effects",
          "delete",
          {},
          effect.id,
        );
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to remove effect.";
      }
    },
  },
  mounted() {
    void this.load();
  },
});
</script>

<style scoped>
.level-up-near {
  color: var(--hoard-gold);
  font-weight: var(--bs-body-font-weight);
}

@media (min-width: 576px) {
  .coin-value-column {
    border-top: 0 !important;
    border-left: var(--bs-border-width) var(--bs-border-style) var(--bs-border-color) !important;
  }
}
</style>
