import type { ThemeDefinition } from "vuetify"

// Hoard — modern digital tabletop tool. Dark base, arcane teal primary +
// violet secondary. Semantic HP colors used by the HP ring and party rail.
export const hoardDark: ThemeDefinition = {
  dark: true,
  colors: {
    background: "#0e1116",
    surface: "#161b22",
    "surface-bright": "#1e2530",
    "surface-light": "#222b37",
    "surface-variant": "#2a3441",
    "on-surface-variant": "#c7d0dc",

    primary: "#2dd4bf", // arcane teal
    "primary-darken-1": "#14b8a6",
    secondary: "#a78bfa", // violet
    "secondary-darken-1": "#8b5cf6",
    accent: "#c4b5fd",

    // semantic HP scale
    "hp-healthy": "#34d399",
    "hp-wounded": "#fbbf24",
    "hp-danger": "#f87171",
    "hp-temp": "#38bdf8",
    "hp-down": "#64748b",

    info: "#38bdf8",
    success: "#34d399",
    warning: "#fbbf24",
    error: "#f87171",

    "on-background": "#e6edf3",
    "on-surface": "#e6edf3",
    "on-primary": "#04201c",
    "on-secondary": "#1e1145",
  },
  variables: {
    "border-color": "#2a3441",
    "border-opacity": 1,
    "theme-code": "#0b0e12",
  },
}
