<template>
  <Avatar
    class="character-avatar"
    :class="`character-avatar--${size}`"
    :label="character.portrait_url ? undefined : initials(character.name)"
    :image="character.portrait_url || undefined"
    shape="circle"
    :aria-label="`${character.name} profile picture`"
  />
</template>

<script lang="ts">
import Avatar from "primevue/avatar";
import { defineComponent, type PropType } from "vue";
import type { Character } from "../api";

export default defineComponent({
  components: { Avatar },
  props: {
    character: { type: Object as PropType<Character>, required: true },
    size: {
      type: String as PropType<"menu" | "rail" | "preview" | "profile">,
      default: "preview",
    },
  },
  methods: {
    initials(name: string): string {
      return name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
        .toUpperCase();
    },
  },
});
</script>

<style scoped>
.character-avatar {
  flex: 0 0 auto;
  overflow: hidden;
}

.character-avatar--menu,
.character-avatar--rail {
  width: 2.75rem;
  height: 2.75rem;
}

.character-avatar--preview {
  width: 5.5rem;
  height: 5.5rem;
  font-size: 1.5rem;
}

.character-avatar--profile {
  width: 7.5rem;
  height: 7.5rem;
  font-size: 2rem;
}

@media (max-width: 575.98px) {
  .character-avatar--preview {
    width: 4.5rem;
    height: 4.5rem;
  }

  .character-avatar--profile {
    width: 6rem;
    height: 6rem;
  }
}
</style>
