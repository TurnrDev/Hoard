<template>
  <section
    v-if="character && campaign"
    aria-labelledby="character-title"
  >
    <PlayerEncounterActions
      v-if="canAct && campaign.encounter"
      :context-id="campaignId"
      :character-id="character.id"
      :current-combatant-id="campaign.encounter.current_combatant_id"
      :combatants="campaign.encounter.combatants"
    />

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

    <div class="row g-3 mb-4">
      <div class="col-12">
        <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xxl-6 g-3">
          <div class="col">
            <section class="border rounded-3 p-3 p-md-4 h-100">
              <Transition
                name="money-card-flip"
                mode="out-in"
              >
                <div
                  v-if="!moneyValueVisible"
                  key="coin-pouch"
                >
                  <header
                    class="d-flex align-items-start justify-content-between gap-2"
                  >
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
                  <header
                    class="d-flex align-items-start justify-content-between gap-2"
                  >
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
                  <div class="h4 mt-3 mb-0">
                    {{ formatGoldValue(character.money.gold_value) }} ¤
                  </div>
                </div>
              </Transition>
            </section>
          </div>
          <div class="col">
            <CalculationCard
              label="HP"
              :summary="`${character.sheet.current_hp} / ${character.sheet.max_hp}`"
              :calculation="character.sheet.hp_calculation"
              :interactive="canEdit"
              activation-label="Adjust hit points"
              calculation-label="Maximum HP"
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
            </CalculationCard>
          </div>
          <div class="col">
            <ComingSoonBlock>
              <section class="border rounded-3 p-3 p-md-4 h-100">
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Armor class
                </div>
                <Skeleton
                  class="mt-3"
                  width="4.5rem"
                  height="1.75rem"
                />
                <Button
                  class="mt-3"
                  size="small"
                  text
                  icon="mdi mdi-rotate-3d-variant"
                  label="Show calculation"
                  aria-label="Show Armor class calculation"
                />
              </section>
            </ComingSoonBlock>
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
            <ComingSoonBlock>
              <section class="border rounded-3 p-3 p-md-4 h-100">
                <div class="text-uppercase fw-semibold small text-body-secondary">
                  Movement speed
                </div>
                <div class="d-flex align-items-center gap-2 mt-3">
                  <span
                    class="mdi mdi-run fs-4"
                    aria-hidden="true"
                  />
                  <Skeleton
                    width="5rem"
                    height="1.75rem"
                  />
                </div>
              </section>
            </ComingSoonBlock>
          </div>
        </div>
      </div>

      <div class="col-12">
        <ComingSoonBlock>
          <section
            class="border rounded-3 p-3 p-md-4"
            aria-labelledby="conditions-heading"
          >
            <header class="mb-3">
              <h2
                id="conditions-heading"
                class="h5 mb-1"
              >
                Conditions
              </h2>
              <p class="small text-body-secondary mb-0">
                Conditions remain active until each cause is removed.
              </p>
            </header>
            <div class="d-flex align-items-start gap-2">
              <Skeleton
                shape="circle"
                size="1.5rem"
              />
              <div class="flex-grow-1 d-grid gap-2">
                <Skeleton width="8rem" />
                <Skeleton width="14rem" />
              </div>
            </div>
          </section>
        </ComingSoonBlock>
      </div>

      <div class="col-12">
        <ComingSoonBlock>
          <section class="mb-4">
            <header>Resources</header>
            <p class="mb-3 d-flex flex-wrap column-gap-4 row-gap-2">
              <span class="d-inline-flex align-items-center gap-2">
                Inspiration:
                <Skeleton width="5rem" />
              </span>
              <span class="d-inline-flex align-items-center gap-2">
                Spell attack:
                <Skeleton width="2rem" />
              </span>
              <span class="d-inline-flex align-items-center gap-2">
                Spell save DC:
                <Skeleton width="2rem" />
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
        </ComingSoonBlock>
      </div>
    </div>

    <section class="character-sheet-preview">
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
            :key="ability.label"
            class="col"
          >
            <AbilityCard
              :label="ability.label"
              :abbreviation="ability.abbreviation"
              :ability="character.sheet.abilities[ability.key]"
              :save="character.sheet.saves[ability.key]"
            />
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
              v-for="(column, columnIndex) in deferredSkillColumns"
              :key="columnIndex"
              class="col-6"
            >
              <section
                class="h-100"
                :class="columnIndex === 0 ? 'pe-2' : 'ps-2 border-start'"
              >
                <div
                  v-for="(group, groupIndex) in column"
                  :key="group.label"
                  :class="{ 'mt-4': groupIndex > 0 }"
                >
                  <h3 class="h6 text-uppercase text-body-secondary mb-1">
                    {{ group.label }}
                  </h3>
                  <ul class="list-group list-group-flush">
                    <li
                      v-for="skill in group.skills"
                      :key="skill"
                      class="list-group-item bg-transparent px-0 py-2 d-flex align-items-center justify-content-between gap-3"
                    >
                      <span class="skill-name">{{ skill }}</span>
                      <span
                        class="d-inline-flex flex-shrink-0 align-items-center gap-1 tabular-nums"
                      >
                        <span
                          v-if="
                            proficiencyIcon(
                              character.sheet.skills[skillKey(skill)].proficiency,
                            )
                          "
                          :class="[
                            'mdi',
                            proficiencyIcon(
                              character.sheet.skills[skillKey(skill)].proficiency,
                            ),
                            'skill-proficiency-icon',
                          ]"
                          role="img"
                          :aria-label="
                            proficiencyLabel(
                              character.sheet.skills[skillKey(skill)].proficiency,
                            )
                          "
                          :title="
                            proficiencyLabel(
                              character.sheet.skills[skillKey(skill)].proficiency,
                            )
                          "
                        />
                        <strong
                          :class="
                            character.sheet.skills[skillKey(skill)].proficiency !==
                            'none'
                              ? proficiencyClass(
                                  character.sheet.skills[skillKey(skill)].proficiency,
                                )
                              : undefined
                          "
                        >
                          {{ signed(character.sheet.skills[skillKey(skill)].bonus) }}
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

      <ComingSoonBlock class="mt-4">
        <section class="border rounded-3 p-3 p-md-4">
          <header class="d-flex align-items-center gap-2 flex-wrap">
            Inventory
            <Skeleton width="4rem" />
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
      </ComingSoonBlock>

      <ComingSoonBlock class="mt-4">
        <section
          class="border rounded-3 p-3 p-md-4"
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
          <div class="d-grid gap-4">
            <section>
              <h3 class="h6 mb-2">
                Equipment
                <Skeleton
                  class="d-inline-block"
                  width="2rem"
                />
              </h3>
              <div class="table-responsive">
                <table class="table table-striped mb-0">
                  <caption class="visually-hidden">Character equipment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Item</th>
                      <th scope="col">Slot</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <th scope="row"><Skeleton width="8rem" /></th>
                      <td><Skeleton width="5rem" /></td>
                      <td><Skeleton width="5rem" /></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
            <section>
              <h3 class="h6 mb-2">
                Active effects
                <Skeleton
                  class="d-inline-block"
                  width="2rem"
                />
              </h3>
              <div class="table-responsive">
                <table class="table table-striped mb-0">
                  <caption class="visually-hidden">Character active effects</caption>
                  <thead>
                    <tr>
                      <th scope="col">Effect</th>
                      <th scope="col">Duration</th>
                      <th scope="col">Modifiers and reminder</th>
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
                      <td><Skeleton width="5rem" /></td>
                      <td><Skeleton width="10rem" /></td>
                      <td>
                        <Skeleton
                          class="ms-auto"
                          width="3rem"
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </section>
      </ComingSoonBlock>

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
          <ComingSoonBlock>
            <SheetDisclosure title="Background and personality">
              <dl class="row g-3 mb-0">
                <div
                  v-for="field in deferredBiographyFields"
                  :key="field.label"
                  :class="field.wide ? 'col-12' : 'col-12 col-md-6'"
                >
                  <dt class="small text-body-secondary mb-1">{{ field.label }}</dt>
                  <dd class="mb-0">
                    <Skeleton :width="field.wide ? '75%' : '10rem'" />
                  </dd>
                </div>
              </dl>
            </SheetDisclosure>
          </ComingSoonBlock>

          <ComingSoonBlock>
            <SheetDisclosure title="Languages and proficiencies">
              <div class="row g-4">
                <section class="col-12 col-md-6">
                  <h3 class="h6 mb-2">Languages</h3>
                  <Skeleton width="75%" />
                </section>
                <section class="col-12 col-md-6">
                  <h3 class="h6 mb-2">Equipment proficiencies</h3>
                  <Skeleton width="85%" />
                </section>
              </div>
            </SheetDisclosure>
          </ComingSoonBlock>

          <ComingSoonBlock>
            <SheetDisclosure title="Notes">
              <Skeleton
                width="80%"
                height="3rem"
              />
            </SheetDisclosure>
          </ComingSoonBlock>

          <ComingSoonBlock>
            <SheetDisclosure title="Features and feats">
              <article>
                <Skeleton
                  width="10rem"
                  class="mb-2"
                />
                <Skeleton width="85%" />
              </article>
            </SheetDisclosure>
          </ComingSoonBlock>

          <ComingSoonBlock>
            <SheetDisclosure title="Spells">
              <article>
                <Skeleton
                  width="9rem"
                  class="mb-2"
                />
                <Skeleton width="80%" />
              </article>
            </SheetDisclosure>
          </ComingSoonBlock>

          <ComingSoonBlock>
            <SheetDisclosure title="Companions">
              <article>
                <Skeleton
                  width="9rem"
                  class="mb-3"
                />
                <dl class="row g-2 mb-0">
                  <div
                    v-for="stat in ['Armor class', 'Hit points', 'Speed']"
                    :key="stat"
                    class="col-4 col-md-auto me-md-4"
                  >
                    <dt class="small text-body-secondary">{{ stat }}</dt>
                    <dd class="mb-0"><Skeleton width="4rem" /></dd>
                  </div>
                </dl>
              </article>
            </SheetDisclosure>
          </ComingSoonBlock>
        </div>
      </section>
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

    <Dialog
      v-model:visible="editorOpen"
      modal
      :header="
        profileSetupRequired ? 'Set up your character' : 'Edit character profile'
      "
      :style="{ width: 'min(72rem, calc(100vw - 2rem))' }"
    >
      <form
        class="d-grid gap-3"
        @submit.prevent="saveProfile"
      >
        <p
          v-if="profileSetupRequired"
          class="text-body-secondary mb-0"
        >
          Choose your character's name, race, and class. Saving makes the character
          active.
        </p>
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
            :required="profileSetupRequired"
            maxlength="100"
            fluid
          />
        </label>
        <label class="d-grid gap-2">
          <span class="fw-semibold">Class</span>
          <InputText
            v-model="draft.characterClass"
            :required="profileSetupRequired"
            maxlength="100"
            fluid
          />
        </label>
        <section class="border-top pt-3">
          <h3 class="h5">HP</h3>
          <div class="row g-3">
            <label class="col-12 col-md-4 d-grid gap-2">
              <span class="fw-semibold">Rolled Hit Points</span>
              <InputNumber
                v-model.number="draft.rolledHitPoints"
                :min="1"
                :max="99999"
                show-buttons
                fluid
              />
            </label>
            <label class="col-12 col-md-4 d-grid gap-2">
              <span class="fw-semibold">HP custom modifier</span>
              <InputNumber
                v-model.number="draft.hpAdjustment"
                :min="-32768"
                :max="32767"
                show-buttons
                fluid
              />
            </label>
            <div class="col-12 col-md-4 border rounded-3 p-3">
              <strong>Maximum HP: {{ draftMaxHp }}</strong>
              <div class="small text-body-secondary tabular-nums mt-1">
                {{ draft.rolledHitPoints }} + ({{
                  draftAbilityModifier("constitution")
                }}
                × {{ campaign.level }}) + {{ draft.hpAdjustment }} = {{ draftMaxHp }}
              </div>
            </div>
          </div>
        </section>
        <section class="border-top pt-3">
          <h3 class="h5">Initiative and proficiency</h3>
          <div class="row g-3 align-items-end">
            <label class="col-12 col-md-4 d-grid gap-2">
              <span class="fw-semibold">Initiative custom modifier</span>
              <InputNumber
                v-model.number="draft.initiativeAdjustment"
                :min="-32768"
                :max="32767"
                show-buttons
                fluid
              />
              <small class="text-body-secondary tabular-nums">
                DEX {{ signed(draftAbilityModifier("dexterity")) }} + feature
                {{ signed(draftInitiativeFeature) }} + custom
                {{ signed(draft.initiativeAdjustment) }} =
                <strong>{{ signed(draftInitiative) }}</strong>
              </small>
            </label>
            <label class="col-12 col-md-4 d-grid gap-2">
              <span class="fw-semibold">Proficiency custom modifier</span>
              <InputNumber
                v-model.number="draft.proficiencyAdjustment"
                :min="-32768"
                :max="32767"
                show-buttons
                fluid
              />
              <small class="text-body-secondary tabular-nums">
                Level {{ campaign.level }} base {{ signed(draftBaseProficiency) }} +
                custom {{ signed(draft.proficiencyAdjustment) }} =
                <strong>{{ signed(draftProficiency) }}</strong>
              </small>
            </label>
          </div>
          <fieldset class="border rounded-3 p-3 mt-3">
            <legend class="float-none w-auto h6 mb-2">Non-proficient checks</legend>
            <label class="d-flex align-items-start gap-2 mb-3">
              <input
                v-model="draft.jackOfAllTrades"
                type="checkbox"
              />
              <span>
                <strong class="d-block">Jack of All Trades</strong>
                <small class="text-body-secondary">
                  Half proficiency, rounded down, on otherwise non-proficient ability
                  checks.
                </small>
              </span>
            </label>
            <label class="d-flex align-items-start gap-2">
              <input
                v-model="draft.remarkableAthlete"
                type="checkbox"
              />
              <span>
                <strong class="d-block">Remarkable Athlete</strong>
                <small class="text-body-secondary">
                  Half proficiency, rounded up, on otherwise non-proficient Strength,
                  Dexterity, and Constitution checks. Contributions never stack.
                </small>
              </span>
            </label>
          </fieldset>
        </section>
        <section class="border-top pt-3">
          <h3 class="h5">Abilities and saving throws</h3>
          <div class="row g-3">
            <fieldset
              v-for="ability in deferredAbilities"
              :key="ability.key"
              class="col-12 border rounded-3 p-3"
            >
              <legend class="float-none w-auto h6 mb-2">{{ ability.label }}</legend>
              <div class="row g-2">
                <label
                  v-for="field in abilityFields"
                  :key="field.key"
                  class="col-6 col-lg-3 d-grid gap-1"
                >
                  <span class="small fw-semibold">{{ field.label }}</span>
                  <InputNumber
                    v-model.number="draft.abilities[ability.key][field.key]"
                    :min="field.key === 'rolled' ? 1 : -30"
                    :max="field.key === 'rolled' ? 30 : 30"
                    show-buttons
                    fluid
                  />
                </label>
              </div>
              <div class="small text-body-secondary tabular-nums mt-2">
                Score {{ draftAbilityScore(ability.key) }} · modifier
                {{ signed(draftAbilityModifier(ability.key)) }} · ability check
                {{ signed(draftAbilityCheck(ability.key)) }}
              </div>
              <div class="row g-2 mt-2 align-items-end">
                <SkillProficiencyPicker
                  v-model="draft.saves[ability.key].proficiency"
                  class="col-8"
                  :input-id="`save-${ability.key}`"
                  label="Saving throw"
                  :allow-expertise="false"
                />
                <label class="col-4 d-grid gap-1">
                  <span class="small fw-semibold">Custom</span>
                  <InputNumber
                    v-model.number="draft.saves[ability.key].adjustment"
                    :min="-99"
                    :max="99"
                    show-buttons
                    fluid
                  />
                </label>
              </div>
              <div class="small text-body-secondary tabular-nums mt-2">
                Saving throw:
                <strong>{{ signed(draftSaveBonus(ability.key)) }}</strong>
              </div>
            </fieldset>
          </div>
        </section>
        <section class="border-top pt-3">
          <h3 class="h5">Skills</h3>
          <div class="row g-3">
            <div
              v-for="(skill, name) in draft.skills"
              :key="name"
              class="col-12 col-md-6 border rounded-3 p-3"
            >
              <SkillProficiencyPicker
                v-model="skill.proficiency"
                :input-id="`skill-${name}`"
                :label="displayIdentifier(String(name))"
              />
              <div class="small text-body-secondary mt-1">
                {{ displayIdentifier(skillAbility(String(name))) }} check
              </div>
              <label class="d-grid gap-1 mt-2">
                <span class="small fw-semibold">Custom modifier</span>
                <InputNumber
                  v-model.number="skill.adjustment"
                  :min="-99"
                  :max="99"
                  show-buttons
                  fluid
                />
              </label>
              <div class="small text-body-secondary tabular-nums mt-2">
                Result:
                <strong>{{ signed(draftSkillBonus(String(name))) }}</strong>
              </div>
            </div>
          </div>
        </section>
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

    <Dialog
      v-model:visible="hpAdjustmentOpen"
      modal
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
        <p class="mb-0">
          Current HP: {{ character.sheet.current_hp }} / {{ character.sheet.max_hp }}
        </p>
        <label class="d-grid gap-2">
          <span class="fw-semibold">Hit points</span>
          <InputNumber
            v-model.number="healthAmount"
            :min="1"
            :step="1"
            show-buttons
            fluid
          />
        </label>
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
            :disabled="healthAmount < 1"
            @click="submitHpAdjustment('damage')"
          />
          <Button
            label="Heal"
            :disabled="healthAmount < 1"
            @click="submitHpAdjustment('healing')"
          />
        </footer>
      </section>
    </Dialog>

    <Dialog
      v-model:visible="healthOpen"
      modal
      :style="{ width: 'min(33rem, calc(100vw - 2rem))' }"
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="health-heading"
      >
        <h2
          id="health-heading"
          class="h3 mb-0"
        >
          Record HP change
        </h2>
        <label class="d-grid gap-2">
          <span class="fw-semibold">Action</span>
          <Select
            v-model="healthReason"
            :options="healthReasonOptions"
            option-label="title"
            option-value="value"
            fluid
          />
        </label>
        <label
          v-if="healthReason !== 'correction'"
          class="d-grid gap-2"
        >
          <span class="fw-semibold">Amount</span>
          <InputNumber
            v-model.number="healthAmount"
            :min="1"
            :step="1"
            show-buttons
            fluid
          />
        </label>
        <template v-else>
          <label class="d-grid gap-2">
            <span class="fw-semibold">Correct current HP</span>
            <InputNumber
              v-model.number="healthCurrent"
              :min="0"
              show-buttons
              fluid
            />
          </label>
          <label class="d-grid gap-2">
            <span class="fw-semibold">Correct temporary HP</span>
            <InputNumber
              v-model.number="healthTemporary"
              :min="0"
              show-buttons
              fluid
            />
          </label>
        </template>
        <Message severity="info">
          {{ healthPreview }}
        </Message>
        <label class="d-grid gap-2">
          <span class="fw-semibold">Reason (optional)</span>
          <Textarea
            v-model="healthDescription"
            rows="2"
            fluid
          />
        </label>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="healthOpen = false"
          />
          <Button
            label="Apply"
            :loading="busy"
            @click="saveHealth"
          />
        </footer>
      </section>
    </Dialog>

    <Dialog
      v-model:visible="shortRestOpen"
      modal
      :style="{ width: 'min(30rem, calc(100vw - 2rem))' }"
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
        <p class="mb-0">
          Enter the HP regained from Hit Die rolls. Temporary HP is cleared.
        </p>
        <label class="d-grid gap-2">
          <span class="fw-semibold">HP regained</span>
          <InputNumber
            v-model.number="shortRestRecovery"
            :min="0"
            :step="1"
            show-buttons
            fluid
          />
        </label>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="shortRestOpen = false"
          />
          <Button
            label="Take short rest"
            :loading="busy"
            :disabled="inCombat"
            @click="takeShortRest"
          />
        </footer>
      </section>
    </Dialog>
  </section>

  <ProgressBar
    v-else-if="!error"
    indeterminate
    aria-label="Loading character profile"
  />
</template>

<script lang="ts">
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
  postHealth,
  takeRest,
  updateCharacter,
  uploadCharacterPortrait,
  type Campaign,
  type Character,
  type LedgerTransaction,
} from "@/api";
import { exchangedCoinAmount } from "@/campaigns/coinExchange";
import ActionMenu from "@/campaigns/components/ActionMenu.vue";
import AbilityCard from "@/campaigns/components/AbilityCard.vue";
import CalculationCard from "@/campaigns/components/CalculationCard.vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import CoinAmountPicker from "@/campaigns/components/CoinAmountPicker.vue";
import ComingSoonBlock from "@/campaigns/components/ComingSoonBlock.vue";
import PlayerEncounterActions from "@/campaigns/components/PlayerEncounterActions.vue";
import SheetDisclosure from "@/campaigns/components/SheetDisclosure.vue";
import SkillProficiencyPicker from "@/campaigns/components/SkillProficiencyPicker.vue";
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
    AbilityCard,
    ActionMenu,
    Button,
    CalculationCard,
    CharacterAvatar,
    CoinAmountPicker,
    ComingSoonBlock,
    Dialog,
    InputNumber,
    InputText,
    Message,
    ProgressBar,
    PlayerEncounterActions,
    RelativeTime,
    Select,
    SheetDisclosure,
    SkillProficiencyPicker,
    Skeleton,
    Textarea,
  },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      character: undefined as Character | undefined,
      editorOpen: false,
      setupPrompted: false,
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
      healthOpen: false,
      hpAdjustmentOpen: false,
      healthReason: "damage" as "damage" | "healing" | "temporary" | "correction",
      healthAmount: 1,
      healthCurrent: 0,
      healthTemporary: 0,
      healthDescription: "",
      healthReasonOptions: [
        { title: "Damage", value: "damage" },
        { title: "Healing", value: "healing" },
        { title: "Temporary HP change", value: "temporary" },
        { title: "Correction", value: "correction" },
      ],
      shortRestOpen: false,
      shortRestRecovery: 0,
      draft: {
        name: "",
        race: "",
        characterClass: "",
        rolledHitPoints: 1,
        hpAdjustment: 0,
        initiativeAdjustment: 0,
        proficiencyAdjustment: 0,
        jackOfAllTrades: false,
        remarkableAthlete: false,
        abilities: {} as Record<string, Record<string, number>>,
        saves: {} as Record<string, { proficiency: string; adjustment: number }>,
        skills: {} as Record<string, { proficiency: string; adjustment: number }>,
      },
      abilityFields: [
        { key: "rolled", label: "Rolled" },
        { key: "ancestry", label: "Ancestry" },
        { key: "background", label: "Background" },
        { key: "custom", label: "Custom" },
      ],
      deferredAbilities: [
        { key: "strength", label: "Strength", abbreviation: "STR" },
        { key: "dexterity", label: "Dexterity", abbreviation: "DEX" },
        { key: "constitution", label: "Constitution", abbreviation: "CON" },
        { key: "intelligence", label: "Intelligence", abbreviation: "INT" },
        { key: "wisdom", label: "Wisdom", abbreviation: "WIS" },
        { key: "charisma", label: "Charisma", abbreviation: "CHA" },
      ],
      deferredSkillColumns: [
        [
          { label: "Strength", skills: ["Athletics"] },
          {
            label: "Dexterity",
            skills: ["Acrobatics", "Sleight of hand", "Stealth"],
          },
          {
            label: "Intelligence",
            skills: ["Arcana", "History", "Investigation", "Nature", "Religion"],
          },
        ],
        [
          {
            label: "Wisdom",
            skills: [
              "Animal handling",
              "Insight",
              "Medicine",
              "Perception",
              "Survival",
            ],
          },
          {
            label: "Charisma",
            skills: ["Deception", "Intimidation", "Performance", "Persuasion"],
          },
        ],
      ],
      deferredBiographyFields: [
        { label: "Background", wide: false },
        { label: "Alignment", wide: false },
        { label: "About", wide: true },
        { label: "Personality traits", wide: true },
        { label: "Ideals", wide: true },
        { label: "Bonds", wide: true },
        { label: "Flaws", wide: true },
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
    profileSetupRequired(): boolean {
      return Boolean(
        this.character &&
        this.character.context_id === this.campaignId &&
        !this.character.is_active,
      );
    },
    inCombat(): boolean {
      return Boolean(this.campaign?.encounter);
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
          icon: "mdi mdi-cash-sync",
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
        { separator: true },
        {
          label: "Short rest",
          icon: "mdi mdi-weather-sunset",
          disabled: this.inCombat,
          command: () => {
            this.shortRestRecovery = 0;
            this.shortRestOpen = true;
          },
        },
        {
          label: "Long rest",
          icon: "mdi mdi-weather-night",
          disabled: this.inCombat,
          command: () => void this.takeLongRest(),
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
    draftBaseProficiency(): number {
      return 2 + Math.floor(((this.campaign?.level ?? 1) - 1) / 4);
    },
    draftProficiency(): number {
      return this.draftBaseProficiency + this.draft.proficiencyAdjustment;
    },
    draftInitiativeFeature(): number {
      return this.draftHalfProficiency("dexterity");
    },
    draftInitiative(): number {
      return (
        this.draftAbilityModifier("dexterity") +
        this.draftInitiativeFeature +
        this.draft.initiativeAdjustment
      );
    },
    draftMaxHp(): number {
      return Math.max(
        1,
        this.draft.rolledHitPoints +
          this.draftAbilityModifier("constitution") * (this.campaign?.level ?? 1) +
          this.draft.hpAdjustment,
      );
    },
    healthPreview(): string {
      if (!this.character) {
        return "";
      }

      const current = this.character.sheet.current_hp;
      const temporary = this.character.sheet.temporary_hp;

      if (this.healthReason === "correction") {
        return `Current ${current} → ${this.healthCurrent}; temporary ${temporary} → ${this.healthTemporary}`;
      }

      if (this.healthReason === "damage") {
        const absorbed = Math.min(temporary, this.healthAmount);
        const nextTemporary = temporary - absorbed;
        const nextCurrent = Math.max(0, current - (this.healthAmount - absorbed));

        return `Current ${current} → ${nextCurrent}; temporary ${temporary} → ${nextTemporary}`;
      }

      if (this.healthReason === "healing") {
        const nextCurrent = Math.min(
          this.character.sheet.max_hp,
          current + this.healthAmount,
        );

        return `Current ${current} → ${nextCurrent}`;
      }

      return `Temporary HP ${temporary} → ${Math.max(0, temporary + this.healthAmount)}`;
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
    displayIdentifier,
    formatCoinPouch,
    formatGoldValue,
    formatXp(value: number): string {
      return `${value.toLocaleString()} XP`;
    },
    signed(value: number): string {
      return value >= 0 ? `+${value}` : `−${Math.abs(value)}`;
    },
    skillKey(value: string): string {
      return value.toLowerCase().replaceAll(" ", "_");
    },
    proficiencyLabel(proficiency: string): string {
      return (
        {
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
          proficient: "mdi-shield-check",
          expertise: "mdi-star-four-points",
        }[proficiency] ?? ""
      );
    },
    draftAbilityScore(ability: string): number {
      const values = this.draft.abilities[ability];

      if (!values) {
        return 10;
      }

      return values.rolled + values.ancestry + values.background + values.custom;
    },
    draftAbilityModifier(ability: string): number {
      return Math.floor((this.draftAbilityScore(ability) - 10) / 2);
    },
    draftAbilityCheck(ability: string): number {
      return this.draftAbilityModifier(ability) + this.draftHalfProficiency(ability);
    },
    draftHalfProficiency(ability: string): number {
      const jackOfAllTrades = this.draft.jackOfAllTrades
        ? Math.floor(this.draftProficiency / 2)
        : 0;
      const remarkableAthlete =
        this.draft.remarkableAthlete &&
        ["strength", "dexterity", "constitution"].includes(ability)
          ? Math.ceil(this.draftProficiency / 2)
          : 0;

      return Math.max(jackOfAllTrades, remarkableAthlete);
    },
    draftSaveBonus(ability: string): number {
      const save = this.draft.saves[ability];
      const proficiency =
        save?.proficiency === "proficient" ? this.draftProficiency : 0;

      return this.draftAbilityModifier(ability) + proficiency + (save?.adjustment ?? 0);
    },
    skillAbility(skill: string): string {
      const abilities: Record<string, string> = {
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

      return abilities[skill] ?? "strength";
    },
    draftSkillBonus(skillName: string): number {
      const skill = this.draft.skills[skillName];
      const ability = this.skillAbility(skillName);
      let proficiency: number;

      if (skill?.proficiency === "proficient") {
        proficiency = this.draftProficiency;
      } else if (skill?.proficiency === "expertise") {
        proficiency = this.draftProficiency * 2;
      } else {
        proficiency = this.draftHalfProficiency(ability);
      }

      return (
        this.draftAbilityModifier(ability) + proficiency + (skill?.adjustment ?? 0)
      );
    },
    openHealthFor(reason: "damage" | "healing" | "temporary" | "correction"): void {
      this.healthReason = reason;
      this.healthAmount = 1;
      this.healthCurrent = this.character?.sheet.current_hp ?? 0;
      this.healthTemporary = this.character?.sheet.temporary_hp ?? 0;
      this.healthDescription = "";
      this.healthOpen = true;
    },
    openHpAdjustment(): void {
      this.healthAmount = 1;
      this.hpAdjustmentOpen = true;
    },
    async submitHpAdjustment(reason: "damage" | "healing"): Promise<void> {
      this.healthReason = reason;
      await this.saveHealth();
      this.hpAdjustmentOpen = false;
    },
    async saveHealth(): Promise<void> {
      if (!this.character) {
        return;
      }
      this.busy = true;
      try {
        await postHealth(this.campaignId, {
          character_id: this.character.id,
          reason: this.healthReason,
          description: this.healthDescription,
          ...(this.healthReason === "correction"
            ? {
                current_hp: this.healthCurrent,
                temporary_hp: this.healthTemporary,
              }
            : this.healthReason === "damage"
              ? { current_hp_delta: -Math.abs(this.healthAmount) }
              : this.healthReason === "healing"
                ? { current_hp_delta: Math.abs(this.healthAmount) }
                : { temporary_hp_delta: this.healthAmount }),
        });
        this.healthOpen = false;
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to update HP.";
      } finally {
        this.busy = false;
      }
    },
    async takeShortRest(): Promise<void> {
      if (!this.character || this.inCombat) {
        return;
      }
      this.busy = true;
      try {
        await takeRest(
          this.campaignId,
          this.character.id,
          "short",
          this.shortRestRecovery,
        );
        this.shortRestOpen = false;
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to take a short rest.";
      } finally {
        this.busy = false;
      }
    },
    async takeLongRest(): Promise<void> {
      if (!this.character || this.inCombat) {
        return;
      }
      this.busy = true;
      try {
        await takeRest(this.campaignId, this.character.id, "long");
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to take a long rest.";
      } finally {
        this.busy = false;
      }
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

        if (this.profileSetupRequired && !this.setupPrompted) {
          this.setupPrompted = true;
          this.openEditor();
        }
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
        rolledHitPoints: this.character.sheet.rolled_hit_points,
        hpAdjustment: this.character.sheet.hp_adjustment,
        initiativeAdjustment: this.character.sheet.initiative_adjustment,
        proficiencyAdjustment: this.character.sheet.proficiency_bonus_adjustment,
        jackOfAllTrades: this.character.sheet.jack_of_all_trades,
        remarkableAthlete: this.character.sheet.remarkable_athlete,
        abilities: Object.fromEntries(
          Object.entries(this.character.sheet.abilities).map(([name, ability]) => [
            name,
            {
              rolled: ability.raw,
              ancestry: ability.ancestry_bonus,
              background: ability.background_bonus,
              custom: ability.score_adjustment,
            },
          ]),
        ),
        saves: Object.fromEntries(
          Object.entries(this.character.sheet.saves).map(([name, save]) => [
            name,
            {
              proficiency: save.proficiency,
              adjustment: save.adjustment,
            },
          ]),
        ),
        skills: Object.fromEntries(
          Object.entries(this.character.sheet.skills).map(([name, skill]) => [
            name,
            {
              proficiency: skill.proficiency,
              adjustment: skill.adjustment,
            },
          ]),
        ),
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
          rolled_hit_points: this.draft.rolledHitPoints,
          hp_adjustment: this.draft.hpAdjustment,
          initiative_adjustment: this.draft.initiativeAdjustment,
          proficiency_bonus_adjustment: this.draft.proficiencyAdjustment,
          jack_of_all_trades: this.draft.jackOfAllTrades,
          remarkable_athlete: this.draft.remarkableAthlete,
          ...Object.fromEntries(
            Object.entries(this.draft.abilities).map(([name, value]) => [
              name,
              value.rolled,
            ]),
          ),
          ability_bonuses: Object.fromEntries(
            Object.entries(this.draft.abilities).map(([name, value]) => [
              name,
              value.ancestry,
            ]),
          ),
          background_ability_bonuses: Object.fromEntries(
            Object.entries(this.draft.abilities).map(([name, value]) => [
              name,
              value.background,
            ]),
          ),
          ability_score_adjustments: Object.fromEntries(
            Object.entries(this.draft.abilities).map(([name, value]) => [
              name,
              value.custom,
            ]),
          ),
          save_proficiencies: Object.fromEntries(
            Object.entries(this.draft.saves).map(([name, value]) => [
              name,
              value.proficiency,
            ]),
          ),
          save_adjustments: Object.fromEntries(
            Object.entries(this.draft.saves).map(([name, value]) => [
              name,
              value.adjustment,
            ]),
          ),
          skill_proficiencies: Object.fromEntries(
            Object.entries(this.draft.skills).map(([name, value]) => [
              name,
              value.proficiency,
            ]),
          ),
          skill_adjustments: Object.fromEntries(
            Object.entries(this.draft.skills).map(([name, value]) => [
              name,
              value.adjustment,
            ]),
          ),
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
.skill-name {
  min-width: 0;
}

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
