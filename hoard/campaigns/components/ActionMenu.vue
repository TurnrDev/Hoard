<template>
  <span class="d-inline-flex">
    <Button
      :icon="icon"
      text
      rounded
      :aria-label="label"
      aria-haspopup="menu"
      :aria-controls="menuId"
      @click.stop="toggle"
    />
    <Menu
      :id="menuId"
      ref="menu"
      :model="items"
      popup
    />
  </span>
</template>

<script lang="ts">
import Button from "primevue/button";
import Menu from "primevue/menu";
import type { MenuItem } from "primevue/menuitem";
import { defineComponent, type PropType } from "vue";

let actionMenuSequence = 0;

export default defineComponent({
  components: { Button, Menu },
  props: {
    items: {
      type: Array as PropType<MenuItem[]>,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
    icon: {
      type: String,
      default: "mdi mdi-dots-vertical",
    },
  },
  data() {
    actionMenuSequence += 1;

    return {
      menuId: `action-menu-${actionMenuSequence}`,
    };
  },
  methods: {
    toggle(event: Event): void {
      const menu = this.$refs.menu as { toggle: (event: Event) => void };

      menu.toggle(event);
    },
  },
});
</script>
