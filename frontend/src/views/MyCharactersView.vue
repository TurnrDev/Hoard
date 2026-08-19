<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  archiveCharacter,
  createCharacter,
  getMyCharacters,
  updateCharacter,
  type Character,
} from "../api";

const route = useRoute();
const campaignId = Number(route.params.id);
const characters = ref<Character[]>([]);
const error = ref("");
const name = ref("");
const race = ref("Human");
const characterClass = ref("Fighter");
const editing = ref<Character>();
const abilities = ref({
  strength: 10,
  dexterity: 10,
  constitution: 10,
  intelligence: 10,
  wisdom: 10,
  charisma: 10,
});

async function load(): Promise<void> {
  try {
    characters.value = await getMyCharacters(campaignId);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load characters.";
  }
}

function edit(character: Character): void {
  editing.value = character;
  name.value = character.name;
  race.value = character.race;
  characterClass.value = character.class;
  abilities.value = {
    strength: character.strength,
    dexterity: character.dexterity,
    constitution: character.constitution,
    intelligence: character.intelligence,
    wisdom: character.wisdom,
    charisma: character.charisma,
  };
}

async function save(): Promise<void> {
  if (!name.value.trim()) return;
  try {
    if (editing.value) {
      await updateCharacter(campaignId, editing.value.id, {
        name: name.value.trim(),
        race: race.value,
        class: characterClass.value,
        ...abilities.value,
      });
    } else {
      await createCharacter(campaignId, {
        name: name.value.trim(),
        race: race.value,
        character_class: characterClass.value,
        ...abilities.value,
      });
    }
    editing.value = undefined;
    name.value = "";
    abilities.value = {
      strength: 10,
      dexterity: 10,
      constitution: 10,
      intelligence: 10,
      wisdom: 10,
      charisma: 10,
    };
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to save character.";
  }
}

async function archive(character: Character): Promise<void> {
  try {
    await archiveCharacter(campaignId, character.id);
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to archive character.";
  }
}

onMounted(load);
</script>

<template>
  <v-container style="max-width: 850px">
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h4">My characters</h1>
      <v-btn :to="`/c/${campaignId}`" prepend-icon="mdi-arrow-left"
        >Campaign</v-btn
      >
    </div>
    <v-alert v-if="error" type="error" closable @click:close="error = ''">{{
      error
    }}</v-alert>
    <v-card class="mb-5">
      <v-card-title>{{
        editing ? "Edit character" : "Create character"
      }}</v-card-title>
      <v-card-text
        ><v-form @submit.prevent="save">
          <v-row
            ><v-col cols="12" md="4"
              ><v-text-field v-model="name" label="Name" hide-details /></v-col
            ><v-col cols="12" md="4"
              ><v-text-field v-model="race" label="Race" hide-details /></v-col
            ><v-col cols="12" md="4"
              ><v-text-field
                v-model="characterClass"
                label="Class"
                hide-details /></v-col
          ></v-row>
          <v-row class="mt-1"
            ><v-col
              v-for="(_, ability) in abilities"
              :key="ability"
              cols="6"
              md="2"
              ><v-text-field
                v-model.number="abilities[ability]"
                type="number"
                min="1"
                max="30"
                :label="ability[0].toUpperCase() + ability.slice(1)"
                hide-details /></v-col
          ></v-row>
          <div class="d-flex ga-2 mt-4">
            <v-btn type="submit">{{
              editing ? "Save" : "Create active character"
            }}</v-btn>
            <v-btn
              v-if="editing"
              variant="text"
              @click="
                editing = undefined;
                name = '';
              "
              >Cancel</v-btn
            >
          </div>
        </v-form></v-card-text
      >
    </v-card>
    <v-list
      ><v-list-item
        v-for="character in characters"
        :key="character.id"
        :title="character.name"
        :subtitle="
          character.is_archived
            ? 'Archived'
            : character.is_active
              ? 'Active'
              : 'Inactive'
        "
      >
        <template #append
          ><v-btn
            v-if="!character.is_archived"
            icon="mdi-pencil"
            variant="text"
            @click="edit(character)" /><v-btn
            v-if="!character.is_archived"
            icon="mdi-archive"
            variant="text"
            @click="archive(character)"
        /></template> </v-list-item
    ></v-list>
  </v-container>
</template>
