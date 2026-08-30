# Hoard contributor guidance

- After modifying first-party Python code, run Ruff against `hoard` only.
- After modifying frontend code, run `npm run fix` from `frontend`, then verify with frontend build when appropriate.
- Never format, lint-fix, bulk-rewrite, or otherwise modify `vendor/`.
- Do not use leading-underscore “private” methods or functions in Python; Python
  has no private methods and the convention makes the code harder to read.

## API architecture

- All new application APIs must use WebSocket. Do not add new HTTP/REST endpoints
  for application data or mutations.
- Design each page around an initial query that returns all data needed to render
  that page. Avoid follow-up request waterfalls where practical.
- Make state changes through commands. A command is acknowledged when accepted;
  its eventual success or failure is reported asynchronously, including a useful
  error when it fails.
- Publish events for accepted changes so every connected client can update its
  local view from the same source of truth. Treat events, rather than the command
  acknowledgement, as the mechanism for distributing resulting state changes.

## Frontend code style

Prioritize readability, clarity, and maintainability over terseness or minimizing line count.

Write code in an explicit, vertically structured style. Code should be easy to scan and understand without mentally unpacking compressed statements or control flow.

The goal is **not verbosity for its own sake**. Concise language features are encouraged when they make an individual expression clearer. Do not use concision to collapse logical structure or multiple steps together.

### Documentation

Document functions, classes, objects and attributes when the meaning cannot be clearly discerned from the name or code.

### Control flow

Always use braces for control-flow blocks, even when the body is a single statement.

Prefer:

```ts
if (typeof msg === "string") {
    return msg;
}
```

Do not write:

```ts
if (typeof msg === "string") return msg;
```

Apply this consistently to `if`, `else`, loops, and similar constructs.

Prefer control flow to be visually obvious from the shape of the code.

### Whitespace and structure

Use blank lines to separate logically distinct parts of a function, component, or block.

Prefer:

```ts
const message = getMessage(response);

if (!message) {
    return null;
}

const formattedMessage = formatMessage(message);

return formattedMessage;
```

rather than grouping logically distinct operations together without whitespace.

Do not optimize code for the fewest lines possible. Vertical whitespace is desirable when it makes logical structure easier to see.

At the same time, do not mechanically insert blank lines between every statement. Group closely related statements together and use whitespace to communicate logical boundaries.

### Concise expressions are fine

Do not interpret these rules as a ban on concise JavaScript or TypeScript syntax.

Idiomatic expressions such as ternaries, optional chaining, nullish coalescing, destructuring, template literals, and concise array operations are fine when the resulting expression remains immediately readable.

For example, this is good:

```ts
const label = isActive ? "Active" : "Inactive";

const value = data?.foo?.bar ?? defaultValue;

const displayName = user.nickname ?? user.name;
```

There is no need to expand these into `if` statements merely to make the code longer.

A useful distinction is:

**Use concise syntax to simplify expressions, but do not use it to compress statements or control flow.**

### Avoid dense statements

Avoid putting multiple logical operations or statements onto one line.

Do not write:

```ts
if (!user) return;
if (loading) return null;
for (const item of items) process(item);
```

Prefer:

```ts
if (!user) {
    return;
}

if (loading) {
    return null;
}

for (const item of items) {
    process(item);
}
```

Likewise, avoid semicolon-separated statements or other techniques whose primary purpose is reducing vertical space.

### Expressions

Avoid unnecessarily dense or clever expressions.

A concise expression is good when its meaning is obvious:

```ts
const canEdit = isOwner && !isLocked;
```

There is no reason to artificially expand simple expressions like this.

Use intermediate variables when they:

- give an important concept a useful name;
- break apart a difficult expression;
- avoid repetition;
- make subsequent control flow easier to understand.

For example:

```ts
const isOwner = user.id === item.ownerId;
const isLocked = item.status === "locked";
const canEdit = isOwner && !isLocked;

if (canEdit) {
    enableEditing();
}
```

This is preferable when those intermediate concepts are meaningful to the surrounding code.

Do not introduce intermediate variables solely to make simple expressions longer.

### Functions

Functions should read top-to-bottom as a sequence of clear steps.

Where applicable, visually separate:

- initial setup;
- validation and guard clauses;
- data retrieval;
- data transformation;
- state changes or other side effects;
- final return logic.

Prefer early returns when they reduce nesting.

Write early returns as normal control-flow blocks:

```ts
if (!response.ok) {
    return null;
}

const data = await response.json();

return transformData(data);
```

rather than:

```ts
if (!response.ok) return null;
const data = await response.json();
return transformData(data);
```

### Components

Apply the same principles to frontend components.

Keep setup, derived state, handlers, effects, and rendering logic visually distinguishable where the framework and component size make this appropriate.

Do not compress component logic merely because JavaScript or TypeScript permits it.

Extract complex expressions or handlers when doing so gives the concept a useful name or makes the component easier to scan. Do not extract trivial expressions simply to increase abstraction.

### General principle

Write frontend code for a developer who values the explicitness, whitespace, and readability commonly associated with well-structured Python.

Prefer:

- obvious over clever;
- readable over terse;
- explicit control flow over compressed control flow;
- vertically structured code over horizontally compressed statements;
- meaningful whitespace between logical sections;
- descriptive names when they clarify concepts;
- idiomatic JavaScript/TypeScript expressions when they remain easy to read.

Do not optimize for minimum line count.

Do not expand already-clear expressions merely for the sake of verbosity.

**Concise expressions are good. Compressed structure is not.**


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
