<template>
  <section
    v-if="!triggerOnly"
    class="border rounded-3 p-3 p-md-4"
    aria-labelledby="conditions-heading"
  >
    <header class="d-flex align-items-center justify-content-between gap-3 mb-3">
      <div>
        <h2
          id="conditions-heading"
          class="h5 mb-1"
        >
          Conditions
        </h2>
        <p class="small text-body-secondary mb-0">
          Conditions remain active until each cause is removed.
        </p>
      </div>
      <Button
        v-if="canEdit && showTrigger"
        label="Add condition"
        icon="mdi mdi-plus"
        size="small"
        @click="openNewCondition"
      />
    </header>

    <p
      v-if="conditions.length === 0"
      class="text-body-secondary mb-0"
    >
      No active conditions.
    </p>
    <ul
      v-else
      class="list-group list-group-flush"
      :aria-label="`${targetName} active conditions`"
    >
      <li
        v-for="condition in conditions"
        :key="condition.id"
        class="list-group-item bg-transparent px-0 py-3"
      >
        <div class="d-flex align-items-start gap-2">
          <span
            :class="['mdi', conditionIcon(condition.id), 'fs-5']"
            aria-hidden="true"
          />
          <div class="flex-grow-1 min-width-0">
            <strong>
              {{ condition.label }}
              <span v-if="condition.exhaustion_level !== null">
                level {{ condition.exhaustion_level }}
              </span>
            </strong>
            <ul class="list-unstyled mb-0 mt-1">
              <li
                v-for="instance in condition.instances"
                :key="instance.id"
                class="d-flex align-items-center justify-content-between gap-2 py-1"
              >
                <span class="small text-body-secondary">
                  {{ causeDescription(instance.source, instance.duration) }}
                </span>
                <span
                  v-if="canEdit"
                  class="d-flex flex-shrink-0 gap-1"
                >
                  <Button
                    icon="mdi mdi-pencil-outline"
                    text
                    rounded
                    size="small"
                    :aria-label="`Edit ${condition.label} cause`"
                    @click="openExistingCondition(condition, instance.id)"
                  />
                  <Button
                    icon="mdi mdi-close"
                    severity="danger"
                    text
                    rounded
                    size="small"
                    :aria-label="`Remove ${condition.label} cause`"
                    @click="$emit('remove', instance.id)"
                  />
                </span>
              </li>
            </ul>
          </div>
        </div>
      </li>
    </ul>
  </section>

  <Button
    v-else-if="canEdit && showTrigger"
    :label="iconOnly ? undefined : 'Conditions'"
    icon="mdi mdi-bandage"
    size="small"
    :text="iconOnly"
    :rounded="iconOnly"
    outlined
    :aria-label="iconOnly ? `Manage ${targetName} conditions` : undefined"
    :title="iconOnly ? `Manage ${targetName} conditions` : undefined"
    @click="openNewCondition"
  />

  <Dialog
    v-model:visible="dialogOpen"
    modal
    :header="dialogTitle"
    :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
  >
    <form
      :id="formId"
      class="d-grid gap-3"
      @submit.prevent="saveCondition"
    >
      <div>
        <label
          class="form-label fw-semibold"
          :for="`${formId}-identifier`"
        >
          Condition
        </label>
        <Select
          :id="`${formId}-identifier`"
          v-model="identifier"
          class="w-100"
          :options="conditionOptions"
          option-label="label"
          option-value="value"
          :disabled="conditionId !== null"
        />
      </div>

      <div v-if="identifier === 'exhaustion'">
        <label
          class="form-label fw-semibold"
          :for="`${formId}-level`"
        >
          Exhaustion level
        </label>
        <InputNumber
          :id="`${formId}-level`"
          v-model="exhaustionLevel"
          class="w-100"
          input-class="w-100"
          show-buttons
          button-layout="horizontal"
          increment-button-icon="mdi mdi-plus"
          decrement-button-icon="mdi mdi-minus"
          :min="1"
          :max="6"
        />
      </div>

      <div>
        <label
          class="form-label fw-semibold"
          :for="`${formId}-source`"
        >
          Source
        </label>
        <InputText
          :id="`${formId}-source`"
          v-model="source"
          class="w-100"
          maxlength="200"
          placeholder="For example: ghoul claws or hunger"
        />
      </div>

      <div>
        <label
          class="form-label fw-semibold"
          :for="`${formId}-duration`"
        >
          Duration or removal reminder
        </label>
        <InputText
          :id="`${formId}-duration`"
          v-model="duration"
          class="w-100"
          maxlength="200"
          placeholder="For example: until the next long rest"
        />
      </div>
    </form>

    <template #footer>
      <Button
        label="Cancel"
        severity="secondary"
        text
        @click="dialogOpen = false"
      />
      <Button
        :form="formId"
        type="submit"
        :label="conditionId === null ? 'Apply condition' : 'Save changes'"
        :disabled="identifier === 'exhaustion' && exhaustionLevel === null"
      />
    </template>
  </Dialog>
</template>

<script lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import { defineComponent, type PropType } from "vue";
import type { ActiveCondition, ConditionIdentifier, ConditionMutation } from "@/api";
import { conditionIcon, conditionOptions } from "@/campaigns/conditionDisplay";

export default defineComponent({
  components: {
    Button,
    Dialog,
    InputNumber,
    InputText,
    Select,
  },
  props: {
    conditions: {
      type: Array as PropType<ActiveCondition[]>,
      required: true,
    },
    targetName: { type: String, required: true },
    targetId: { type: [Number, String], required: true },
    canEdit: { type: Boolean, default: false },
    triggerOnly: { type: Boolean, default: false },
    iconOnly: { type: Boolean, default: false },
    showTrigger: { type: Boolean, default: true },
  },
  emits: ["apply", "remove"],
  data() {
    return {
      dialogOpen: false,
      conditionId: null as number | null,
      identifier: "prone" as ConditionIdentifier,
      source: "",
      duration: "",
      exhaustionLevel: null as number | null,
      conditionOptions,
    };
  },
  computed: {
    dialogTitle(): string {
      return this.conditionId === null
        ? `Apply a condition to ${this.targetName}`
        : `Edit ${this.targetName}'s condition`;
    },
    formId(): string {
      return `condition-${this.targetId}`;
    },
  },
  methods: {
    conditionIcon,
    causeDescription(source: string, duration: string): string {
      const details = [source, duration].filter(Boolean);

      return details.length ? details.join(" · ") : "No source or duration recorded";
    },
    openNewCondition(): void {
      this.conditionId = null;
      this.identifier = "prone";
      this.source = "";
      this.duration = "";
      this.exhaustionLevel = null;
      this.dialogOpen = true;
    },
    openExistingCondition(condition: ActiveCondition, conditionId: number): void {
      const instance = condition.instances.find(
        (candidate) => candidate.id === conditionId,
      );

      if (!instance) {
        return;
      }

      this.conditionId = conditionId;
      this.identifier = condition.id;
      this.source = instance.source;
      this.duration = instance.duration;
      this.exhaustionLevel = condition.exhaustion_level;
      this.dialogOpen = true;
    },
    saveCondition(): void {
      const condition: ConditionMutation = {
        identifier: this.identifier,
        source: this.source.trim(),
        duration: this.duration.trim(),
      };

      if (this.conditionId !== null) {
        condition.condition_id = this.conditionId;
      }

      if (this.identifier === "exhaustion" && this.exhaustionLevel !== null) {
        condition.exhaustion_level = this.exhaustionLevel;
      }

      this.$emit("apply", condition);
      this.dialogOpen = false;
    },
  },
});
</script>
