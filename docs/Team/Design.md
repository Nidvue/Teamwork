# DESIGN - README, visual assets and conversion

Owner: Designer. The developer-ready brief for `README.md` and `assets/**`:
audience, information hierarchy, tokens, accessibility and the conversion
checklist a Tester can assert on.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md) · [README](https://github.com/Nidvue/Teamwork/blob/main/README.md)

## 0. Principles and typography

The same rules that govern a product UI govern this repository's own surfaces
(README, docs site, SVGs). User first: every choice is justified by what the
reader is trying to do.

| principle | applied here | check |
|---|---|---|
| Simple | one pitch line, one install block, one comparison table; no badge wallpaper | time to first understood claim |
| Efficient | the reader reaches a working command in one screen | lines above the fold before the quickstart |
| Usable | headings in order, real alt text on every SVG, links that say where they go | `teamwork links` -> 0, one `<h1>` |
| Great experience | consistent voice, honest limits (stars are not promised), no marketing filler | no claim without evidence |

**Typography and fonts.** The repository ships **no font files**: every SVG uses
`ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif`
(banner, logo marks) or `ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation
Mono", monospace` (demo) - an explicit fallback chain ending in a generic family,
no `@font-face`, no external resource - so nothing is fetched at render time and
nothing is licensed to ship. Sizes follow a short scale (96 wordmark / 22 tagline /
16 org label / 15 chip and demo line / 14 caption in the banner and demo, scaled by
`viewBox`, not by pixels at one size). Text is **real text** everywhere -
the terminal demo sets characters, never an image of characters - so it stays
selectable and accessible. Body copy in Markdown is left to the platform stack and
the reader's own size settings, which is the most user-centred default available.

## 1. Audience and job to be done

| # | Audience | Arrives believing | Job to be done in the README | Success signal |
|---|---|---|---|---|
| A1 | Developers already using a coding agent | "multi-agent frameworks are demos, not teams" | Decide in 15 s whether this is a real, runnable system | Copies the install or quickstart command |
| A2 | Engineers evaluating CrewAI/AutoGen/MetaGPT/LangGraph/Aider | "I need a comparison, not a slogan" | See the one structural difference that matters | Reads the comparison row and the evidence gate |
| A3 | Tooling and security reviewers | "agent tools have no audit trail" | Confirm provenance, licensing and privacy posture | Opens the ledger and privacy claims |
| A4 | Users of any coding agent | "is this just a prompt?" | Recognise a skill they can clone into the host | Clones the skill to `.agents/skills/teamwork` and names it in a request |

Primary job: **convert a skeptical developer into a first command run.** Everything
above the fold serves A1; the proof sections serve A2-A4.

## 2. Information hierarchy

Order is deliberate: claim, proof, action, depth.

| # | README block | Purpose | Serves |
|---|---|---|---|
| 1 | Centered hero: banner SVG, H1, one-line pitch, badges | State what it is and that it is real in one screen | A1-A4 |
| 2 | Animated terminal demo | Show the skill install and the one-prompt start, not tell | A1, A4 |
| 3 | Why Teamwork (3 differentiators) | The three structural claims a competitor cannot copy cheaply | A2, A3 |
| 4 | Features table | Depth without scrolling walls of prose | A1-A4 |
| 5 | Install the skill (one clone) + optional engine + 30-second quickstart | Remove every excuse not to run it; make the skill, not an app, the thing you install | A1 |
| 6 | For agents: host detection, install, verify, startup routine, hard rules | Let the agent install and drive the skill without a human relaying instructions | A1, A4 |
| 7 | Common ways to use it: eight trimmed real transcripts (new project, feature, red CI, manual steering, pulse, resume, audit proof, model routing) | Show the recurring jobs, not only the first command | A1, A2 |
| 8 | How it works (mermaid flowchart) | Make the loop legible: lanes -> self-check -> review -> STOP | A1, A2 |
| 9 | Teamwork vs alternatives | Meet the evaluation frame honestly, with sources | A2 |
| 10 | Architecture at a glance | Prove it is engineered, not a prompt file | A2, A3 |
| 11 | Roadmap | Signal stewardship and direction | A1 |
| 12 | Contributing / security / license / no personal data | Answer the trust and contribution questions | A3 |
| 13 | Star history | Social proof, honestly framed as not guaranteed | A1 |

## 3. Visual system

The Teamwork marks are hand-authored SVG (text, no raster); the only
Teamwork-surface raster is `assets/social-preview.png`. `docs/assets/` holds the
Nidvue trademark set (SVG plus PNG/ICO rasters). Nothing enters Git LFS (R-9),
except that `.gitattributes` opts `docs/assets/*` out of LFS at the cost of also
opting the SVGs out of **text diffs** - see the finding in section 9.
No external fonts, no network, no `<script>`.

| Asset | Size / viewBox | Job |
|---|---|---|
| `assets/banner.svg` | 1280 x 360, declared = viewBox | Wordmark, pitch, role chips, mini org chart |
| `assets/logo.svg` | 128 x 128, declared = viewBox | Repository mark, not part of the installed bundle; CI prose/media fixture |
| `assets/demo.svg` | 960 x 560, declared = viewBox | Animated terminal transcript: skill clone (nested `.git` dropped) -> skill-named request -> loop gate |
| `assets/social-preview.png` | 1280 x 640, RGB, no alpha | GitHub social preview / OG image; the only raster on a Teamwork surface |
| `docs/assets/nidvue-icon.svg` | 256 x 256, declared = viewBox | Nidvue mark: README hero icon, MkDocs theme logo |
| `docs/assets/nidvue-favicon.svg` | 256 x 256, declared = viewBox | MkDocs favicon (the same mark, standalone) |
| `docs/assets/nidvue-favicon.ico` | 16 / 32 / 48 PNG frames | Windows/legacy favicon container of the same mark |
| `docs/assets/nidvue-apple-touch-icon.png` | 180 x 180, RGB, opaque | iOS home-screen icon, rendered from the mark SVG; trademark set only, no in-tree reference |

The full inventory - references, measured size, review result - is the asset
record in section 9.

### Tokens

| Token | Value | Use |
|---|---|---|
| background | `#0b1020` -> `#141a3a` -> `#0b1020` | Banner gradient |
| terminal surface | `#0d1117`, title bar `#161b22`, border `#30363d` | Demo window |
| accent (indigo -> cyan) | `#818cf8` -> `#22d3ee` | Mark, CEO node, chips |
| text primary | `#ffffff`, `#e6edf3`, `#e0e7ff` | Headlines, command text |
| text muted | `#c9d1d9`, `#8b949e`, `#c7d2fe` | Output, title bar, tagline |
| status | ok `#3fb950`, warn `#d29922`, ceo `#d2a8ff` | `[ok]`, `CONTINUE`, `[ceo]` |
| type | system sans stack; `ui-monospace` stack in the demo | No downloaded fonts |
| spacing | 8 px grid; 18 px window radius; 17 px chip radius | Consistent geometry |

## 4. Badges: chosen and why

| Badge | Message | Why it earns a slot | Link target | Alt text |
|---|---|---|---|---|
| CI | Build is green | The first credential a developer checks | Actions `ci.yml` | "CI status" |
| License | AGPL-3.0 | Copyleft is a deliberate decision (R-11); state it up front | `LICENSE` | "License: AGPL-3.0" |
| Python | 3.9-3.13 | Compatibility is a purchase decision | Architecture | "Python 3.9 to 3.13" |
| Skill install | One clone, nothing to build | Sets the install expectation correctly: this is a skill, not an app | Install guide | "Skill: one clone to install" |
| PRs welcome | Contributions open | Lowers the barrier for the first PR | `CONTRIBUTING.md` | "PRs welcome" |
| Stars | Social proof | Requested conversion signal; never promised (R-1) | Stargazers | "GitHub stars" |

Rejected: "platform" and "build" badges add noise without a decision; "Made with
Python" duplicates the Python badge.

## 5. Accessibility

| Check | Requirement | Result |
|---|---|---|
| Contrast, body text | >= 4.5:1 (WCAG 2.1 AA) | 13 text pairs over 21 background checks all pass; lowest pair 5.62:1 (`#8b949e` on the `#161b22` title bar), next 6.35:1 (CEO node label on the indigo end of the accent gradient) |
| Contrast, decorative mark | >= 3:1 | Passes at its worst: NIDVUE frame `#8584F0` on white 3.20:1, NIDVUE N `#5857E8` on the README dark ground 3.56:1, logo node 4.24:1 (non-text, so the 3:1 bar applies). The frame used to be drawn at `opacity="0.92"`, which composites to 2.88:1 on white - fixed this sweep |
| Text alternatives | Every `<img>` and every SVG has a text alternative | `alt` on each README image; `<title>` + `<desc>` + `aria-labelledby` in all five SVGs, and every `aria-labelledby` token resolves to an element (checked, not assumed) |
| Colour independence | Colour never the only carrier of meaning | `[ok]`, `[ceo]`, `CONTINUE` are word labels; status colour is redundant |
| Motion | Animation is decorative and can be stopped | CSS keyframes; `@media (prefers-reduced-motion: reduce)` removes all animation and reveals the full transcript |
| Static fallback | Content survives no-CSS/crawler rendering | The three typed lines start clipped (`clip-path` inline base state) and the `prefers-reduced-motion` block unclips them; a renderer that runs neither CSS nor animation still shows every other line, and the full transcript is in the `<desc>` and in the README `alt` text. Measured: `cairosvg` (which ignores the animation) renders all eight lines |
| No external resources | No fonts, network, or scripts | Verified by parse: no `@font-face`, `@import`, `<script>`, `xlink:href`, `<image>`, `base64`, no `href`/`src` on any element and no `url()` outside the same document; every `font-family` stack ends in a generic family. One URL string exists inside `demo.svg`, and it is transcript text - the clone command the reader is meant to copy - not a fetched resource |
| Intrinsic size | Declared size matches the viewBox so nothing reflows while loading | All five SVGs declare `width`/`height` equal to their `viewBox`; both NIDVUE SVGs were viewBox-only (`300 x 150` default box) until this sweep |

Contrast measurements (WCAG 2.1 relative-luminance formula, computed by
`Scratch/verify_assets.py` - see section 8.2; worst stop of each gradient):

| Pair | Ratio | Level |
|---|---|---|
| `#ffffff` on `#141a3a` (wordmark, worst stop) | 16.95:1 | AAA |
| `#c7d2fe` on `#141a3a` (tagline, worst stop) | 11.37:1 | AAA |
| `#e0e7ff` on the chip fill over `#141a3a` | 11.00:1 | AAA |
| `#0b1020` on `#818cf8` (CEO node, indigo end) | 6.35:1 | AA |
| `#e0e7ff` on `#111735` | 14.23:1 | AAA |
| `#a5f3fc` on `#0e1430` | 14.49:1 | AAA |
| `#e6edf3` on `#0d1117` | 16.02:1 | AAA |
| `#c9d1d9` on `#0d1117` | 12.26:1 | AAA |
| `#3fb950` on `#0d1117` | 7.45:1 | AAA |
| `#d2a8ff` on `#0d1117` | 9.72:1 | AAA |
| `#d29922` on `#0d1117` | 7.50:1 | AAA |
| `#8b949e` on `#161b22` | 5.62:1 | AA |

Non-text marks: `#0b1020` on `#6366f1` 4.24:1, `#8584F0` on white 3.20:1,
`#5857E8` on `#0b1020` 3.56:1 and on white 5.33:1 - all above the 3:1 bar.

## 6. Conversion checklist

Assertable by a Tester on the merged README.

- [ ] Pitch and project name visible before the first scroll (hero block).
- [ ] Animated demo is the first element after the hero and needs no JS/network.
- [ ] Six badges present, each with alt text and a working link target.
- [ ] Install section installs the skill first (project or user skills directory, or `AGENTS.md` where the host has no skill loader) and demotes pipx/uvx/pip/source to an optional engine.
- [ ] Quickstart is no more than four commands and names the workspace path.
- [ ] Comparison table has 5 alternatives x 6 decision columns, with sources.
- [ ] License (AGPL-3.0) and the "no personal data" statement are present.
- [ ] Exactly one top-level heading (HTML `<h1>` or markdown `# `); every fenced block balanced.
- [ ] Every internal link in the README resolves; no bare or malformed external URL in it.
- [ ] Every SVG parses as XML and carries `<title>` + `<desc>`.
- [ ] Every SVG declares `width`/`height` equal to its `viewBox`, and no SVG
      references an external font, URL or script.
- [ ] The `How it works` diagram shows the self-check record, the `--credit`
      step and the delta re-review, not only a full re-review loop.

## 7. Implementation notes

- The demo is one SVG with CSS keyframes: a stepped `clip-path` types each
  command, `fade` reveals output lines, `blink` drives the cursor. Delays are
  absolute so the transcript reads in order in ~7 s.
- The demo's first line is the skill install (one clone) and its second is the
  host request `use the teamwork skill: ...` - the product is a skill, so the demo must not open
  with an app-style `teamwork` subcommand. The engine transcript follows as
  evidence of what the skill does.
- The banner org chart shows the CEO delegating to Architect, Developer and
  Reviewer, with Tester and the Ledger below - the same shape as the mermaid
  flowchart in the README.
- The README flowchart carries the two review steps the prose promises
  (`README.md` "Review throughput"): the self-check writes a record at that
  revision, `REC -.-> RV` is the `--credit` citation ("verify once - cite with
  --credit"), and a failed review goes to `FX[Owner fixes]` and back to the
  self-check as a **delta** rather than to the whole lane set. Before this sweep
  the diagram sent every fail straight back to `LANES`, which contradicted the
  same README section.
- Repository URLs use the public namespace `Nidvue/Teamwork` after the move from
  the former personal handle; the same value is used by `pyproject.toml`,
  `mkdocs.yml`, `CITATION.cff` and `CONTRIBUTING.md`. GitHub redirects the old
  paths, but nothing in the tree relies on that redirect.

## 8. Verification

Two passes are on record: the README/assets deliverable at `e5efc5f`, and the
graphics sweep of this task. The sweep rows were run in the worktree immediately
before the commit that carries this file and re-run at that commit, so the tree
they measured is the tree that landed.

### 8.1 README and assets deliverable (`e5efc5f`)

| Check | Command | Result |
|---|---|---|
| SVG XML | `python3 -c "import xml.etree.ElementTree as ET; ET.parse(<f>)"` for each `assets/*.svg` | 3/3 parse, no error |
| Link health | `python3 scripts/teamwork.py links` | 0 new broken/malformed/bare links from README or Design; repo-wide exit 1 from pre-existing issues below |
| Focused link rows | filter `link_report()` to README + Design | `broken: none`, `external_bad: none`, `bare: none` |
| Fence balance | count lines beginning with three backticks | 14 markers, even, balanced |
| Top-level heading | markdown `^# ` plus HTML `<h1>` outside fences | exactly 1 (`<h1>Nidvue Teamwork</h1>`) |
| Anchor use | `grep -oE '\]\(#[a-z0-9-]+\)'` on README and Design | none used, so none can dangle |
| No external resources in SVG | `grep -nE '<script|@font-face|xlink:href|href="http' assets/*.svg` | no matches; only the required `xmlns` namespace |

### 8.2 Graphics sweep (T-0001, 2026-10-30)

Host: Windows, `venv\Scripts\python.exe` 3.15.2. The audit is split by what the
host can do:

- **structure, sizes, rasters, contrast** - stdlib only, `Scratch/verify_assets.py`
  (parses every SVG with `xml.etree.ElementTree`, decodes the PNG chunks and the
  ICO directory by hand, and computes contrast with the WCAG relative-luminance
  formula). No eyeballing.
- **render and look** - `Scratch/render_review.py` under WSL, where the repo's
  `.venv` has `cairosvg` and Pillow: every SVG rasterised at 1x, 2x and 16 px and
  opened; every raster decoded.
- **diagram** - `Scratch/check_mermaid.py`, because no mermaid renderer exists on
  this host and fetching one is not allowed.

All three scripts live in the agent's gitignored `Scratch/`; the repository holds
no audit code for this.

| Check | Command | Result |
|---|---|---|
| Structure and semantics, all 5 SVGs | `venv\Scripts\python.exe Scratch\verify_assets.py <worktree>` | 5/5 well-formed; 5/5 `role="img"` with `<title>`, `<desc>` and every `aria-labelledby` token resolving; 5/5 declared `width`/`height` = `viewBox`; every `font-family` stack ends in a generic family; 0 `<script>`, `@font-face`, `@import`, `xlink:href`, `<image>`, `base64`, external `href`/`src`/`url()`; geometry inside the viewBox; 13 `<text>` elements in the banner and 11 in the demo (129 and 516 characters of real text), no text drawn as a path |
| Raster container and size | same script | `social-preview.png` 1280x640 colourtype 2 (RGB), chunks `IHDR IDAT IDAT IEND`, no metadata chunk; `nidvue-apple-touch-icon.png` 180x180 colourtype 2; `nidvue-favicon.ico` header `0,1,3`, 16-byte entries, 3 PNG frames 16/32/48, 0 trailing bytes |
| ICO decodes in a real decoder | `.venv/bin/python Scratch/render_review.py` (WSL, Pillow 13.0.0) | `PIL.Image.open` -> `sizes [(16, 16), (32, 32), (48, 48)]`, every frame RGBA (before the repair: `OSError: Truncated File Read`) |
| Contrast | same stdlib script | 13 text pairs over 21 background checks, all >= 4.5:1, worst 5.62:1; marks all >= 3:1 after the frame fix (3.20:1 worst) |
| Render and look | `render_review.py` at 1x, 2x and 16 px, every file opened | IMG-2 tagline clear of the org chart; IMG-4 all eight transcript lines legible, no clipping, no tofu; IMG-1/3/5/6 clean; NIDVUE legible at 16 px on light and dark; touch icon now shows the mark on white, not on black |
| Diagram | `venv\Scripts\python.exe Scratch\check_mermaid.py README.md` | 1 block, 16 nodes, 17 edges, balanced shapes, every endpoint declared, `--credit` and delta-fix steps present, 0 problems |
| Links | `python scripts/teamwork.py --project <worktree> links` | 0 issues (75 markdown files, 388 internal links) |
| Asset contract tests | `venv\Scripts\python.exe -m pytest tests/unit/test_skill_contracts.py -q -k "mark or prose or readme or media"` | 8 passed |
| Docs site | not run this sweep | `mkdocs` is not installed in the Windows venv and installing it needs the network; the docs-site build is the Release lane's gate, and this sweep changed no `mkdocs.yml`. **UNVERIFIED here** |

Not measured here, and therefore not claimed: a browser render of the README
(GitHub's markdown/Mermaid pipeline), and the social preview's provenance - the
raster predates this host and has no committed generator (section 9).

Findings outside this lane's ownership, for the CEO/Architect (not introduced by
the README or the assets). All three were fixed and are now green in
`teamwork.py links` (0 issues):

- the broken `docs/Team/Architecture.md` -> `Testing.md` link was removed;
- the missing back-links in `Architecture.md` and `Research.md` were added;
- the guide back-link was added to `Architecture.md`.

## 9. Visual assets (raster and vector)

Imaging is part of this document: the Designer decides what the deliverable
needs and owns the asset end to end. The policy - medium choice, the
`imaging probe`, the model ranking, the review of every candidate, the
improvement loop and the privacy/licence red lines - lives in the Designer's
charter,
[`roles/designer.md`](https://github.com/Nidvue/Teamwork/blob/main/roles/designer.md).

### Capability

| field | value |
|---|---|
| probe | `python scripts/teamwork.py imaging probe` on this host (Windows, 2026-10-30) -> `provider: -`, `model: -`, `source: none detected`: **no image model is reachable from this lane**. The earlier pass recorded `provider=local`, `model=qwen-image-2.1` on the authoring host; that result is not reproducible here and is not relied on |
| provider ranking check | the configured LLM provider is `ollama-cloud`; its catalog is text/vision **input** only (checked 2026-10-17), so no cloud text-to-image model is available to the team |
| model used | none in this sweep. Every change is hand-authored SVG or a `cairosvg` render of it (fallback ladder rungs 4-5: hand-authored vector, diagram-as-code) |
| model licence | the shipped social preview was composed programmatically on the earlier host; no third-party image is redistributed and no real person is depicted |
| local fallback | `qimg` (text-to-image and instruction-driven image editing) exists on the authoring host only |
| cloud prompt policy | no private data, no real people, metadata stripped before commit |
| medium decision | vector first: the README banner, logo and terminal demo are hand-authored SVG; a raster exists only for the surfaces that must be raster - the GitHub social preview and the iOS touch icon - and the touch icon is rendered from the SVG rather than drawn |

### Assets

Inventory, measured 2026-10-30 in this worktree (`git grep -l -F <path>` = who
references it, `wc -c` = size). "Referenced by" counts the document that records
the asset, not only the surface that displays it.

| id | asset | medium | size | referenced by | review result |
|---|---|---|---|---|---|
| IMG-1 | `assets/social-preview.png` | raster | 1280x640, 71 004 B (69 KiB), RGB | `scripts/build_pi_package.py:30` (`PREVIEW`), `.gitattributes:82` (LFS opt-out), Design/Plan/Decisions/Archive, `roles/designer.md` | pass - template layout, real text, measured on white: name 18.55:1, description 8.29:1, accent rule 5.33:1; only IHDR/IDAT/IEND chunks; inside the 40 pt safe area. One deviation recorded below (pitch punctuation) |
| IMG-2 | `assets/banner.svg` | svg | 1280x360 declared, 5 029 B | `README.md:2` (hero), Design/Plan/Archive | pass - one defect fixed (tagline collided with the org chart at the widest font of the stack; 25 -> 22 px) |
| IMG-3 | `assets/logo.svg` | svg | 128x128 declared, 964 B | `tests/unit/test_skill_contracts.py:251` (`PROSE_AND_MEDIA_EXAMPLES`), Design/Plan/Archive | pass - the standalone Teamwork mark; **kept, not dead**: it is the fixture that proves `assets/**` is treated as prose/media, and the mark the banner draws at 132 px. It is not on a product surface by design (README shows the *Nidvue* mark) |
| IMG-4 | `assets/demo.svg` | svg | 960x560 declared, 4 778 B | `README.md:19`, Design/Plan/Project/Pi-Packaging/Archive, `tests/unit/test_{skill_contracts,privacy_scan}.py` | pass - one stale line fixed (`12 roles staffed` -> `5 roles staffed, 2 lanes running`, matching the `slim` roster tier) |
| IMG-5 | `docs/assets/nidvue-icon.svg` | svg | 256x256 declared, 608 B | `README.md:3`, `mkdocs.yml:30` (theme logo), `tests/unit/test_skill_contracts.py:1262-1276` | pass - `role=img`, `<title>` + `<desc>`, no external resource, geometry centred in the viewBox; intrinsic size declared and the frame drawn at full opacity this sweep |
| IMG-6 | `docs/assets/nidvue-favicon.svg` | svg | 256x256 declared, 602 B | `mkdocs.yml:31` (favicon), `tests/unit/test_skill_contracts.py:1263,1277` | pass - `<desc>` + `aria-labelledby` added earlier, intrinsic size declared and frame at full opacity this sweep; legible at 16 px on light and dark grounds |
| IMG-7 | `docs/assets/nidvue-favicon.ico` | raster (ICO) | 16 + 32 + 48 PNG frames, 1 892 B | Plan/Archive only (the trademark set, `NOTICE:14`); no page loads it | **repaired earlier this task** - the directory used 12-byte entries with offsets 12 short, so `PIL.Image.open` raised `OSError: Truncated File Read`; rebuilt with 16-byte entries over the same three frames. Re-verified this sweep: `sizes [(16, 16), (32, 32), (48, 48)]`, all RGBA |
| IMG-8 | `docs/assets/nidvue-apple-touch-icon.png` | raster | 180x180, 1 952 B, RGB | Plan/Archive only, `NOTICE:14` | **repaired this sweep** - it shipped RGBA (alpha 0..255), so iOS composited the transparent ground on black and the indigo N fell to 3.56:1; now rendered opaque from `nidvue-favicon.svg` on the mark's white ground |

#### IMG-1 - social preview

- medium: raster, because the GitHub social preview/OG surface must be a raster
  image; there is no vector channel for it
- design source: **GitHub's official `repository-open-graph-template.png`**, followed
  strictly - 1280x640, white ground, the whole composition inside the template's
  40 pt safe border, and the template's centred stack: icon, then the name in bold,
  then a short two-line description
- composition: the Nidvue mark (rounded, 150 px) above **Nidvue Teamwork** in
  DejaVu Sans Bold 72 px, then the pitch in DejaVu Sans 32 px - all text drawn with a
  real font, never generated by an image model
- acceptance criteria: 1280x640 exactly, nothing outside the 40 pt safe area, no
  model-rendered lettering, legible at thumbnail size, under 1 MiB as a plain
  (non-LFS) file
- licence / terms: the Nidvue mark is Nidvue's trademark (NOTICE); no third-party
  asset is redistributed and no real person is depicted
- candidates reviewed: the earlier generated illustration was **rejected** for this
  surface - it did not follow the template
- selected: the template-conformant card, rebuilt programmatically
- evidence: `PIL` composition @worktree -> 1280x640, 71 004 B (69 KiB; the 33 KiB
  figure recorded here earlier was measured before the round-3 supersampling),
  content bottom 510 of a 600 safe bottom; re-measured 2026-10-30 -> 1280x640,
  colortype 2 (RGB, no alpha), no EXIF or `tEXt` chunk; reviewed visually before
  commit and again in this sweep

### Review log

| candidate | verdict | reason | reviewer |
|---|---|---|---|
| IMG-1-0..3 (generated illustrations) | reject | did not follow GitHub's open-graph template; the brief requires the template layout | Designer-1 |
| IMG-1-4 (template card, first draft) | reject | stack sat high in the frame, leaving the lower third empty | Designer-1 |
| IMG-1-5 (template card, centred) | **select** | icon + name + two-line pitch, optically centred inside the safe area, crisp real text | Designer-1 |

### Improvement log

| round | what changed | why (criterion) | review after |
|---|---|---|---|
| 1 | replaced the generated illustration with the template card | "follow GitHub's template" | layout matches the template |
| 2 | optically centred the stack (down 60 px) | "nothing outside the safe area" + balance at thumbnail size | pass: content bottom 500, safe bottom 600 |
| 3 | rebuilt with 4x supersampling, the mark rasterised from the SVG at 600 px, and the palette taken from the brand (`#5857E8` / `#8584F0`); moved the accent rule clear of the text | "no aliasing" + "foreground and background colours correct and harmonious" | pass: re-measured 2026-10-30 -> name 18.55:1, description 8.29:1, accent rule 5.33:1 on white; edges smooth at 2x zoom |
| 4 | widened the accent rule from a 132 px stub to the full title width (730 px, 8 px thick) and snapped the drawing coordinates to integers | "the underline is too short" + no stray pixels at the caps | pass: rule spans the title exactly, inside the 40 pt safe area, edges clean at 2x zoom |
| 5 | NIDVUE mark: declared `width="256" height="256"` and dropped the frame's `opacity="0.92"` | "state the intrinsic size or aspect ratio" + the 3:1 non-text bar: at 0.92 the frame composites to 2.88:1 on white, at full opacity 3.20:1 | pass: rendered at 16 px, 1x and 2x on white and on `#0d1117`; frame reads as one mark with the N |
| 6 | touch icon re-rendered from `nidvue-favicon.svg` at 180x180 on white, opaque RGB | "a touch icon must be opaque": the RGBA copy was composited by iOS on black, taking the N to 3.56:1 and hiding the mark's ground | pass: `alpha` channel gone (colortype 2), mark unchanged, 1 952 B |
| 7 | README flowchart: added the recorded-run node, the `--credit` edge and the `FX[Owner fixes]` delta node; labelled the lane group "one per staffed role" | "the pitch and the protocol must say the same thing": the README's own "Review throughput" row promises `--credit` and a delta re-review, and the diagram showed a full re-review loop | pass: 16 nodes, 17 edges, balanced, every endpoint declared (`check_mermaid.py`) |

#### IMG-2..IMG-4 - vector

- medium: SVG, hand-authored - the surfaces are a banner, a mark and a mocked
  terminal, all of which need to scale, diff and stay accessible
- acceptance criteria: valid XML, a `viewBox`, no embedded raster or base64, no
  external font dependency, `<title>` + `<desc>` + `role="img"`, legible at 16 px
  and at 2x, geometry inside the viewBox, contrast >= 4.5:1 for text
- evidence (2026-10-30 sweep, re-run on the current revision):
  `ET.parse` on all five SVGs -> 5/5 well-formed; no `@font-face`, `@import`,
  `<script>`, `xlink:href`, `<image>`, `base64` or fetched URL in any of them; no
  `href`/`src` attribute and no external `url()`; every `font-family` ends in a
  generic family; every SVG declares `width`/`height` equal to its `viewBox`;
  geometry inside the viewBox; `cairosvg` render at 1x, 2x and 16 px -> every text
  line legible, no tofu, no clipping; contrast 13 text pairs over 21 background
  checks >= 4.5:1 and every mark >= 3:1 (section 5)

### Review log - the superseded generated round for IMG-1

Kept as the evidence that the review was real; the candidates below were
illustrations generated for the social preview and **none of them ships**. The
round was rejected for a layout reason (the surface has to follow GitHub's
template), which is recorded in the log above.

| candidate | verdict | reason | reviewer |
|---|---|---|---|
| IMG-1-0 | reject | human figures read as generic silhouettes; the ledger idea is weak | Designer-1 |
| IMG-1-1 | reject | hub is small and the panes are ambiguous | Designer-1 |
| IMG-1-2 | superseded | chosen inside that round, then rejected with the whole round: the surface must follow the open-graph template, not an illustration | Designer-1 |
| IMG-1-3 | reject | busier background, weaker subject separation | Designer-1 |

| round | what changed | why (criterion) | review after |
|---|---|---|---|
| 1 | flattened RGBA to RGB and re-encoded with metadata stripped (625 KiB -> 516 KiB) | "under 1 MiB as a plain file" and the "strip metadata" red line - measured on the generated illustration of that round, not on the shipped card | superseded with the round; the shipped card is 69 KiB with only IHDR/IDAT/IEND chunks |

### 2026-10-30 graphics sweep (T-0001)

Every asset was parsed and measured with the stdlib script, rendered with
`cairosvg` at 1x / 2x / 16 px and opened as an image, and the rasters decoded with
Pillow. The rows below are the findings that produced a change or a decision.

| asset | finding (measured) | change |
|---|---|---|
| IMG-2 banner | the tagline overran its column: at the widest member of the font stack (the DejaVu Sans fallback, 601 px) it ended at x = 849 while the org chart's first box starts at x = 832, so the copy collided with `Architect` on any renderer whose font is wider than Arial's | tagline 25 px -> 22 px: worst case 529 px, ends at x = 777, 55 px clear of the chart; copy unchanged |
| IMG-4 demo | `objective accepted: 12 roles staffed, 3 lanes running` matched no roster tier - `ROSTER_TIERS` (`src/teamwork/config.py`) is `slim` (5 roles), `standard` (8) and `full` (15), and `docs/guide/cli.md` states `slim` is the default | corrected to `5 roles staffed, 2 lanes running`; the rest of the transcript is untouched |
| IMG-6 favicon.svg | `role="img"` and a `<title>` but no `<desc>` and no `aria-labelledby`, unlike IMG-5 | added `<desc>` + `aria-labelledby="ft fd"` |
| IMG-7 favicon.ico | the directory used 12-byte entries, so the image offsets were 12 short and `wPlanes` / `wBitCount` read as garbage; `PIL.Image.open` raised `OSError: Truncated File Read` | container rebuilt (6 + 3 x 16 B) over the same three PNG frames; `PIL` now reports frames 16/32/48 |
| IMG-5, IMG-6 (both NIDVUE SVGs) | `viewBox` only, no `width`/`height`, so a bare `<img>` gives the mark a 300x150 default box before CSS runs; and the `#8584F0` frame carries `opacity="0.92"`, which composites to **2.88:1** on white - under the 3:1 bar this document asserts for a meaningful graphic | `width="256" height="256"` declared; `opacity` removed -> 3.20:1 on white, 5.91:1 on `#0d1117`; the two files stay identical apart from their `<desc>` |
| IMG-8 touch icon | shipped RGBA with `alpha` 0..255, so iOS composites the transparent ground on black: the indigo N drops to 3.56:1 and the mark loses its white ground | re-rendered from `nidvue-favicon.svg` at 180x180 on white, saved colourtype 2 (RGB), metadata-free, 1 952 B |
| IMG-1 social preview | pitch reads "One prompt in**,** a whole company of agents out." while the README, the banner and the `<h1>` subtitle read "One prompt in**.** A whole company of agents out." | no change - see the deviation note below; the card is otherwise identical in wording and mark |
| README mermaid flowchart | the flow showed lanes -> self-check -> review -> merge -> loop and sent every fail back to `LANES`, omitting the two steps the protocol is built on: a recorded result at the same revision is **credited** (`--credit`) rather than re-run, and a failed review is re-reviewed as a **delta** by the reviewer that raised the finding | block edited: `REC[(Recorded runs at that revision)]`, `REC -.->|verify once - cite with --credit| RV`, `RV -- fail + findings --> FX[Owner fixes]`, `FX --> SC`; lane group labelled "one per staffed role" |
| IMG-3 logo | measured, no defect: `role=img`, title + desc, no text, no external reference, geometry inside the 128 viewBox | none - the fixture usage is the reason it ships |

Deviation accepted - the social preview's comma: the OG card is the one asset with
no committed generator (`scripts/` builds no image), so a rebuild would change the
whole card for one character and could not be shown to have changed nothing else.
The words are identical; the README remains the canonical wording and the CEO can
ask for a rebuild if the verbatim string matters more than the risk.

Repair recipe for IMG-7 (the three frames are the existing payload bytes):

```sh
# the shipped file carries its PNG frames at byte 42, 291 and 1017
.venv/bin/python - <<'PY'
import struct, pathlib, io
from PIL import Image
p = pathlib.Path("docs/assets/nidvue-favicon.ico")
old = p.read_bytes()
frames = [old[42:291], old[291:1017], old[1017:]]
dims = [Image.open(io.BytesIO(f)).size for f in frames]
header = struct.pack("<HHH", 0, 1, len(frames))
offset = 6 + 16 * len(frames)
entries = b""
for f, (w, h) in zip(frames, dims):
    entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(f), offset)
    offset += len(f)
p.write_bytes(header + entries + b"".join(frames))
PY
```

Result: 1 892 B; `PIL.Image.open` -> `sizes [(16, 16), (32, 32), (48, 48)]`; all
three frames decode as RGBA.

Render recipe for IMG-8 (reproducible from the tracked SVG, no image model):

```sh
# WSL, the repo .venv has cairosvg + Pillow
.venv/bin/python - <<'PY'
import io, cairosvg
from PIL import Image
png = cairosvg.svg2png(url="docs/assets/nidvue-favicon.svg", output_width=180, output_height=180)
mark = Image.open(io.BytesIO(png)).convert("RGBA")
canvas = Image.new("RGB", (180, 180), (255, 255, 255))
canvas.paste(mark, (0, 0), mark)
canvas.save("docs/assets/nidvue-apple-touch-icon.png", format="PNG", optimize=True)
PY
```

Result: 1 952 B, 180x180, colourtype 2 (RGB), chunks `IHDR IDAT IEND`.

#### Findings for other lanes (not edited here - outside this task's file scope)

| # | file | finding | owner | suggested fix |
|---|---|---|---|---|
| F-1 | `.gitattributes:88-90` | `docs/assets/* -filter -diff -merge -text` marks the NIDVUE **SVGs** as binary too, so `git diff` prints "Binary files differ" for a hand-authored text asset; every change to IMG-5/IMG-6 in this sweep is invisible in the diff a Reviewer reads | Architect / Release Engineer | split the rule: `docs/assets/*.svg -filter -merge` (keep text/diff) and `docs/assets/*.png -filter -diff -merge -text`; `-filter` alone is enough to stay out of LFS |
| F-2 | `README.md:2,19` | the hero `<img>` tags declare no intrinsic height (`width="100%"` and `width="820"`), so the two largest assets shift the page while loading; `README.md:3` does it right (`width="88" height="88"`) | CEO (README prose) | add `height="360"` / `height="478"` (the 2x-safe intrinsic ratio) next to the widths |
| F-3 | `assets/social-preview.png` | the pitch on the OG card uses a comma where the README uses a full stop (deviation note above) | CEO | rebuild the card only with a committed generator, so the change can be replayed |

### Notes

- Generated lettering is the failure mode this surface is most exposed to; every
  candidate was checked explicitly for stray glyphs before selection.
- The raster is committed as a normal binary (opted out of Git LFS in
  `.gitattributes`) so a plain `git clone` has the real file, not a pointer.
- GitHub's social preview is uploaded in repository **Settings**; there is no API
  for it, so the file lives here and the CEO uploads it as a manual release step.

## 10. Sources

- [WCAG 2.1 - Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) - accessed 2026-10-17
- [MDN - prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) - accessed 2026-10-17
- [W3C - Images tutorial (text alternatives)](https://www.w3.org/WAI/tutorials/images/) - accessed 2026-10-17
- [GitHub Docs - Creating diagrams (mermaid)](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) - accessed 2026-10-17
- [Shields.io - badge service](https://shields.io/) - accessed 2026-10-17
- [Star History](https://star-history.com/) - accessed 2026-10-17
