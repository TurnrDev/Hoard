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
      :movement-speed="character.sheet.speed"
    />

    <header
      class="position-relative mb-4"
      :class="{ 'pe-5': canEdit }"
    >
      <div class="d-flex flex-wrap align-items-center gap-3">
        <CharacterAvatar
          :character="character"
          size="profile"
        />
        <div>
          <h1 :class="{ 'inspired-name': character.has_inspiration }">
            {{ character.name }}
            <span
              v-if="character.has_inspiration"
              class="visually-hidden"
            >
              — Inspired
            </span>
          </h1>
          <p class="mb-1">{{ character.race }} · {{ character.class }}</p>
          <p
            v-if="character.is_dead"
            class="mb-1 text-danger fw-semibold"
          >
            <span
              class="mdi mdi-coffin me-1"
              aria-hidden="true"
            />
            Dead
            <template v-if="character.death">
              · Died {{ character.death.campaign_date }}
            </template>
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
      <div class="position-absolute top-0 end-0 d-flex gap-2">
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
      v-if="ownCharacter && character.is_dead && character.death?.notice_visible"
      severity="error"
      class="mb-4"
    >
      You are dead.
      <template v-if="character.death.revival_notice_visible">
        Your party can still revive you.
      </template>
      You died on {{ character.death.campaign_date }}.
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
            class="d-none d-sm-block float-end"
          >
            <ActionMenu
              label="Coin actions"
              :items="coinActionItems"
            />
          </div>
          <div class="d-sm-none">
            <Transition
              name="ability-card-flip"
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
          <div class="row g-0 h-100 d-none d-sm-flex">
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
        <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xl-5 g-3">
          <div class="col">
            <CalculationCard
              label="HP"
              :summary="`${character.sheet.current_hp} / ${character.sheet.max_hp}`"
              :calculation="character.sheet.hp_calculation"
              :interactive="canEdit"
              activation-label="Adjust hit points"
              calculation-label="Maximum HP"
              :force-back="character.sheet.current_hp === 0"
              back-label="Death saving throws"
              @activate="openHpAdjustment"
            >
              <template #actions>
                <ActionMenu
                  v-if="canEdit"
                  label="More HP options"
                  :items="hpActionItems"
                />
              </template>
              <template #summary>
                {{ character.sheet.current_hp }}
                <template v-if="character.sheet.temporary_hp">
                  + {{ character.sheet.temporary_hp }}
                </template>
                <span aria-hidden="true">/</span>
                {{ character.sheet.max_hp }}
              </template>
              <template #back>
                <div class="d-grid gap-3">
                  <div
                    v-for="kind in deathSaveKinds"
                    :key="kind"
                  >
                    <div
                      class="d-flex align-items-center justify-content-between gap-2"
                    >
                      <span class="fw-semibold">
                        {{ kind === "successes" ? "Successes" : "Failures" }}
                      </span>
                      <span
                        class="d-flex gap-1"
                        role="group"
                        :aria-label="`${deathSaveCount(kind)} of 3 ${kind}`"
                      >
                        <button
                          v-for="index in 3"
                          :key="index"
                          type="button"
                          :class="[
                            'death-save-toggle mdi',
                            character.death_saves[kind][index - 1]
                              ? kind === 'successes'
                                ? 'mdi-check-circle'
                                : 'mdi-close-circle'
                              : 'mdi-circle-outline',
                          ]"
                          :aria-label="`Set ${kind} to ${deathSaveTargetCount(kind, index - 1)}`"
                          :aria-pressed="character.death_saves[kind][index - 1]"
                          :disabled="deathSaveBusy || !canEdit || character.is_dead"
                          @click="toggleDeathSave(kind, index - 1)"
                        />
                      </span>
                    </div>
                  </div>
                  <Button
                    v-if="canEdit"
                    label="Stabilize"
                    icon="mdi mdi-medical-bag"
                    :loading="stabilizationBusy"
                    @click="stabilize"
                  />
                </div>
              </template>
            </CalculationCard>
          </div>
          <div class="col">
            <CalculationCard
              label="Armor class"
              :summary="String(character.sheet.armor_class_calculation.value)"
              :calculation="character.sheet.armor_class_calculation"
            />
          </div>
          <div class="col">
            <CalculationCard
              label="Initiative bonus"
              :summary="signed(character.sheet.initiative.value)"
              :calculation="character.sheet.initiative"
            />
          </div>
          <div class="col">
            <CalculationCard
              label="Proficiency bonus"
              :summary="signed(character.sheet.proficiency_bonus)"
              :calculation="character.sheet.proficiency_bonus_calculation"
            />
          </div>
          <div class="col">
            <section class="border rounded-3 p-3 p-md-4 h-100">
              <div class="d-flex align-items-start justify-content-between gap-2">
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Movement speed
                </div>
                <Button
                  v-if="canEdit"
                  icon="mdi mdi-pencil-outline"
                  text
                  rounded
                  size="small"
                  aria-label="Edit movement speed"
                  @click="openSpeedEditor"
                />
              </div>
              <div class="h4 mt-3 mb-0 tabular-nums">
                <span
                  class="mdi mdi-run me-1"
                  aria-hidden="true"
                />
                {{ movementSpeedLabel }}
              </div>
            </section>
          </div>
        </div>
      </div>
      <div
        class="col-12"
        :class="{ 'd-none': character.conditions.length === 0 }"
      >
        <ConditionManager
          ref="conditionManager"
          :trigger-only="character.conditions.length === 0"
          :show-trigger="false"
          :conditions="character.conditions"
          :target-name="character.name"
          :target-id="`character-${character.id}`"
          :can-edit="canEdit"
          @apply="applyCondition"
          @remove="removeCondition"
        />
      </div>
      <div
        v-if="canEdit && !character.spells.length"
        class="col-12"
      >
        <Button
          label="Add spell"
          icon="mdi mdi-plus"
          @click="openSpellEditor"
        />
      </div>
      <div class="col-12">
        <section
          v-if="character.spells.length"
          class="mb-4"
          aria-labelledby="spells-heading"
        >
          <header class="mb-3">
            <div class="d-flex align-items-center justify-content-between gap-3">
              <h2
                id="spells-heading"
                class="h4 mb-1"
              >
                Spells
              </h2>
              <Button
                v-if="canEdit"
                label="Add spell"
                icon="mdi mdi-plus"
                size="small"
                @click="openSpellEditor"
              />
            </div>
            <div
              v-if="character.sheet.spellcasting_classes.length"
              class="d-flex flex-wrap gap-3 small"
            >
              <span
                v-for="spellcastingClass in character.sheet.spellcasting_classes"
                :key="spellcastingClass.name"
              >
                <strong>{{ spellcastingClass.name }}:</strong>
                Spell attack {{ signed(spellcastingClass.spell_attack) }} · Spell save
                DC
                {{ spellcastingClass.spell_save_dc }}
              </span>
            </div>
          </header>
          <div class="row g-3 align-items-start">
            <div
              v-if="spellSlotPools.length"
              class="col-12 col-xl-4"
            >
              <h3 class="h5 mb-3">Spell slots</h3>
              <div class="row row-cols-2 row-cols-md-3 row-cols-lg-5 row-cols-xl-9 g-2">
                <div
                  v-for="slot in spellSlotPools"
                  :key="slot.level"
                  class="col"
                >
                  <article class="border rounded-3 p-2 h-100 text-center">
                    <h4 class="h6 mb-2">{{ spellSlotLabel(slot.level) }}</h4>
                    <span class="small text-body-secondary d-block mb-0">
                      Available
                    </span>
                    <strong class="fs-3 lh-1 tabular-nums">
                      {{ slot.pool.current }} / {{ slot.pool.maximum }}
                    </strong>
                    <p class="small text-body-secondary mb-0 mt-2">
                      {{ spellSlotSource(slot.pool) }}
                    </p>
                  </article>
                </div>
              </div>
            </div>
            <div :class="spellSlotPools.length ? 'col-12 col-xl-8' : 'col-12'">
              <SheetDisclosure
                title="Known spells"
                :count="character.spells.length"
              >
                <ul class="list-group list-group-flush">
                  <li
                    v-for="spell in character.spells"
                    :key="spell.id"
                    class="list-group-item bg-transparent px-0 py-3"
                  >
                    <article class="d-flex align-items-start gap-3">
                      <div class="flex-grow-1">
                        <div class="d-flex align-items-center gap-2 flex-wrap mb-2">
                          <h3 class="h6 mb-0">{{ spell.name }}</h3>
                          <span class="small text-body-secondary">
                            {{ spell.level === 0 ? "Cantrip" : `Level ${spell.level}` }}
                          </span>
                        </div>
                        <dl
                          v-if="spellDetailItems(spell).length"
                          class="row row-cols-1 row-cols-md-2 g-2 small mb-3"
                        >
                          <div
                            v-for="detail in spellDetailItems(spell)"
                            :key="detail.label"
                            class="col"
                          >
                            <dt class="text-body-secondary">{{ detail.label }}</dt>
                            <dd class="mb-0">{{ detail.value }}</dd>
                          </div>
                        </dl>
                        <p
                          v-if="spell.description"
                          class="mb-2 sheet-copy"
                        >
                          {{ spell.description }}
                        </p>
                      </div>
                      <Button
                        v-if="canEdit"
                        icon="mdi mdi-pencil-outline"
                        text
                        rounded
                        size="small"
                        class="flex-shrink-0"
                        :aria-label="`Edit ${spell.name}`"
                        @click="openExistingSpellEditor(spell)"
                      />
                      <Button
                        v-if="canEdit"
                        size="small"
                        text
                        class="flex-shrink-0"
                        :aria-label="`Record casting ${spell.name}`"
                        @click="openSpellCast(spell)"
                      >
                        Cast
                      </Button>
                      <Button
                        v-if="canEdit"
                        icon="mdi mdi-delete-outline"
                        severity="danger"
                        text
                        rounded
                        size="small"
                        class="flex-shrink-0"
                        :aria-label="`Remove ${spell.name}`"
                        @click="askToRemoveSpell(spell)"
                      />
                    </article>
                  </li>
                </ul>
              </SheetDisclosure>
            </div>
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
              v-for="ability in abilityGroups"
              :key="ability.key"
              class="col"
            >
              <Transition
                name="ability-card-flip"
                mode="out-in"
              >
                <article
                  v-if="flippedAbilityKey !== ability.key"
                  :key="`${ability.key}-front`"
                  class="border rounded-3 p-3 h-100 text-center"
                >
                  <header class="mb-3">
                    <h3 class="h5 mb-0">{{ ability.label }}</h3>
                    <span class="small text-uppercase text-body-secondary">
                      {{ ability.abbreviation }} · {{ ability.score }}
                    </span>
                  </header>

                  <div class="row row-cols-2 g-2 align-items-start tabular-nums">
                    <div class="col">
                      <span class="small text-body-secondary d-block mb-1">
                        Modifier
                      </span>
                      <strong class="fs-3 lh-1">
                        {{ signed(ability.modifier) }}
                      </strong>
                    </div>
                    <div class="col">
                      <span class="small text-body-secondary d-block mb-1">Save</span>
                      <div
                        class="d-flex align-items-center justify-content-center gap-1"
                      >
                        <span
                          v-if="ability.save.proficient"
                          class="mdi mdi-shield-check proficiency-bonus"
                          role="img"
                          aria-label="Proficient saving throw"
                          title="Proficient saving throw"
                        />
                        <strong
                          class="fs-3 lh-1"
                          :class="
                            ability.save.proficient
                              ? proficiencyClass('proficient')
                              : undefined
                          "
                        >
                          {{ signed(ability.save.bonus) }}
                        </strong>
                      </div>
                    </div>
                  </div>
                  <Button
                    class="mt-3"
                    size="small"
                    text
                    icon="mdi mdi-rotate-3d-variant"
                    label="Show calculation"
                    :aria-label="`Show ${ability.label} calculation`"
                    @click="showAbilityCalculation(ability.key)"
                  />
                </article>

                <article
                  v-else
                  :key="`${ability.key}-back`"
                  class="border rounded-3 p-3 h-100"
                >
                  <header
                    class="d-flex align-items-start justify-content-between gap-3 mb-3"
                  >
                    <div>
                      <h3 class="h5 mb-0">{{ ability.label }}</h3>
                      <span class="small text-body-secondary">Calculation</span>
                    </div>
                    <Button
                      size="small"
                      text
                      rounded
                      icon="mdi mdi-rotate-3d-variant"
                      :aria-label="`Show ${ability.label} summary`"
                      @click="hideAbilityCalculation"
                    />
                  </header>

                  <CalculationBreakdown
                    :label="`${ability.label} score`"
                    :calculation="ability.calculation"
                    expanded
                  />

                  <dl class="small mb-3 mt-3 pt-3 border-top">
                    <div class="d-flex justify-content-between gap-3">
                      <dt class="text-body-secondary fw-normal">Modifier from score</dt>
                      <dd class="mb-1 fw-semibold tabular-nums">
                        {{ signed(ability.modifierFromScore) }}
                      </dd>
                    </div>
                    <div class="d-flex justify-content-between gap-3">
                      <dt class="text-body-secondary fw-normal">Adjustment</dt>
                      <dd class="mb-0 fw-semibold tabular-nums">
                        {{ signed(ability.modifierAdjustment) }}
                      </dd>
                    </div>
                  </dl>

                  <div class="pt-3 border-top">
                    <CalculationBreakdown
                      :label="`${ability.label} saving throw`"
                      :calculation="ability.save.formula"
                      expanded
                    />
                  </div>

                  <Button
                    class="mt-3"
                    size="small"
                    text
                    icon="mdi mdi-arrow-u-left-top"
                    label="Back to summary"
                    @click="hideAbilityCalculation"
                  />
                </article>
              </Transition>
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
                v-for="(column, columnIndex) in skillColumns"
                :key="columnIndex"
                class="col-6"
              >
                <section
                  class="h-100"
                  :class="columnIndex === 0 ? 'pe-2' : 'ps-2 border-start'"
                >
                  <div
                    v-for="(ability, abilityIndex) in column"
                    :key="ability.key"
                    :class="{ 'mt-4': abilityIndex > 0 }"
                  >
                    <h3 class="h6 text-uppercase text-body-secondary mb-1">
                      {{ ability.label }}
                    </h3>
                    <ul class="list-group list-group-flush">
                      <li
                        v-for="skill in ability.skills"
                        :key="skill.name"
                        class="list-group-item bg-transparent px-0 py-2 d-flex align-items-center justify-content-between gap-3"
                      >
                        <span class="skill-name">{{ displayName(skill.name) }}</span>
                        <span
                          class="d-inline-flex flex-shrink-0 align-items-center gap-1 tabular-nums"
                        >
                          <span
                            v-if="proficiencyIcon(skill.proficiency)"
                            :class="[
                              'mdi',
                              proficiencyIcon(skill.proficiency),
                              'skill-proficiency-icon',
                              {
                                'text-body-secondary': skill.proficiency === 'half',
                              },
                            ]"
                            role="img"
                            :aria-label="proficiencyLabel(skill.proficiency)"
                            :title="proficiencyLabel(skill.proficiency)"
                          />
                          <strong
                            :class="
                              skill.proficiency !== 'none'
                                ? proficiencyClass(skill.proficiency)
                                : undefined
                            "
                          >
                            {{ signed(skill.bonus) }}
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

        <section class="mt-4 border rounded-3 p-3 p-md-4">
          <header class="d-flex align-items-center gap-2 flex-wrap">
            Equipment
            <span class="small text-body-secondary ms-2">
              {{ character.inventory.length }} carried
            </span>
            <span class="flex-grow-1" />
            <Button
              v-if="canAct"
              size="small"
              icon="mdi mdi-plus"
              @click="openAddItemDialog"
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
                  <th scope="col">Type</th>
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
                  <th scope="col">Status</th>
                  <th scope="col">Attunement</th>
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
                  <td>
                    {{
                      displayName(
                        entry.item.equipment.item_type ||
                          entry.item.equipment.category ||
                          "item",
                      )
                    }}
                  </td>
                  <td class="text-end tabular-nums">
                    {{ entry.quantity.toLocaleString() }}
                  </td>
                  <td>{{ entry.equipped ? "Equipped" : "Carried" }}</td>
                  <td>
                    <Button
                      v-if="entry.item.equipment.requires_attunement"
                      size="small"
                      text
                      :icon="
                        entry.is_attuned
                          ? 'mdi mdi-link-variant'
                          : 'mdi mdi-link-variant-off'
                      "
                      :label="entry.is_attuned ? 'Attuned' : 'Attune'"
                      :aria-label="`${entry.is_attuned ? 'Remove attunement from' : 'Attune to'} ${entry.name}`"
                      :disabled="!canEdit || attunementBusyItemId === entry.item_id"
                      @click="toggleItemAttunement(entry)"
                    />
                    <span
                      v-else
                      class="text-body-secondary"
                    >
                      Not required
                    </span>
                  </td>
                  <td class="text-end tabular-nums">
                    {{ formatItemWeight(entry.item) }}
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
              No equipment recorded.
            </span>
          </div>
        </section>
        <section
          v-if="character.effects.length"
          class="mt-4 border rounded-3 p-3 p-md-4"
          aria-labelledby="equipment-heading"
        >
          <header class="d-flex align-items-center gap-2 flex-wrap mb-3">
            <h2
              id="equipment-heading"
              class="h4 mb-0"
            >
              Active effects
            </h2>
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

          <div class="d-grid gap-4">
            <section v-if="character.effects.length">
              <h3 class="h6 mb-2">
                Active effects
                <span class="fw-normal text-body-secondary">
                  {{ character.effects.length }}
                </span>
              </h3>
              <div
                class="table-responsive"
                tabindex="0"
                aria-label="Character active effects table"
              >
                <table class="table table-striped mb-0">
                  <caption class="visually-hidden">
                    Effects applied to {{ character.name }}
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Effect</th>
                      <th scope="col">Duration</th>
                      <th scope="col">Modifiers and reminder</th>
                      <th
                        v-if="canEdit"
                        scope="col"
                        class="text-end"
                      >
                        Actions
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
                        <span
                          v-if="effect.source"
                          class="d-block small fw-normal text-body-secondary"
                        >
                          {{ effect.source }}
                        </span>
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
                      <td
                        v-if="canEdit"
                        class="text-end text-nowrap"
                      >
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
            <SheetDisclosure title="Background and personality">
              <dl
                v-if="biographyFields.length"
                class="row g-3 mb-0"
              >
                <div
                  v-for="field in biographyFields"
                  :key="field.label"
                  :class="field.wide ? 'col-12' : 'col-12 col-md-6'"
                >
                  <dt class="small text-body-secondary mb-1">{{ field.label }}</dt>
                  <dd class="mb-0 sheet-copy">{{ field.value }}</dd>
                </div>
              </dl>
              <p
                v-else
                class="text-body-secondary mb-0"
              >
                No background or personality details recorded.
              </p>
            </SheetDisclosure>

            <SheetDisclosure title="Languages and proficiencies">
              <div
                v-if="character.languages.length || equipmentProficiencyGroups.length"
                class="row g-4"
              >
                <section
                  v-if="character.languages.length"
                  class="col-12 col-md-6"
                  aria-labelledby="languages-heading"
                >
                  <h3
                    id="languages-heading"
                    class="h6 mb-2"
                  >
                    Languages
                  </h3>
                  <p class="mb-0">{{ character.languages.join(", ") }}</p>
                </section>
                <section
                  v-if="equipmentProficiencyGroups.length"
                  class="col-12 col-md-6"
                  aria-labelledby="equipment-proficiencies-heading"
                >
                  <h3
                    id="equipment-proficiencies-heading"
                    class="h6 mb-2"
                  >
                    Equipment proficiencies
                  </h3>
                  <dl class="mb-0">
                    <div
                      v-for="group in equipmentProficiencyGroups"
                      :key="group.label"
                      class="mb-2"
                    >
                      <dt class="small text-body-secondary">{{ group.label }}</dt>
                      <dd class="mb-0">{{ group.values.join(", ") }}</dd>
                    </div>
                  </dl>
                </section>
              </div>
              <p
                v-else
                class="text-body-secondary mb-0"
              >
                No languages or equipment proficiencies recorded.
              </p>
            </SheetDisclosure>

            <SheetDisclosure
              v-if="ownCharacter"
              title="Notes"
              :count="character.notes.length"
            >
              <div
                v-if="!noteEditorOpen"
                class="d-flex justify-content-end mb-3"
              >
                <Button
                  label="Add note"
                  icon="mdi mdi-note-plus-outline"
                  size="small"
                  @click="startAddingNote"
                />
              </div>

              <form
                v-if="noteEditorOpen"
                class="border rounded p-3 mb-3"
                @submit.prevent="saveNote"
              >
                <h3 class="h6 mb-3">
                  {{ editingNoteId === undefined ? "Add note" : "Edit note" }}
                </h3>

                <div class="mb-3">
                  <Textarea
                    id="note-body"
                    v-model="noteBody"
                    class="w-100"
                    rows="5"
                    auto-resize
                    aria-label="Note body"
                  />
                  <div class="form-text">Markdown formatting is supported.</div>
                </div>

                <div class="d-flex flex-wrap justify-content-end gap-2">
                  <Button
                    type="button"
                    label="Cancel"
                    severity="secondary"
                    outlined
                    :disabled="noteBusy"
                    @click="closeNoteEditor"
                  />
                  <Button
                    type="submit"
                    :label="editingNoteId === undefined ? 'Add note' : 'Save note'"
                    icon="mdi mdi-content-save-outline"
                    :loading="noteBusy"
                    :disabled="noteIsEmpty"
                  />
                </div>
              </form>

              <ul
                v-if="character.notes.length"
                class="list-group list-group-flush"
              >
                <li
                  v-for="(note, noteIndex) in character.notes"
                  :key="note.id"
                  class="list-group-item bg-transparent px-0 py-3"
                >
                  <article>
                    <div class="d-flex align-items-start justify-content-between gap-3">
                      <MarkdownContent
                        :source="note.body"
                        class="flex-grow-1 overflow-hidden"
                      />
                      <div
                        v-if="ownCharacter"
                        class="d-flex flex-shrink-0 gap-1"
                      >
                        <Button
                          icon="mdi mdi-pencil-outline"
                          severity="secondary"
                          text
                          rounded
                          size="small"
                          :aria-label="`Edit note ${noteIndex + 1}`"
                          :disabled="noteEditorOpen || noteBusy"
                          @click="startEditingNote(note)"
                        />
                        <Button
                          icon="mdi mdi-delete-outline"
                          severity="danger"
                          text
                          rounded
                          size="small"
                          :aria-label="`Remove note ${noteIndex + 1}`"
                          :disabled="noteEditorOpen || noteBusy"
                          @click="askToRemoveNote(note)"
                        />
                      </div>
                    </div>
                  </article>
                </li>
              </ul>
              <p
                v-else
                class="text-body-secondary mb-0"
              >
                No notes recorded.
              </p>
            </SheetDisclosure>

            <SheetDisclosure
              title="Features and feats"
              :count="character.features.length"
            >
              <ul
                v-if="character.features.length"
                class="list-group list-group-flush"
              >
                <li
                  v-for="feature in character.features"
                  :key="feature.id"
                  class="list-group-item bg-transparent px-0 py-3"
                >
                  <article>
                    <div class="d-flex align-items-start gap-2 flex-wrap mb-2">
                      <h3 class="h6 mb-0">{{ feature.name }}</h3>
                      <span class="small text-body-secondary">
                        {{ displayName(feature.kind) }}
                      </span>
                    </div>
                    <p
                      v-if="feature.description"
                      class="mb-2 sheet-copy"
                    >
                      {{ feature.description }}
                    </p>
                    <p
                      v-if="feature.notes"
                      class="small text-body-secondary mb-0 sheet-copy"
                    >
                      <strong>Notes:</strong>
                      {{ feature.notes }}
                    </p>
                  </article>
                </li>
              </ul>
              <p
                v-else
                class="text-body-secondary mb-0"
              >
                No features or feats recorded.
              </p>
            </SheetDisclosure>

            <SheetDisclosure
              title="Companions"
              :count="character.companions.length"
            >
              <ul
                v-if="character.companions.length"
                class="list-group list-group-flush"
              >
                <li
                  v-for="companion in character.companions"
                  :key="companion.id"
                  class="list-group-item bg-transparent px-0 py-3"
                >
                  <article>
                    <h3 class="h6 mb-3">{{ companion.name }}</h3>
                    <dl class="row g-2 mb-0">
                      <div class="col-4 col-md-auto me-md-4">
                        <dt class="small text-body-secondary">Armor class</dt>
                        <dd class="fs-5 tabular-nums mb-0">
                          {{ companion.armor_class }}
                        </dd>
                      </div>
                      <div class="col-4 col-md-auto me-md-4">
                        <dt class="small text-body-secondary">Hit points</dt>
                        <dd class="fs-5 tabular-nums mb-0">
                          {{ companion.current_hp }} / {{ companion.max_hp }}
                        </dd>
                      </div>
                      <div class="col-4 col-md-auto">
                        <dt class="small text-body-secondary">Speed</dt>
                        <dd class="fs-5 tabular-nums mb-0">
                          {{ companion.speed || "—" }}
                        </dd>
                      </div>
                    </dl>
                    <p
                      v-if="companion.notes"
                      class="small text-body-secondary mt-3 mb-0 sheet-copy"
                    >
                      <strong>Notes:</strong>
                      {{ companion.notes }}
                    </p>
                  </article>
                </li>
              </ul>
              <p
                v-else
                class="text-body-secondary mb-0"
              >
                No companions recorded.
              </p>
            </SheetDisclosure>
          </div>
        </section>
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
            :loading="itemsLoading"
            remote-search
            label="Item"
            no-data-text="No campaign items available."
            @search="searchAvailableItems"
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
      v-model:visible="nativeBehaviourOpen"
      header="System behaviour"
      :style="{ width: 'min(40rem, calc(100vw - 2rem))' }"
    >
      <p class="text-body-secondary">
        This control comes from the active RPG Companion system. Hoard executes its
        event and mechanics against authoritative native character state, then updates
        the familiar sheet fields as read-only projections.
      </p>
      <dl v-if="nativeBehaviourNode">
        <dt>Control</dt>
        <dd>{{ displayName(String(nativeBehaviourNode.id ?? "native control")) }}</dd>
        <dt>Event</dt>
        <dd>
          <code>{{ nativeBehaviourEvent }}</code>
        </dd>
      </dl>
      <Message
        v-if="!nativeBehaviourEvent"
        severity="warn"
      >
        This native view does not expose a directly executable event. Hoard keeps the
        control visible so unsupported behaviour is not silently omitted.
      </Message>
    </Dialog>
    <Dialog
      v-model:visible="nativeResourcePickerOpen"
      :header="`Add ${displayName(nativeResourceKind || 'resource')}`"
      :style="{ width: 'min(38rem, calc(100vw - 2rem))' }"
    >
      <div class="d-flex gap-2 mb-3">
        <InputText
          v-model="nativeResourceQuery"
          placeholder="Search enabled Compendium content"
          fluid
          @keyup.enter.prevent="searchNativeResources"
        />
        <Button
          label="Search"
          icon="mdi mdi-magnify"
          @click="searchNativeResources"
        />
      </div>
      <div class="list-group">
        <button
          v-for="entry in nativeResourceResults"
          :key="entry.id"
          type="button"
          class="list-group-item list-group-item-action text-start"
          @click="attachNativeResource(entry.id)"
        >
          <strong>{{ entry.name }}</strong>
          <span class="small text-body-secondary ms-2">{{ entry.source }}</span>
        </button>
      </div>
      <Message
        v-if="!nativeResourceResults.length"
        severity="info"
        class="mb-0"
      >
        Search the enabled Compendium for this native resource type.
      </Message>
    </Dialog>
    <Dialog
      v-model:visible="noteRemoveOpen"
      modal
      header="Remove note?"
      :style="{ width: 'min(30rem, calc(100vw - 2rem))' }"
      @update:visible="closeNoteRemovalWhenClosed"
    >
      <p class="mb-4">Remove this note? This cannot be undone.</p>
      <footer class="d-flex flex-wrap justify-content-end gap-2">
        <Button
          label="Cancel"
          severity="secondary"
          outlined
          :disabled="noteBusy"
          @click="closeNoteRemoval"
        />
        <Button
          label="Remove note"
          icon="mdi mdi-delete-outline"
          severity="danger"
          :loading="noteBusy"
          @click="removeNote"
        />
      </footer>
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
      v-model:visible="spellEditorOpen"
      :style="{ width: 'min(35rem, calc(100vw - 2rem))' }"
    >
      <form
        class="d-grid gap-3"
        @submit.prevent="saveSpell"
      >
        <h2 class="h3 mb-0">
          {{ editingSpell ? `Edit ${editingSpell.name}` : "Add spell" }}
        </h2>
        <div
          v-if="!editingSpell"
          class="d-flex gap-2"
        >
          <InputText
            v-model="spellQuery"
            placeholder="Search the compendium"
            fluid
            @keyup.enter.prevent="searchSpells"
          />
          <Button
            type="button"
            label="Search"
            :loading="spellBusy"
            @click="searchSpells"
          />
        </div>
        <div
          v-if="!editingSpell && spellResults.length"
          class="list-group"
        >
          <button
            v-for="result in spellResults"
            :key="result.id"
            type="button"
            class="list-group-item list-group-item-action text-start"
            @click="addCompendiumSpell(result.id)"
          >
            <strong>{{ result.name }}</strong>
            <span class="small text-body-secondary ms-2">{{ result.source }}</span>
          </button>
        </div>
        <p
          v-if="!editingSpell"
          class="small text-body-secondary mb-0"
        >
          Choose an existing spell, or create a campaign-custom spell below.
        </p>
        <Message
          v-else-if="!editingSpell.is_custom"
          severity="info"
        >
          Published Compendium content is immutable. Saving creates a campaign-custom
          copy and switches only this character to it.
        </Message>
        <div v-else>
          <label
            for="spell-edit-mode"
            class="form-label"
          >
            Apply changes
          </label>
          <Select
            id="spell-edit-mode"
            v-model="spellEditMode"
            :options="spellEditModes"
            option-label="label"
            option-value="value"
            fluid
          />
          <div class="form-text">
            Shared updates affect every character using this custom spell. A copy only
            changes this character.
          </div>
        </div>
        <div>
          <label
            for="spell-name"
            class="form-label"
          >
            Name
          </label>
          <InputText
            id="spell-name"
            v-model="spellName"
            fluid
            autofocus
          />
        </div>
        <div>
          <label
            for="spell-level"
            class="form-label"
          >
            Spell level
          </label>
          <InputNumber
            input-id="spell-level"
            v-model.number="spellLevel"
            :min="0"
            :max="9"
            :step="1"
            show-buttons
            fluid
          />
          <div class="form-text">Use 0 for a cantrip.</div>
        </div>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-casting-time"
            >
              Casting time
            </label>
            <InputText
              id="spell-casting-time"
              v-model="spellCastingTime"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-range"
            >
              Range
            </label>
            <InputText
              id="spell-range"
              v-model="spellRange"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-target"
            >
              Target
            </label>
            <InputText
              id="spell-target"
              v-model="spellTarget"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-components"
            >
              Components
            </label>
            <InputText
              id="spell-components"
              v-model="spellComponents"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-materials"
            >
              Materials
            </label>
            <InputText
              id="spell-materials"
              v-model="spellMaterials"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-duration"
            >
              Duration
            </label>
            <InputText
              id="spell-duration"
              v-model="spellDuration"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-school"
            >
              School
            </label>
            <InputText
              id="spell-school"
              v-model="spellSchool"
              fluid
            />
          </div>
          <div class="col-12 col-md-6">
            <label
              class="form-label"
              for="spell-classes"
            >
              Classes
            </label>
            <InputText
              id="spell-classes"
              v-model="spellClasses"
              fluid
            />
          </div>
        </div>
        <div class="d-flex flex-wrap gap-3">
          <div class="form-check">
            <input
              id="spell-concentration"
              v-model="spellConcentration"
              class="form-check-input"
              type="checkbox"
            />
            <label
              class="form-check-label"
              for="spell-concentration"
            >
              Concentration
            </label>
          </div>
          <div class="form-check">
            <input
              id="spell-ritual"
              v-model="spellRitual"
              class="form-check-input"
              type="checkbox"
            />
            <label
              class="form-check-label"
              for="spell-ritual"
            >
              Ritual
            </label>
          </div>
        </div>
        <div>
          <label
            for="spell-description"
            class="form-label"
          >
            Description
          </label>
          <Textarea
            id="spell-description"
            v-model="spellDescription"
            rows="5"
            auto-resize
            fluid
          />
        </div>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            type="button"
            label="Cancel"
            severity="secondary"
            outlined
            :disabled="spellBusy"
            @click="spellEditorOpen = false"
          />
          <Button
            type="submit"
            :label="editingSpell ? 'Save spell' : 'Add spell'"
            :icon="editingSpell ? 'mdi mdi-content-save-outline' : 'mdi mdi-plus'"
            :loading="spellBusy"
            :disabled="!spellName.trim()"
          />
        </footer>
      </form>
    </Dialog>
    <Dialog
      v-model:visible="spellRemoveOpen"
      :style="{ width: 'min(29rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="remove-spell-heading"
      >
        <h2
          id="remove-spell-heading"
          class="h3 mb-0"
        >
          Remove spell?
        </h2>
        <p class="mb-0">Remove {{ spellToRemove?.name }}? This cannot be undone.</p>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            :disabled="spellBusy"
            @click="closeSpellRemoval"
          />
          <Button
            label="Remove spell"
            icon="mdi mdi-delete-outline"
            severity="danger"
            :loading="spellBusy"
            @click="removeSpell"
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
      v-model:visible="speedOpen"
      :style="{ width: 'min(26rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="edit-speed-heading"
      >
        <h2
          id="edit-speed-heading"
          class="h3 mb-0"
        >
          Edit movement speed
        </h2>
        <label class="form-label mb-0">
          Walking speed
          <InputNumber
            v-model.number="speedFeet"
            input-id="character-speed"
            :min="0"
            :max="1000"
            :step="5"
            :invalid="speedFeet !== null && speedFeet % 5 !== 0"
            suffix=" ft"
            show-buttons
            button-layout="horizontal"
            fluid
          >
            <template #decrementicon>
              <span aria-hidden="true">−5</span>
            </template>
            <template #incrementicon>
              <span aria-hidden="true">+5</span>
            </template>
          </InputNumber>
          <small class="d-block text-body-secondary mt-1">
            Enter a multiple of 5 feet.
          </small>
        </label>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="speedOpen = false"
          />
          <Button
            label="Save speed"
            :disabled="speedInvalid"
            @click="saveSpeed"
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
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import type { MenuItem } from "primevue/menuitem";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { defineComponent } from "vue";
import {
  archiveCharacter,
  attachCharacterNativeResource,
  castCharacterSpell,
  changeCharacterSheetRecord,
  createCompendiumSpell,
  editCharacterSpell,
  executeCharacterNativeEvent,
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  detachCharacterNativeResource,
  getCampaign,
  getTransactions,
  postHealth,
  removeCharacterCondition,
  removeCharacterPortrait,
  restCharacter,
  searchItems,
  searchCompendiumEntries,
  setCharacterCondition,
  setCharacterDeathSaves,
  setCharacterItemAttunement,
  setCharacterInspiration,
  stabilizeCharacter,
  updateCharacter,
  uploadCharacterPortrait,
  type Campaign,
  type Character,
  type CharacterNote,
  type ConditionMutation,
  type Item,
  type LedgerTransaction,
  type CompendiumSearchEntry,
  type NativeViewNode,
} from "@/api";
import { exchangedCoinAmount } from "@/campaigns/coinExchange";
import {
  readCoinDisplayMode,
  storeCoinDisplayMode,
} from "@/campaigns/coinDisplayPreference";
import ActionMenu from "@/campaigns/components/ActionMenu.vue";
import CalculationBreakdown from "@/campaigns/components/CalculationBreakdown.vue";
import CalculationCard from "@/campaigns/components/CalculationCard.vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import CoinAmountPicker from "@/campaigns/components/CoinAmountPicker.vue";
import ConditionManager from "@/campaigns/components/ConditionManager.vue";
import ItemPickerDialog from "@/campaigns/components/ItemPickerDialog.vue";
import MarkdownContent from "@/campaigns/components/MarkdownContent.vue";
import PlayerEncounterActions from "@/campaigns/components/PlayerEncounterActions.vue";
import RelativeTime from "@/components/RelativeTime.vue";
import SheetDisclosure from "@/campaigns/components/SheetDisclosure.vue";
import { displayCoin, displayIdentifier, formatCoinPouch } from "@/campaigns/display";
import type { PickerCandidate } from "@/campaigns/itemPicker";
import { formatGoldValue, formatMoneyValue } from "@/campaigns/money";
import { campaignRefreshRevision } from "@/realtime";

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
    CalculationCard,
    Dialog,
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
    MarkdownContent,
    PlayerEncounterActions,
    RelativeTime,
    SheetDisclosure,
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
      itemsLoading: false,
      itemSearchSequence: 0,
      attunementBusyItemId: undefined as number | undefined,
      deathSaveBusy: false,
      stabilizationBusy: false,
      deathSaveKinds: ["successes", "failures"] as const,
      flippedAbilityKey: "",
      moneyValueVisible: readCoinDisplayMode() === "value",
      error: typeof levelUpError === "string" ? levelUpError : "",
      nativeBehaviourOpen: false,
      nativeBehaviourNode: undefined as NativeViewNode | undefined,
      nativeResourcePickerOpen: false,
      nativeResourceKind: "",
      nativeResourceQuery: "",
      nativeResourceResults: [] as CompendiumSearchEntry[],
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
      speedOpen: false,
      speedFeet: null as number | null,
      healthReason: "damage" as "damage" | "healing" | "temporary" | "correction",
      healthAmount: 1,
      healthCurrent: 0,
      healthTemporary: 0,
      healthDescription: "",
      shortRestOpen: false,
      shortRestHp: 0,
      spellEditorOpen: false,
      editingSpell: undefined as Character["spells"][number] | undefined,
      spellEditMode: "shared" as "shared" | "clone",
      spellEditModes: [
        { label: "Update shared custom spell", value: "shared" },
        { label: "Clone for this character", value: "clone" },
      ],
      spellRemoveOpen: false,
      spellBusy: false,
      spellToRemove: undefined as Character["spells"][number] | undefined,
      spellName: "",
      spellLevel: 0,
      spellDescription: "",
      spellQuery: "",
      spellResults: [] as CompendiumSearchEntry[],
      spellCastingTime: "",
      spellRange: "",
      spellTarget: "",
      spellComponents: "",
      spellDuration: "",
      spellSchool: "",
      spellMaterials: "",
      spellClasses: "",
      spellConcentration: false,
      spellRitual: false,
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
      noteEditorOpen: false,
      editingNoteId: undefined as number | undefined,
      noteBody: "",
      noteBusy: false,
      noteRemoveOpen: false,
      noteToRemove: undefined as CharacterNote | undefined,
      denominations: denominationOptions,
      xpThresholds,
      effectTargets: effectTargetOptions,
    };
  },
  computed: {
    nativeExtensionSections(): Character["native_sheet"]["sections"] {
      const customSections = new Set([
        "avatar",
        "conditions",
        "status",
        "abilities",
        "saving_throws",
        "skills",
        "equipment",
        "weapons",
        "features",
        "notes",
        "spell_slots",
        "spells",
        "companions",
      ]);

      return (this.character?.native_sheet.sections ?? []).filter(
        (section) => !customSections.has(section.id),
      );
    },
    nativeBehaviourEvent(): string {
      const event = this.nativeBehaviourNode?.system_behaviour?.event;
      if (typeof event === "string") {
        return event;
      }
      if (typeof event === "object" && event !== null) {
        const name = (event as Record<string, unknown>).name;
        if (typeof name === "object" && name !== null && "formula" in name) {
          return String((name as Record<string, unknown>).value ?? "");
        }

        return String(name ?? "");
      }

      return "";
    },
    characterActionItems(): MenuItem[] {
      const items: MenuItem[] = [];

      if (this.character?.has_inspiration) {
        items.push({
          label: "Use inspiration",
          icon: "mdi mdi-star",
          command: () => void this.toggleInspiration(),
        });
      } else if (this.campaign?.is_game_master) {
        items.push({
          label: "Award inspiration",
          icon: "mdi mdi-star-outline",
          command: () => void this.toggleInspiration(),
        });
      }

      items.push({
        label: "Add condition",
        icon: "mdi mdi-bandage",
        command: () => this.openConditionManager(),
      });

      if (this.needsStabilization) {
        items.push({
          label: "Stabilize",
          icon: "mdi mdi-medical-bag",
          command: () => void this.stabilize(),
        });
      } else {
        items.push(
          {
            label: "Short rest",
            icon: "mdi mdi-weather-sunset",
            command: () => this.openShortRest(),
          },
          {
            label: "Long rest",
            icon: "mdi mdi-weather-night",
            command: () => void this.takeRest("long"),
          },
        );
      }

      items.push(
        { separator: true },
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
      );

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
      const items: MenuItem[] = [
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
        { separator: true },
      ];

      if (this.needsStabilization) {
        items.push({
          label: "Stabilize",
          icon: "mdi mdi-medical-bag",
          command: () => void this.stabilize(),
        });
      } else {
        items.push(
          {
            label: "Short rest",
            icon: "mdi mdi-weather-sunset",
            command: () => this.openShortRest(),
          },
          {
            label: "Long rest",
            icon: "mdi mdi-weather-night",
            command: () => void this.takeRest("long"),
          },
        );
      }

      return items;
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
      const loadoutByItem = new Map(
        (this.character?.loadout ?? []).map((entry) => [entry.item_id, entry]),
      );

      return (this.character?.inventory ?? []).map((entry) => {
        const loadout = loadoutByItem.get(entry.item_id);

        return {
          ...entry,
          item: entry.item,
          equipped: loadout?.equipped ?? false,
          slot: loadout?.slot ?? "other",
        };
      });
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
    noteIsEmpty(): boolean {
      return !this.noteBody.trim();
    },
    canDamage(): boolean {
      const sheet = this.character?.sheet;

      return Boolean(sheet && (sheet.current_hp > 0 || sheet.temporary_hp > 0));
    },
    canHeal(): boolean {
      const sheet = this.character?.sheet;

      return Boolean(sheet && sheet.current_hp < sheet.max_hp);
    },
    needsStabilization(): boolean {
      return Boolean(
        this.character &&
        (this.character.sheet.current_hp === 0 || this.character.is_dead),
      );
    },
    movementSpeedLabel(): string {
      const speed = this.character?.sheet.speed.trim();

      if (!speed) {
        return "Not set";
      }

      return /^\d+$/.test(speed) ? `${speed} ft` : speed;
    },
    speedInvalid(): boolean {
      return (
        this.speedFeet === null ||
        !Number.isInteger(this.speedFeet) ||
        this.speedFeet < 0 ||
        this.speedFeet > 1000 ||
        this.speedFeet % 5 !== 0
      );
    },
    spellSlotPools() {
      if (!this.character) {
        return [];
      }

      return Object.entries(this.character.sheet.spell_slot_pools).map(
        ([level, pool]) => ({ level, pool }),
      );
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

      return [
        ["strength", "Strength", "STR"],
        ["dexterity", "Dexterity", "DEX"],
        ["constitution", "Constitution", "CON"],
        ["intelligence", "Intelligence", "INT"],
        ["wisdom", "Wisdom", "WIS"],
        ["charisma", "Charisma", "CHA"],
      ].map(([key, label, abbreviation]) => {
        const ability = character.sheet.abilities[key];
        const save = character.sheet.saves[key];

        return {
          key,
          label,
          abbreviation,
          score: ability.score,
          calculation: ability.formula,
          modifier: ability.modifier,
          modifierFromScore: ability.modifier - ability.adjustment,
          modifierAdjustment: ability.adjustment,
          save,
          skills: Object.entries(character.sheet.skills)
            .filter(([name]) => skillAbilities[name] === key)
            .map(([name, skill]) => ({ name, ...skill })),
        };
      });
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
    biographyFields(): Array<{ label: string; value: string; wide: boolean }> {
      if (!this.character) {
        return [];
      }

      return [
        { label: "Background", value: this.character.background, wide: false },
        { label: "Alignment", value: this.character.alignment, wide: false },
        { label: "About", value: this.character.about, wide: true },
        {
          label: "Personality traits",
          value: this.character.personality_traits,
          wide: true,
        },
        { label: "Ideals", value: this.character.ideals, wide: true },
        { label: "Bonds", value: this.character.bonds, wide: true },
        { label: "Flaws", value: this.character.flaws, wide: true },
      ].filter((field) => field.value.trim());
    },
    equipmentProficiencyGroups(): Array<{ label: string; values: string[] }> {
      if (!this.character) {
        return [];
      }

      return Object.entries(this.character.equipment_proficiencies)
        .map(([group, values]) => ({
          label: displayIdentifier(group),
          values: values.map(displayIdentifier),
        }))
        .filter((group) => group.values.length);
    },
  },
  watch: {
    refreshRevision(): void {
      void this.load();
    },
  },
  methods: {
    deathSaveCount(kind: "successes" | "failures"): number {
      return this.character?.death_saves[kind].filter(Boolean).length ?? 0;
    },
    deathSaveTargetCount(kind: "successes" | "failures", index: number): number {
      const currentValue = this.character?.death_saves[kind][index] ?? false;

      return currentValue ? index : index + 1;
    },
    async toggleDeathSave(
      kind: "successes" | "failures",
      index: number,
    ): Promise<void> {
      if (!this.character || this.deathSaveBusy || !this.canEdit) {
        return;
      }

      const targetCount = this.deathSaveTargetCount(kind, index);
      this.deathSaveBusy = true;

      try {
        await setCharacterDeathSaves(
          this.campaignId,
          this.character.id,
          kind,
          targetCount,
        );
        this.showSuccess(
          `${targetCount} ${kind === "successes" ? "success" : "failure"}${targetCount === 1 ? "" : "s"} marked.`,
        );
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to update death saving throws.";
      } finally {
        this.deathSaveBusy = false;
      }
    },
    async stabilize(): Promise<void> {
      if (!this.character || !this.canEdit || this.stabilizationBusy) {
        return;
      }

      this.stabilizationBusy = true;
      this.error = "";

      try {
        await stabilizeCharacter(this.campaignId, this.character.id);
        await this.load();
        this.showSuccess("Character stabilized at 1 HP and is prone.");
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to stabilize this character.";
      } finally {
        this.stabilizationBusy = false;
      }
    },
    async toggleItemAttunement(entry: InventoryRow): Promise<void> {
      if (!this.character || this.attunementBusyItemId || !this.canEdit) {
        return;
      }

      this.attunementBusyItemId = entry.item_id;

      try {
        await setCharacterItemAttunement(
          this.campaignId,
          this.character.id,
          entry.item_id,
          !entry.is_attuned,
        );
        this.showSuccess(entry.is_attuned ? "Attunement removed." : "Item attuned.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to change attunement.";
      } finally {
        this.attunementBusyItemId = undefined;
      }
    },
    showNativeBehaviour(node: NativeViewNode): void {
      this.nativeBehaviourNode = node;
      this.nativeBehaviourOpen = true;
    },
    async openNativeResourcePicker(kind: string): Promise<void> {
      this.nativeResourceKind = kind;
      this.nativeResourceQuery = "";
      this.nativeResourceResults = [];
      this.nativeResourcePickerOpen = true;
      await this.searchNativeResources();
    },
    async searchNativeResources(): Promise<void> {
      if (!this.nativeResourceKind) {
        return;
      }

      try {
        this.nativeResourceResults = await searchCompendiumEntries(
          this.campaignId,
          this.nativeResourceKind,
          this.nativeResourceQuery,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to search native resources.";
      }
    },
    async attachNativeResource(entryId: number): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await attachCharacterNativeResource(
          this.campaignId,
          this.character.id,
          entryId,
        );
        this.nativeResourcePickerOpen = false;
        this.showSuccess("Resource attached.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to attach resource.";
      }
    },
    async detachNativeResource(entryId: number): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        await detachCharacterNativeResource(
          this.campaignId,
          this.character.id,
          entryId,
        );
        this.showSuccess("Resource detached. Compendium content was kept.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to detach resource.";
      }
    },
    async runNativeControl(control: {
      eventName: string;
      viewValues?: Record<string, unknown>;
      statUpdates?: Record<string, unknown>;
    }): Promise<void> {
      if (!this.character) {
        return;
      }

      try {
        const result = await executeCharacterNativeEvent(
          this.campaignId,
          this.character.id,
          control.eventName,
          {
            view_values: control.viewValues,
            stat_updates: control.statUpdates,
          },
        );
        const message = result.messages.at(-1);
        this.showSuccess(
          typeof message?.message === "string"
            ? message.message
            : "System action applied.",
        );
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to apply the system action.";
      }
    },
    showAbilityCalculation(abilityKey: string): void {
      this.flippedAbilityKey = abilityKey;
    },
    hideAbilityCalculation(): void {
      this.flippedAbilityKey = "";
    },
    toggleMoneyCard(): void {
      this.moneyValueVisible = !this.moneyValueVisible;
      storeCoinDisplayMode(this.moneyValueVisible ? "value" : "pouch");
    },
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
    formatItemWeight(item: Item | null | undefined): string {
      const amount = item?.equipment.weight_amount;

      if (!amount) {
        return "—";
      }

      const numericAmount = Number(amount);
      const formattedAmount = Number.isFinite(numericAmount)
        ? numericAmount.toLocaleString()
        : amount;
      const unit = item.equipment.weight_unit;

      return unit ? `${formattedAmount} ${unit}` : formattedAmount;
    },
    signed(value: number): string {
      return value >= 0 ? `+${value}` : `${value}`;
    },
    spellSlotLabel(level: string): string {
      return level.startsWith("pact-")
        ? `Pact level ${level.slice(5)}`
        : `Level ${level}`;
    },
    spellSlotSource(pool: Character["sheet"]["spell_slot_pools"][string]): string {
      if (pool.adjustment) {
        return `Class ${pool.calculated}, adjustment ${this.signed(pool.adjustment)}`;
      }

      return `Class ${pool.calculated}`;
    },
    spellDetailItems(spell: Character["spells"][number]): Array<{
      label: string;
      value: string;
    }> {
      const fields: Array<{ label: string; keys: string[] }> = [
        { label: "Casting time", keys: ["castingTime", "casting_time"] },
        { label: "Range", keys: ["range"] },
        { label: "Target", keys: ["target"] },
        { label: "Components", keys: ["components"] },
        { label: "Duration", keys: ["duration"] },
        { label: "School", keys: ["school"] },
        { label: "Classes", keys: ["classes"] },
      ];

      return fields.flatMap((field) => {
        const value = this.spellDetailValue(
          spell as unknown as Record<string, unknown>,
          field.keys,
        );

        if (value === undefined || value === null || value === "") {
          return [];
        }

        return [{ label: field.label, value: this.formatSpellDetail(value) }];
      });
    },
    spellDetailValue(details: Record<string, unknown>, keys: string[]): unknown {
      for (const key of keys) {
        if (Object.hasOwn(details, key)) {
          return details[key];
        }
      }

      return undefined;
    },
    formatSpellDetail(value: unknown): string {
      if (Array.isArray(value)) {
        return value.map((item) => this.formatSpellDetail(item)).join(", ");
      }

      if (typeof value === "object" && value !== null) {
        const detail = value as Record<string, unknown>;
        const displayValue =
          detail.name ?? detail.label ?? detail.value ?? detail.description;

        return displayValue === undefined ? "—" : this.formatSpellDetail(displayValue);
      }

      return String(value);
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
    proficiencyIcon(proficiency: string): string {
      return (
        {
          half: "mdi-circle-half-full",
          proficient: "mdi-shield-check",
          expertise: "mdi-star-four-points",
        }[proficiency] ?? ""
      );
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
    openSpellEditor(): void {
      this.editingSpell = undefined;
      this.spellEditMode = "shared";
      this.spellName = "";
      this.spellLevel = 0;
      this.spellDescription = "";
      this.spellQuery = "";
      this.spellResults = [];
      this.spellCastingTime = "";
      this.spellRange = "";
      this.spellTarget = "";
      this.spellComponents = "";
      this.spellMaterials = "";
      this.spellDuration = "";
      this.spellSchool = "";
      this.spellClasses = "";
      this.spellConcentration = false;
      this.spellRitual = false;
      this.spellEditorOpen = true;
    },
    openExistingSpellEditor(spell: Character["spells"][number]): void {
      this.editingSpell = spell;
      this.spellEditMode = spell.is_custom ? "shared" : "clone";
      this.spellName = spell.name;
      this.spellLevel = spell.level;
      this.spellDescription = spell.description;
      this.spellCastingTime = spell.casting_time;
      this.spellRange = spell.range;
      this.spellTarget = spell.target;
      this.spellComponents = spell.components;
      this.spellMaterials = spell.materials;
      this.spellDuration = spell.duration;
      this.spellSchool = spell.school;
      this.spellClasses = spell.classes.join(", ");
      this.spellConcentration = spell.concentration;
      this.spellRitual = spell.ritual;
      this.spellQuery = "";
      this.spellResults = [];
      this.spellEditorOpen = true;
    },
    async searchSpells(): Promise<void> {
      if (this.spellBusy) {
        return;
      }

      this.spellBusy = true;

      try {
        this.spellResults = await searchCompendiumEntries(
          this.campaignId,
          "spell",
          this.spellQuery,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to search spells.";
      } finally {
        this.spellBusy = false;
      }
    },
    async addCompendiumSpell(entryId: number): Promise<void> {
      if (!this.character || this.spellBusy) {
        return;
      }

      this.spellBusy = true;

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "spells",
          "create",
          {
            catalogue_entry_id: entryId,
          },
        );
        this.spellEditorOpen = false;
        this.showSuccess("Spell added.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to add spell.";
      } finally {
        this.spellBusy = false;
      }
    },
    async saveSpell(): Promise<void> {
      if (!this.character || !this.spellName.trim() || this.spellBusy) {
        return;
      }

      this.spellBusy = true;

      try {
        const card = {
          name: this.spellName.trim(),
          level: this.spellLevel,
          school: this.spellSchool.trim(),
          casting_time: this.spellCastingTime.trim(),
          range: this.spellRange.trim(),
          target: this.spellTarget.trim(),
          components: this.spellComponents.trim(),
          materials: this.spellMaterials.trim(),
          duration: this.spellDuration.trim(),
          concentration: this.spellConcentration,
          ritual: this.spellRitual,
          classes: this.spellClasses
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          description: this.spellDescription.trim(),
        };
        if (this.editingSpell) {
          await editCharacterSpell(
            this.campaignId,
            this.character.id,
            this.editingSpell.id,
            this.editingSpell.is_custom ? this.spellEditMode : "clone",
            card,
          );
          this.spellEditorOpen = false;
          this.showSuccess(`${this.spellName.trim()} saved.`);
          await this.load();
          return;
        }
        const entry = await createCompendiumSpell(this.campaignId, card);
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "spells",
          "create",
          {
            catalogue_entry_id: entry.id,
          },
        );
        this.spellEditorOpen = false;
        this.showSuccess(`${this.spellName.trim()} added.`);
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to add spell.";
      } finally {
        this.spellBusy = false;
      }
    },
    askToRemoveSpell(spell: Character["spells"][number]): void {
      this.spellToRemove = spell;
      this.spellRemoveOpen = true;
    },
    closeSpellRemoval(): void {
      if (this.spellBusy) {
        return;
      }

      this.spellRemoveOpen = false;
      this.spellToRemove = undefined;
    },
    async removeSpell(): Promise<void> {
      if (!this.character || !this.spellToRemove || this.spellBusy) {
        return;
      }

      const spell = this.spellToRemove;
      this.spellBusy = true;

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "spells",
          "delete",
          {},
          spell.id,
        );
        this.spellRemoveOpen = false;
        this.spellToRemove = undefined;
        this.showSuccess(`${spell.name} removed.`);
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to remove spell.";
      } finally {
        this.spellBusy = false;
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
    startAddingNote(): void {
      this.editingNoteId = undefined;
      this.noteBody = "";
      this.noteEditorOpen = true;
    },
    startEditingNote(note: CharacterNote): void {
      this.editingNoteId = note.id;
      this.noteBody = note.body;
      this.noteEditorOpen = true;
    },
    closeNoteEditor(): void {
      if (this.noteBusy) {
        return;
      }

      this.noteEditorOpen = false;
      this.editingNoteId = undefined;
      this.noteBody = "";
    },
    async saveNote(): Promise<void> {
      if (!this.character || this.noteIsEmpty || this.noteBusy) {
        return;
      }

      const operation = this.editingNoteId === undefined ? "create" : "update";

      this.noteBusy = true;

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "notes",
          operation,
          {
            body: this.noteBody.trim(),
          },
          this.editingNoteId,
        );
        this.noteEditorOpen = false;
        this.editingNoteId = undefined;
        this.noteBody = "";
        this.showSuccess(operation === "create" ? "Note added." : "Note updated.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to save note.";
      } finally {
        this.noteBusy = false;
      }
    },
    askToRemoveNote(note: CharacterNote): void {
      this.noteToRemove = note;
      this.noteRemoveOpen = true;
    },
    closeNoteRemoval(): void {
      if (this.noteBusy) {
        return;
      }

      this.noteRemoveOpen = false;
      this.noteToRemove = undefined;
    },
    closeNoteRemovalWhenClosed(open: boolean): void {
      if (!open) {
        this.closeNoteRemoval();
      }
    },
    async removeNote(): Promise<void> {
      if (!this.character || !this.noteToRemove || this.noteBusy) {
        return;
      }

      this.noteBusy = true;

      try {
        await changeCharacterSheetRecord(
          this.campaignId,
          this.character.id,
          "notes",
          "delete",
          {},
          this.noteToRemove.id,
        );
        this.noteRemoveOpen = false;
        this.noteToRemove = undefined;
        this.showSuccess("Note removed.");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to remove note.";
      } finally {
        this.noteBusy = false;
      }
    },
    async load(): Promise<void> {
      try {
        const [nextCampaign, recent] = await Promise.all([
          getCampaign(this.campaignId),
          getTransactions(this.campaignId, "all", 1, this.characterId),
        ]);

        this.campaign = nextCampaign;
        this.characters = nextCampaign.characters;
        this.character = nextCampaign.characters.find(
          (candidate) => candidate.id === this.characterId,
        );
        this.ownCharacter = this.character?.context_id === this.campaignId;

        if (this.ownCharacter && this.character && !this.character.is_build_complete) {
          await this.$router.replace(
            `/c/${this.campaignId}/characters/${this.characterId}/build`,
          );
          return;
        }

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
    openAddItemDialog(): void {
      this.addItemOpen = true;
    },
    async searchAvailableItems(query: string): Promise<void> {
      const sequence = ++this.itemSearchSequence;
      this.itemsLoading = true;

      try {
        const items = await searchItems(this.campaignId, query);

        if (sequence === this.itemSearchSequence) {
          this.items = items;
        }
      } catch (exception) {
        if (sequence === this.itemSearchSequence) {
          this.error =
            exception instanceof Error
              ? exception.message
              : "Unable to search campaign items.";
        }
      } finally {
        if (sequence === this.itemSearchSequence) {
          this.itemsLoading = false;
        }
      }
    },
    async toggleInspiration(): Promise<void> {
      if (!this.character) {
        return;
      }

      const inspirationWasAvailable = this.character.has_inspiration;

      try {
        this.character = await setCharacterInspiration(
          this.campaignId,
          this.character.id,
          !this.character.has_inspiration,
        );
        this.showSuccess(
          inspirationWasAvailable ? "Inspiration used." : "Inspiration awarded.",
        );
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to update inspiration.";
      }
    },
    openConditionManager(): void {
      const conditionManager = this.$refs.conditionManager as
        { openNewCondition: () => void } | undefined;

      conditionManager?.openNewCondition();
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
    openSpeedEditor(): void {
      const distance = this.character?.sheet.speed.match(/\d+/)?.[0];

      this.speedFeet = distance ? Number(distance) : null;
      this.speedOpen = true;
    },
    async saveSpeed(): Promise<void> {
      if (!this.character || this.speedInvalid) {
        return;
      }

      const speed = String(this.speedFeet as number);

      try {
        await updateCharacter(this.campaignId, this.character.id, { speed });
        this.character = {
          ...this.character,
          sheet: { ...this.character.sheet, speed },
        };
        this.speedOpen = false;
        this.showSuccess("Movement speed updated.");
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to update movement speed.";
      }
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
  font-weight: var(--bs-body-font-weight);
}

.skill-proficiency-icon {
  color: var(--hoard-gold);
}

.skill-name {
  min-width: 0;
}

.sheet-copy {
  overflow-wrap: anywhere;
  white-space: pre-line;
}

.death-save-toggle {
  border: 0;
  border-radius: 50%;
  padding: 0.125rem;
  background: transparent;
  color: currentColor;
  font-size: 1.5rem;
  line-height: 1;
}

.death-save-toggle:focus-visible {
  outline: 0.2rem solid var(--bs-focus-ring-color);
  outline-offset: 0.1rem;
}

.death-save-toggle:disabled {
  opacity: 0.65;
}

.ability-card-flip-enter-active,
.ability-card-flip-leave-active {
  transition:
    transform 140ms ease,
    opacity 140ms ease;
  transform-origin: center;
}

.ability-card-flip-enter-from {
  opacity: 0;
  transform: rotateY(90deg);
}

.ability-card-flip-leave-to {
  opacity: 0;
  transform: rotateY(-90deg);
}

@media (prefers-reduced-motion: reduce) {
  .ability-card-flip-enter-active,
  .ability-card-flip-leave-active {
    transition: none;
  }
}

@media (min-width: 576px) {
  .coin-value-column {
    border-top: 0 !important;
    border-left: var(--bs-border-width) var(--bs-border-style) var(--bs-border-color) !important;
  }
}
</style>
