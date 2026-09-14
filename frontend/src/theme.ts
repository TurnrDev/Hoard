import { definePreset, usePreset } from "@primeuix/themes";
import Lara from "@primeuix/themes/lara";

const hoardSurface = {
  0: "#d8d2c7",
  50: "#f8f3e8",
  100: "#eee6d5",
  200: "#dfd1b7",
  300: "#cab995",
  400: "#a99674",
  500: "#82745b",
  600: "#625945",
  700: "#453f31",
  800: "#2c2a22",
  900: "#1b1c17",
  950: "#11130f",
};

const hoardGold = {
  50: "#fff9e8",
  100: "#fdf0c8",
  200: "#f9df91",
  300: "#f2c85c",
  400: "#e7b13c",
  500: "#c58b20",
  600: "#9b6818",
  700: "#744c15",
  800: "#4e3214",
  900: "#2c1b0e",
  950: "#1b1008",
};

const hoardGreen = {
  50: "#edf7f1",
  100: "#d5ecdd",
  200: "#acd9bd",
  300: "#7cc09a",
  400: "#4ca476",
  500: "#2f855a",
  600: "#236b49",
  700: "#1d553c",
  800: "#194431",
  900: "#153829",
  950: "#0b2118",
};

const colourblindBlue = {
  50: "#eef7ff",
  100: "#d9edff",
  200: "#b9dcff",
  300: "#89c4ff",
  400: "#55a5f4",
  500: "#287fce",
  600: "#1d61a3",
  700: "#184a7e",
  800: "#173554",
  900: "#12253a",
  950: "#0b1726",
};

export const HoardLara = definePreset(Lara, {
  primitive: {
    gold: hoardGold,
    hoardGreen,
    hoardSurface,
  },
  semantic: {
    primary: {
      50: "{hoardGreen.50}",
      100: "{hoardGreen.100}",
      200: "{hoardGreen.200}",
      300: "{hoardGreen.300}",
      400: "{hoardGreen.400}",
      500: "{hoardGreen.500}",
      600: "{hoardGreen.600}",
      700: "{hoardGreen.700}",
      800: "{hoardGreen.800}",
      900: "{hoardGreen.900}",
      950: "{hoardGreen.950}",
    },
    colorScheme: {
      light: {
        surface: {
          0: "{hoardSurface.0}",
          50: "{hoardSurface.50}",
          100: "{hoardSurface.100}",
          200: "{hoardSurface.200}",
          300: "{hoardSurface.300}",
          400: "{hoardSurface.400}",
          500: "{hoardSurface.500}",
          600: "{hoardSurface.600}",
          700: "{hoardSurface.700}",
          800: "{hoardSurface.800}",
          900: "{hoardSurface.900}",
          950: "{hoardSurface.950}",
        },
      },
      dark: {
        surface: {
          0: "{hoardSurface.0}",
          50: "{hoardSurface.50}",
          100: "{hoardSurface.100}",
          200: "{hoardSurface.200}",
          300: "{hoardSurface.300}",
          400: "{hoardSurface.400}",
          500: "{hoardSurface.500}",
          600: "{hoardSurface.600}",
          700: "{hoardSurface.700}",
          800: "{hoardSurface.800}",
          900: "{hoardSurface.900}",
          950: "{hoardSurface.950}",
        },
      },
    },
  },
});

export const HoardLaraColourblind = definePreset(HoardLara, {
  primitive: {
    colourblindBlue,
  },
  semantic: {
    primary: {
      50: "{colourblindBlue.50}",
      100: "{colourblindBlue.100}",
      200: "{colourblindBlue.200}",
      300: "{colourblindBlue.300}",
      400: "{colourblindBlue.400}",
      500: "{colourblindBlue.500}",
      600: "{colourblindBlue.600}",
      700: "{colourblindBlue.700}",
      800: "{colourblindBlue.800}",
      900: "{colourblindBlue.900}",
      950: "{colourblindBlue.950}",
    },
    colorScheme: {
      dark: {
        surface: {
          0: "#c3beb4",
        },
      },
    },
  },
});

export type ThemePreferences = {
  colourMode: "system" | "light" | "dark";
  palette: "normal" | "colourblind";
};

const themeStorageKey = "hoard:theme-preferences";

const defaultThemePreferences: ThemePreferences = {
  colourMode: "system",
  palette: "normal",
};

export function readThemePreferences(): ThemePreferences {
  const stored = localStorage.getItem(themeStorageKey);

  if (!stored) {
    return defaultThemePreferences;
  }

  try {
    const preferences = JSON.parse(stored) as Partial<ThemePreferences>;

    return {
      colourMode:
        preferences.colourMode === "light" ||
        preferences.colourMode === "dark" ||
        preferences.colourMode === "system"
          ? preferences.colourMode
          : defaultThemePreferences.colourMode,
      palette:
        preferences.palette === "colourblind" || preferences.palette === "normal"
          ? preferences.palette
          : defaultThemePreferences.palette,
    };
  } catch {
    return defaultThemePreferences;
  }
}

export function applyThemePreferences(preferences: ThemePreferences): void {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark =
    preferences.colourMode === "dark" ||
    (preferences.colourMode === "system" && prefersDark);

  localStorage.setItem(themeStorageKey, JSON.stringify(preferences));
  document.documentElement.classList.toggle("hoard-dark", isDark);
  document.documentElement.style.colorScheme = isDark ? "dark" : "light";
  document.documentElement.dataset.bsTheme = isDark ? "dark" : "light";
  document.documentElement.dataset.hoardPalette = preferences.palette;

  usePreset(preferences.palette === "colourblind" ? HoardLaraColourblind : HoardLara);
}
