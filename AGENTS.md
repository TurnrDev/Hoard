# Hoard contributor guidance

- After modifying first-party Python code, run Ruff against `hoard` only.
- After modifying frontend code, run `npm run fix` from `frontend`, then verify with
  `npm run check` and the frontend build when appropriate.
- Never format, lint-fix, bulk-rewrite, or otherwise modify `vendor/`.
