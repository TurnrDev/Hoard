const coinLabels: Record<string, string> = {
  cp: "CP",
  sp: "SP",
  ep: "EP",
  gp: "GP",
  pp: "PP",
};

const abbreviations: Record<string, string> = {
  ac: "AC",
  hp: "HP",
  xp: "XP",
  npc: "NPC",
  gm: "GM",
  id: "ID",
  pp: "PP",
  gp: "GP",
  ep: "EP",
  sp: "SP",
  cp: "CP",
};

export function displayIdentifier(value: string): string {
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replaceAll(".", " ")
    .split(/\s+/)
    .filter(Boolean)
    .map(
      (word) =>
        abbreviations[word.toLowerCase()] ?? `${word[0].toUpperCase()}${word.slice(1)}`,
    )
    .join(" ");
}

export function displayCoin(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  return coinLabels[value.toLowerCase()] ?? displayIdentifier(value);
}

export function formatCoinPouch(amounts: Record<string, number | string>): string {
  return ["pp", "gp", "ep", "sp", "cp"]
    .map((denomination) => {
      const amount = Number(amounts[denomination] ?? 0);
      return `${Number.isFinite(amount) ? amount.toLocaleString() : amounts[denomination]} ${displayCoin(denomination)}`;
    })
    .join(" · ");
}
