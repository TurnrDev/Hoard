export function formatGoldValue(value: number | string): string {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? numeric.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : String(value);
}
