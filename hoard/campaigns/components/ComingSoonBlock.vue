<template>
  <div class="coming-soon-block">
    <BlockUI
      :blocked="true"
      class="coming-soon-block__content"
    >
      <slot />
    </BlockUI>
    <Tag
      class="coming-soon-block__tag"
      value="Coming soon"
      severity="secondary"
    />
  </div>
</template>

<script lang="ts">
import BlockUI from "primevue/blockui";
import Tag from "primevue/tag";
import { defineComponent } from "vue";

export default defineComponent({
  name: "ComingSoonBlock",
  components: { BlockUI, Tag },
});
</script>

<style scoped>
.coming-soon-block {
  position: relative;
  height: 100%;
}

.coming-soon-block__content {
  display: block;
  height: 100%;
}

.coming-soon-block__tag {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 2;
  translate: -50% -50%;
  box-shadow: var(--bs-box-shadow-sm);
  pointer-events: none;
}

.coming-soon-block :deep(.p-blockui-mask) {
  background: color-mix(in srgb, var(--bs-body-bg) 42%, transparent) !important;
  opacity: 1 !important;
}
</style>
