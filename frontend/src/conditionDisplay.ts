export const conditionIcons: Record<string, string> = {
  blinded: "mdi-eye-off-outline",
  charmed: "mdi-heart-outline",
  deafened: "mdi-ear-hearing-off",
  exhaustion: "mdi-battery-low",
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

export function conditionIcon(identifier: string): string {
  return conditionIcons[identifier.toLowerCase()] ?? "mdi-alert-circle-outline";
}
