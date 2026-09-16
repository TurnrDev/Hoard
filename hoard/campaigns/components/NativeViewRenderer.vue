<template>
  <hr v-if="node.type === 'divider'" />
  <span
    v-else-if="node.type === 'spacer'"
    class="flex-grow-1"
    aria-hidden="true"
  />
  <span
    v-else-if="node.type === 'icon'"
    class="mdi mdi-puzzle-outline"
    aria-hidden="true"
  />
  <span v-else-if="node.type === 'text'">
    {{ displayValue(node.text) }}
  </span>
  <span v-else-if="node.type === 'stat'">
    {{ displayValue(node.current_value) }}
  </span>
  <span
    v-else-if="node.type === 'chip' || node.type === 'diffText'"
    class="badge text-bg-secondary"
  >
    {{ displayValue(node.text ?? node.label ?? node.value) }}
  </span>
  <div
    v-else-if="node.type === 'avatar'"
    class="d-flex align-items-center gap-2"
  >
    <span
      class="mdi mdi-account-circle fs-2"
      aria-hidden="true"
    />
    <span>{{ displayValue(node.name) || "Character portrait" }}</span>
  </div>
  <label
    v-else-if="node.type === 'checkbox' && node.stat"
    class="d-flex align-items-center gap-2"
  >
    <Checkbox
      :model-value="Boolean(node.current_value)"
      binary
      :disabled="!canEdit"
      @update:model-value="updateStat(node.stat, Boolean($event))"
    />
    {{ displayValue(node.label) || displayIdentifier(node.stat) }}
  </label>
  <label
    v-else-if="node.type === 'select' && node.stat"
    class="d-grid gap-1"
  >
    <span class="small fw-semibold">
      {{ displayValue(node.label) || displayIdentifier(node.stat) }}
    </span>
    <Select
      :model-value="node.current_value"
      :options="selectOptions"
      option-label="name"
      option-value="id"
      :disabled="!canEdit"
      @update:model-value="updateStat(node.stat, $event)"
    />
  </label>
  <label
    v-else-if="node.type === 'ticker' && node.stat"
    class="d-grid gap-1"
  >
    <span class="small fw-semibold">
      {{ displayValue(node.label) || displayIdentifier(node.stat) }}
    </span>
    <InputNumber
      :model-value="numericValue(node.current_value)"
      :disabled="!canEdit"
      :min="numericValue(node.minimum)"
      :max="numericValue(node.maximum)"
      :step="1"
      show-buttons
      button-layout="horizontal"
      increment-button-icon="mdi mdi-plus"
      decrement-button-icon="mdi mdi-minus"
      @update:model-value="updateStat(node.stat, $event ?? 0)"
    />
  </label>
  <div
    v-else-if="node.type === 'selectResources'"
    class="d-flex align-items-center gap-2"
  >
    <Button
      :label="`Add ${displayIdentifier(String(node.resource_id ?? 'resource'))}`"
      icon="mdi mdi-plus"
      outlined
      size="small"
      :disabled="!canEdit || !node.resource_id"
      @click="$emit('select-resource', String(node.resource_id))"
    />
  </div>
  <div
    v-else-if="isButton"
    class="d-flex align-items-center gap-2"
  >
    <Button
      :label="buttonLabel"
      outlined
      size="small"
      :disabled="!canEdit || !eventName"
      @click="activate"
    />
    <button
      type="button"
      class="btn btn-link btn-sm"
      :aria-label="`Show system behaviour for ${buttonLabel}`"
      @click="showBehaviour"
    >
      System behaviour
    </button>
  </div>
  <div
    v-else-if="
      ['resourceSection', 'resource', 'resourceArray'].includes(node.type ?? '')
    "
  >
    <div
      v-if="resourceItems.length"
      class="row g-2"
    >
      <div
        v-for="(resource, index) in resourceItems"
        :key="resourceIdentifier(resource, index)"
        class="col-12 col-md-6"
      >
        <article class="border rounded-3 p-3 h-100">
          <div class="d-flex align-items-start justify-content-between gap-2">
            <strong>{{ resourceName(resource) }}</strong>
            <Button
              v-if="canEdit && resource['$hoard_entry_id']"
              icon="mdi mdi-delete-outline"
              severity="danger"
              text
              rounded
              size="small"
              :aria-label="`Remove ${resourceName(resource)}`"
              @click="$emit('detach-resource', Number(resource['$hoard_entry_id']))"
            />
          </div>
          <p
            v-if="resourceDescription(resource)"
            class="small text-body-secondary mb-0 mt-2"
          >
            {{ resourceDescription(resource) }}
          </p>
        </article>
      </div>
    </div>
    <p
      v-else
      class="small text-body-secondary mb-0"
    >
      No {{ displayIdentifier(String(node.resource_id ?? "resources")) }} selected.
    </p>
  </div>
  <section
    v-else-if="isContainer"
    class="native-view-container d-grid gap-2"
  >
    <NativeViewRenderer
      v-for="(child, index) in childNodes"
      :key="String(child.id ?? `${node.id ?? node.type}-${index}`)"
      :node="child"
      :can-edit="canEdit"
      @activate="$emit('activate', $event)"
      @show-behaviour="$emit('show-behaviour', $event)"
      @select-resource="$emit('select-resource', $event)"
      @detach-resource="$emit('detach-resource', $event)"
    />
  </section>
  <Message
    v-else
    severity="warn"
    class="mb-0"
  >
    This system uses the unsupported
    {{ displayIdentifier(String(node.type ?? "view")) }}
    view. Its content has not been hidden.
  </Message>
</template>

<script lang="ts">
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import Select from "primevue/select";
import { defineComponent, type PropType } from "vue";
import type { NativeViewNode } from "@/api";
import { displayIdentifier } from "@/campaigns/display";

type NativeActivation = {
  eventName: string;
  viewValues?: Record<string, unknown>;
  statUpdates?: Record<string, unknown>;
};

export default defineComponent({
  name: "NativeViewRenderer",
  components: { Button, Checkbox, InputNumber, Message, Select },
  props: {
    node: { type: Object as PropType<NativeViewNode>, required: true },
    canEdit: { type: Boolean, default: false },
  },
  emits: {
    activate: (value: NativeActivation) => Boolean(value),
    "show-behaviour": (value: NativeViewNode) => Boolean(value),
    "select-resource": (value: string) => Boolean(value),
    "detach-resource": (value: number) => value > 0,
  },
  computed: {
    isButton(): boolean {
      return ["button", "menuButton", "popUpButton"].includes(this.node.type ?? "");
    },
    isContainer(): boolean {
      return [
        "section",
        "composite",
        "collapsible",
        "listItem",
        "list",
        "avatarSection",
        "viewPager",
      ].includes(this.node.type ?? "");
    },
    childNodes(): NativeViewNode[] {
      const keys = [
        "header",
        "content",
        "children",
        "components",
        "center_content",
        "bottom_content",
        "items",
        "list_items",
      ];

      return keys.flatMap((key) => {
        const value = this.node[key];

        return Array.isArray(value) ? (value as NativeViewNode[]) : [];
      });
    },
    eventName(): string {
      const behaviour = this.node.system_behaviour;
      const event = behaviour?.event;
      if (typeof event === "string") {
        return event;
      }
      if (typeof event === "object" && event !== null) {
        const name = (event as Record<string, unknown>).name;

        return String(this.resolvedValue(name) ?? "");
      }
      return "";
    },
    buttonLabel(): string {
      return String(
        this.displayValue(this.node.title) ||
          this.displayValue(this.node.label) ||
          displayIdentifier(String(this.node.id ?? "Action")),
      );
    },
    resourceItems(): Array<Record<string, unknown>> {
      if (Array.isArray(this.node.current_resources)) {
        return this.node.current_resources as Array<Record<string, unknown>>;
      }
      if (Array.isArray(this.node.current_value)) {
        return this.node.current_value as Array<Record<string, unknown>>;
      }
      if (typeof this.node.current_value === "object" && this.node.current_value) {
        return [this.node.current_value as Record<string, unknown>];
      }

      return [];
    },
    selectOptions(): Array<{ id: unknown; name: string }> {
      const options = this.node.resolved_options;
      if (!Array.isArray(options)) {
        return [];
      }

      return options.map((option) => {
        const row = option as Record<string, unknown>;

        return {
          id: row.id ?? row.value,
          name: String(row.name ?? row.label ?? row.id ?? row.value ?? "Option"),
        };
      });
    },
  },
  methods: {
    displayIdentifier,
    resolvedValue(value: unknown): unknown {
      if (typeof value === "object" && value !== null && "formula" in value) {
        return (value as Record<string, unknown>).value;
      }

      return value;
    },
    displayValue(value: unknown): string {
      const resolved = this.resolvedValue(value);

      return resolved === null || resolved === undefined ? "" : String(resolved);
    },
    numericValue(value: unknown): number | undefined {
      const resolved = Number(this.resolvedValue(value));

      return Number.isFinite(resolved) ? resolved : undefined;
    },
    activate(): void {
      if (!this.eventName) {
        return;
      }

      this.$emit("activate", {
        eventName: this.eventName,
        viewValues: { [String(this.node.id ?? "control")]: this.node.current_value },
      });
    },
    updateStat(stat: string, value: unknown): void {
      this.$emit("activate", {
        eventName: `hoard_control:${this.node.id ?? stat}`,
        statUpdates: { [stat]: value },
        viewValues: { [String(this.node.id ?? stat)]: value },
      });
    },
    showBehaviour(): void {
      this.$emit("show-behaviour", this.node);
    },
    resourceStats(resource: Record<string, unknown>): Record<string, unknown> {
      const stats = resource.stats;

      return typeof stats === "object" && stats !== null
        ? (stats as Record<string, unknown>)
        : {};
    },
    resourceStat(resource: Record<string, unknown>, key: string): unknown {
      const value = this.resourceStats(resource)[key];

      if (typeof value === "object" && value !== null && "value" in value) {
        return (value as Record<string, unknown>).value;
      }

      return value;
    },
    resourceName(resource: Record<string, unknown>): string {
      return String(
        this.resourceStat(resource, "name") ??
          displayIdentifier(String(resource.resource_id ?? "Resource")),
      );
    },
    resourceDescription(resource: Record<string, unknown>): string {
      return String(this.resourceStat(resource, "description") ?? "");
    },
    resourceIdentifier(resource: Record<string, unknown>, index: number): string {
      return String(
        this.resourceStat(resource, "id") ?? `${resource.resource_id}-${index}`,
      );
    },
  },
});
</script>
