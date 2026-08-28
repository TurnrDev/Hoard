# Hoard contributor guidance

- After modifying first-party Python code, run Ruff against `hoard` only.
- After modifying frontend code, run `npm run fix` from `frontend`, then verify with
  `npm run check` and the frontend build when appropriate.
- Never format, lint-fix, bulk-rewrite, or otherwise modify `vendor/`.
- Do not use leading-underscore “private” methods or functions in Python; Python
  has no private methods and the convention makes the code harder to read.

## Frontend accessibility baseline

- Target WCAG 2.2 AA. Do not use colour as the only indication of state, meaning, or
  destructive actions; pair it with clear text, an icon, pattern, or another cue.
- Use native semantic HTML whenever possible. Data tables need a caption, `th` cells
  with the appropriate `scope`, and row headers where rows have a natural label.
- Dense data tables must use subtle zebra striping for row tracking, but stripes are
  decorative: they must not convey information. Numeric columns should be right
  aligned and use tabular numerals.
- Icon-only controls require a contextual accessible name. Keyboard focus must remain
  obvious with a high-contrast visible indicator.
- Preserve readable type and layouts when users increase text size or apply WCAG text
  spacing overrides; avoid tight tracking and text conveyed only through colour.
- Use Vuetify's `v-number-input` for numeric entry. Choose `split` controls when a
  field has room for side controls, and `stacked` controls for compact grids or table
  cells; set meaningful `min`, `max`, `step`, and precision constraints.
- Never expose API keys, enum values, or abbreviations verbatim in the UI. Format
  them through shared display helpers (for example, `gp` as `GP` and `initiative` as
  `Initiative`).
- When frontend UI changes affect accessibility, run the normal frontend checks and
  build, then manually verify keyboard focus, 200% zoom/reflow, contrast, a
  red/green colour-vision simulation, and affected tables with a screen reader.
