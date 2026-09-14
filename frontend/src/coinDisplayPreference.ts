export type CoinDisplayMode = "pouch" | "value";

const coinDisplayModeStorageKey = "hoard:coin-display-mode";
const defaultCoinDisplayMode: CoinDisplayMode = "pouch";

export function readCoinDisplayMode(): CoinDisplayMode {
  try {
    const storedMode = localStorage.getItem(coinDisplayModeStorageKey);

    if (storedMode === "pouch" || storedMode === "value") {
      return storedMode;
    }
  } catch {
    return defaultCoinDisplayMode;
  }

  return defaultCoinDisplayMode;
}

export function storeCoinDisplayMode(mode: CoinDisplayMode): void {
  try {
    localStorage.setItem(coinDisplayModeStorageKey, mode);
  } catch {
    // The selected mode still applies to the current page when storage is unavailable.
  }
}
