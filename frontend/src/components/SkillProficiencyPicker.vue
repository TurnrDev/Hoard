<template>
  <div class="d-grid gap-2">
    <span
      :id="`${inputId}-label`"
      class="fw-semibold"
    >
      {{ label }}
    </span>
    <SelectButton
      :model-value="modelValue || 'none'"
      :options="proficiencyChoices"
      option-label="title"
      option-value="value"
      :allow-empty="false"
      :aria-labelledby="`${inputId}-label`"
      :loading="loading"
      :disabled="disabled"
      size="small"
      fluid
      @update:model-value="updateValue"
    >
      <template #option="{ option }">
        <span :title="option.title">
          <span
            :class="['mdi', option.icon, 'fs-5']"
            aria-hidden="true"
          />
          <span class="visually-hidden">{{ option.title }}</span>
        </span>
      </template>
    </SelectButton>
  </div>
</template>

<script lang="ts">
import SelectButton from "primevue/selectbutton";
import { defineComponent } from "vue";

export default defineComponent({
  components: {
    SelectButton,
  },
  props: {
    modelValue: { type: String, default: "none" },
    inputId: { type: String, required: true },
    label: { type: String, required: true },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      proficiencyChoices: [
        { title: "None", value: "none", icon: "mdi-circle-outline" },
        {
          title: "Half proficiency",
          value: "half",
          icon: "mdi-circle-half-full",
        },
        { title: "Proficient", value: "proficient", icon: "mdi-circle" },
        { title: "Expertise", value: "expertise", icon: "mdi-star-circle" },
      ],
    };
  },
  methods: {
    updateValue(value: string | null): void {
      this.$emit("update:modelValue", value ?? "none");
    },
  },
});
</script>
