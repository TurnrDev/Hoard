<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Character } from "../api";

const props = defineProps<{ characters: Character[] }>();
const emit = defineEmits<{ selected: [characterId: number | undefined] }>();
const selectedId = ref<number>();

const options = computed(() =>
  props.characters.map((character) => ({
    title: character.name,
    value: character.id,
  })),
);

watch(
  () => props.characters,
  (characters) => {
    if (!characters.some((character) => character.id === selectedId.value))
      selectedId.value = characters[0]?.id;
    emit("selected", selectedId.value);
  },
  { immediate: true },
);
watch(selectedId, (characterId) => emit("selected", characterId));
</script>

<template>
  <v-select
    v-model="selectedId"
    :items="options"
    item-title="title"
    item-value="value"
    label="Character"
  />
</template>
