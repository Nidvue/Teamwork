# DESIGN - UX, interaction, accessibility, visual assets

Owner: Designer. Developer-ready specs, not illustrations of finished code, plus
the record for every visual asset (raster and vector) the deliverable needs.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md)

## Principles

User first. Every choice - layout, typography, font, colour, image - is justified
by the user's task, not by taste. Simplicity, efficiency, usability and a great
experience, in that order. See `roles/designer.md` for the full policy.

| principle | what it means here | check |
|---|---|---|
| Simple | shortest correct path, one primary action, remove before adding | steps in the primary flow |
| Efficient | fewest actions, no dead ends, progressive disclosure | actions to complete the task |
| Usable | keyboard, focus, contrast, targets, semantics, zoom | contrast >= 4.5:1, target >= 24px, 200% zoom |
| Great experience | consistent states, honest errors, no dark patterns | every state specified |

## Typography and fonts

| field | value |
|---|---|
| type scale | e.g. 12 / 14 / 16 / 20 / 28 px |
| body size / line height | >= 16 px / 1.4-1.6 |
| measure | 45-75 characters |
| font stack | `<platform stack>`, fallbacks stated explicitly |
| shipped font? | name + licence + subset, or "none - platform stack" |
| text-as-image | never; all text is real text |

## Flows

| flow | entry | steps | success | errors | a11y |
|---|---|---|---|---|---|
| | | | | | |

## Components and states

| component | default / hover / focus / active / disabled / loading / empty / error | tokens |
|---|---|---|
| | | |

## Visual system

- Spacing / type / colour tokens: ...
- Layout and breakpoints: ...
- Motion: ...

## Copy

| context | string |
|---|---|
| | |

## Visual assets

You decide what the deliverable needs and you own it end to end - see
`roles/designer.md` for the policy, the model ranking and the improvement loop.
Vector first; raster only where the surface needs one.

### Capability

| field | value |
|---|---|
| probe | `<teamwork imaging probe>` output (provider, model, source) |
| model licence | |
| local fallback | |
| cloud prompt policy | no private data, no real people, metadata stripped |
| medium decision | vector first; say why for each raster |

### Assets

| id | asset | medium | purpose / surface | path | size | candidates | status |
|---|---|---|---|---|---|---|---|
| IMG-1 | | svg / raster / diagram | | | | 4 (raster) | planned |

### IMG-1 - <name>

- medium: `<svg | raster | diagram-as-code>` and why
- prompt (raster) or viewBox/tokens (vector): `<verbatim>`
- negative: `text, letters, words, watermark, logo, ...`
- seed base (raster): `<n>` (candidate i uses seed+i)
- acceptance criteria: composition and safe area, legibility at 16 px and 2x,
  no rendered text, correct anatomy, palette match, no watermark, resolution and
  sharpness, accessible title/desc for vector
- licence / terms:
- candidates reviewed:
- selected:
- evidence: `<command @rev -> observed result>`

### Review log

| candidate | verdict | reason | reviewer |
|---|---|---|---|
| IMG-1-0 | | | |

### Improvement log

| round | what changed | why (criterion) | review after |
|---|---|---|---|
| 1 | | | |

> Cap: three improvement rounds per asset. If it still fails, escalate to the CEO
> with the criteria it cannot meet and the two best attempts. Never lower a
> criterion to make an asset pass, and never delete a rejected attempt.
