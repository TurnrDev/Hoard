import { computed, ref } from "vue";

export type ConnectionSource = "browser" | "campaign" | "http" | "user";

const unavailableSources = ref<Set<ConnectionSource>>(new Set());

export const serverIsReconnecting = computed(() => unavailableSources.value.size > 0);

export function markConnectionAvailable(source: ConnectionSource): void {
  if (!unavailableSources.value.has(source)) {
    return;
  }

  const nextSources = new Set(unavailableSources.value);
  nextSources.delete(source);
  unavailableSources.value = nextSources;
}

export function markConnectionUnavailable(source: ConnectionSource): void {
  if (unavailableSources.value.has(source)) {
    return;
  }

  unavailableSources.value = new Set([...unavailableSources.value, source]);
}
