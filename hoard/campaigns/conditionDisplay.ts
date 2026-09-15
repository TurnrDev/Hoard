import type { ConditionIdentifier } from "@/api";

export const conditionIcons: Record<string, string> = {
  blinded: "mdi-eye-off-outline",
  charmed: "mdi-heart-outline",
  deafened: "mdi-ear-hearing-off",
  exhaustion: "mdi-sleep",
  frightened: "mdi-emoticon-frown-outline",
  grappled: "mdi-handcuffs",
  incapacitated: "mdi-account-cancel-outline",
  invisible: "mdi-ghost-outline",
  paralyzed: "mdi-motion-pause-outline",
  petrified: "mdi-account-lock-outline",
  poisoned: "mdi-bottle-tonic-skull-outline",
  prone: "mdi-human-handsdown",
  restrained: "mdi-link-variant",
  stunned: "mdi-head-flash-outline",
  unconscious: "mdi-sleep",
  pacify: "mdi-peace",
};

export const conditionOptions: Array<{
  label: string;
  value: ConditionIdentifier;
}> = [
  { label: "Blinded", value: "blinded" },
  { label: "Charmed", value: "charmed" },
  { label: "Deafened", value: "deafened" },
  { label: "Exhaustion", value: "exhaustion" },
  { label: "Frightened", value: "frightened" },
  { label: "Grappled", value: "grappled" },
  { label: "Incapacitated", value: "incapacitated" },
  { label: "Invisible", value: "invisible" },
  { label: "Paralyzed", value: "paralyzed" },
  { label: "Petrified", value: "petrified" },
  { label: "Poisoned", value: "poisoned" },
  { label: "Prone", value: "prone" },
  { label: "Restrained", value: "restrained" },
  { label: "Stunned", value: "stunned" },
  { label: "Unconscious", value: "unconscious" },
  { label: "Pacify", value: "pacify" },
];

export function conditionIcon(identifier: string): string {
  return conditionIcons[identifier.toLowerCase()] ?? "mdi-alert-circle-outline";
}
