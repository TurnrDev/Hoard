export const coinValuesInCopper: Record<string, number> = {
  cp: 1,
  sp: 10,
  ep: 50,
  gp: 100,
  pp: 1000,
};

export function exchangedCoinAmount(
  source: string,
  target: string,
  amount: number,
): number | null {
  const sourceValue = coinValuesInCopper[source];
  const targetValue = coinValuesInCopper[target];
  if (
    !sourceValue ||
    !targetValue ||
    source === target ||
    !Number.isInteger(amount) ||
    amount <= 0
  )
    return null;
  const copper = sourceValue * amount;
  const result = copper / targetValue;
  return Number.isInteger(result) ? result : null;
}
