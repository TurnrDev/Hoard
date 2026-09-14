export function formatMoneyValue(value: number | string): string {
  const numeric = Number(value);

  return Number.isFinite(numeric)
    ? numeric.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : String(value);
}

export function formatCompactMoneyValue(value: number | string): string {
  const numeric = Number(value);

  return Number.isFinite(numeric)
    ? numeric.toLocaleString(undefined, {
        notation: "compact",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : String(value);
}

export const formatGoldValue = formatMoneyValue;
