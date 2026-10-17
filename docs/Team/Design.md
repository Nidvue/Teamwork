# DESIGN - README, visual assets and conversion

Owner: Designer. The developer-ready brief for `README.md` and `assets/**`:
audience, information hierarchy, tokens, accessibility and the conversion
checklist a Tester can assert on.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md) · [README](https://github.com/VisionPZ/Nidvue-Teamwork/blob/main/README.md)

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
`font-family="system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
sans-serif"` (an explicit fallback chain, no `@font-face`, no external resource),
so nothing is fetched at render time and nothing is licensed to ship. Sizes follow
a short scale (28 title / 20 lead / 14 body / 12 caption in the banner and demo,
scaled by `viewBox`, not by pixels at one size). Text is **real text** everywhere -
the terminal demo sets characters, never an image of characters - so it stays
selectable and accessible. Body copy in Markdown is left to the platform stack and
the reader's own size settings, which is the most user-centred default available.

## 1. Audience and job to be done

| # | Audience | Arrives believing | Job to be done in the README | Success signal |
|---|---|---|---|---|
| A1 | Developers already using a coding agent | "multi-agent frameworks are demos, not teams" | Decide in 15 s whether this is a real, runnable system | Copies the install or quickstart command |
| A2 | Engineers evaluating CrewAI/AutoGen/MetaGPT/LangGraph/Aider | "I need a comparison, not a slogan" | See the one structural difference that matters | Reads the comparison row and the evidence gate |
| A3 | Tooling and security reviewers | "agent tools have no audit trail" | Confirm provenance, licensing and privacy posture | Opens the ledger and privacy claims |
| A4 | Pi users | "is this just a prompt?" | Recognise a skill + package they can load | Loads `SKILL.md` as `~/.pi/agent/skills/teamwork` |

Primary job: **convert a skeptical developer into a first command run.** Everything
above the fold serves A1; the proof sections serve A2-A4.

## 2. Information hierarchy

Order is deliberate: claim, proof, action, depth.

| # | README block | Purpose | Serves |
|---|---|---|---|
| 1 | Centered hero: banner SVG, H1, one-line pitch, badges | State what it is and that it is real in one screen | A1-A4 |
| 2 | Animated terminal demo | Show the CEO starting a company, not tell | A1, A4 |
| 3 | Why Teamwork (3 differentiators) | The three structural claims a competitor cannot copy cheaply | A2, A3 |
| 4 | Features table | Depth without scrolling walls of prose | A1-A4 |
| 5 | Install (pipx / uvx / pip / source) + 30-second quickstart | Remove every excuse not to run it | A1 |
| 6 | How it works (mermaid flowchart) | Make the loop legible: lanes -> self-check -> review -> STOP | A1, A2 |
| 7 | Teamwork vs alternatives | Meet the evaluation frame honestly, with sources | A2 |
| 8 | Architecture at a glance | Prove it is engineered, not a prompt file | A2, A3 |
| 9 | Roadmap | Signal stewardship and direction | A1 |
| 10 | Contributing / security / license / no personal data | Answer the trust and contribution questions | A3 |
| 11 | Star history | Social proof, honestly framed as not guaranteed | A1 |

## 3. Visual system

All assets are hand-authored SVG (text, no raster), so nothing enters Git LFS
(R-9). No external fonts, no network, no `<script>`.

| Asset | Size / viewBox | Job |
|---|---|---|
| `assets/banner.svg` | 1280 x 360 | Wordmark, pitch, role chips, mini org chart |
| `assets/logo.svg` | 128 x 128 | Compact mark for docs/favicons |
| `assets/demo.svg` | 960 x 560 | Animated terminal transcript of `init` -> task -> loop |

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
| PyPI-ready | Packaging is prepared | Sets install expectations honestly | Install guide | "PyPI: ready" |
| PRs welcome | Contributions open | Lowers the barrier for the first PR | `CONTRIBUTING.md` | "PRs welcome" |
| Stars | Social proof | Requested conversion signal; never promised (R-1) | Stargazers | "GitHub stars" |

Rejected: "platform" and "build" badges add noise without a decision; "Made with
Python" duplicates the Python badge.

## 5. Accessibility

| Check | Requirement | Result |
|---|---|---|
| Contrast, body text | >= 4.5:1 (WCAG 2.1 AA) | All pairs pass; lowest textual pair 5.62:1, accent node 6.35:1 |
| Contrast, decorative mark | >= 3:1 | Passes |
| Text alternatives | Every `<img>` and every SVG has a text alternative | `alt` on each README image; `<title>` + `<desc>` in each SVG |
| Colour independence | Colour never the only carrier of meaning | `[ok]`, `[ceo]`, `CONTINUE` are word labels; status colour is redundant |
| Motion | Animation is decorative and can be stopped | CSS keyframes; `@media (prefers-reduced-motion: reduce)` removes all animation and reveals the full transcript |
| Static fallback | Content survives no-CSS/crawler rendering | Base state of every animated element is visible; `<desc>` holds the full transcript |
| No external resources | No fonts, network, or scripts | Verified by grep: no `@font-face`, no `<script>`, no `xlink:href`; the only `http` string is the required SVG namespace |

Contrast measurements (WCAG relative-luminance formula, computed with a local
snippet - see section 9):

| Pair | Ratio | Level |
|---|---|---|
| `#ffffff` on `#0b1020` | 18.93:1 | AAA |
| `#c7d2fe` on `#141a3a` | 11.37:1 | AAA |
| `#e0e7ff` on `#111735` | 14.23:1 | AAA |
| `#e6edf3` on `#0d1117` | 16.02:1 | AAA |
| `#c9d1d9` on `#0d1117` | 12.26:1 | AAA |
| `#3fb950` on `#0d1117` | 7.45:1 | AAA |
| `#8b949e` on `#161b22` | 5.62:1 | AA |
| `#0b1020` on `#818cf8` | 6.35:1 | AA |
| `#0b1020` on `#22d3ee` | 10.48:1 | AAA |

## 6. Conversion checklist

Assertable by a Tester on the merged README.

- [ ] Pitch and project name visible before the first scroll (hero block).
- [ ] Animated demo is the first element after the hero and needs no JS/network.
- [ ] Six badges present, each with alt text and a working link target.
- [ ] Install section covers pipx, uvx, pip and source, copy-pasteable.
- [ ] Quickstart is no more than four commands and names the workspace path.
- [ ] Comparison table has 5 alternatives x 6 decision columns, with sources.
- [ ] License (AGPL-3.0) and the "no personal data" statement are present.
- [ ] Exactly one top-level heading (HTML `<h1>` or markdown `# `); every fenced block balanced.
- [ ] Every internal link in the README resolves; no bare or malformed external URL in it.
- [ ] Every SVG parses as XML and carries `<title>` + `<desc>`.

## 7. Implementation notes

- The demo is one SVG with CSS keyframes: a stepped `clip-path` types the
  command, `fade` reveals output lines, `blink` drives the cursor. Delays are
  absolute so the transcript reads in order in ~6 s.
- The banner org chart shows the CEO delegating to Architect, Developer and
  Reviewer, with Tester and the Ledger below - the same shape as the mermaid
  flowchart in the README.
- Repository URLs use the public namespace `VisionPZ/Nidvue-Teamwork` (the same value
  already used by `pyproject.toml`, `mkdocs.yml` and `CONTRIBUTING.md`). If the
  owner handle is ever treated as private, substitute it before publishing.

## 8. Verification (this deliverable)

Revision of record: `e5efc5f` (working tree; `README.md`, `assets/**` and
`docs/Team/Design.md` are new in this task).

| Check | Command | Result |
|---|---|---|
| SVG XML | `python3 -c "import xml.etree.ElementTree as ET; ET.parse(<f>)"` for each `assets/*.svg` | 3/3 parse, no error |
| Link health | `python3 scripts/teamwork.py links` | 0 new broken/malformed/bare links from README or Design; repo-wide exit 1 from pre-existing issues below |
| Focused link rows | filter `link_report()` to README + Design | `broken: none`, `external_bad: none`, `bare: none` |
| Fence balance | count lines beginning with three backticks | 14 markers, even, balanced |
| Top-level heading | markdown `^# ` plus HTML `<h1>` outside fences | exactly 1 (`<h1>Nidvue Teamwork</h1>`) |
| Anchor use | `grep -oE '\]\(#[a-z0-9-]+\)'` on README and Design | none used, so none can dangle |
| No external resources in SVG | `grep -nE '<script|@font-face|xlink:href|href="http' assets/*.svg` | no matches; only the required `xmlns` namespace |

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
[`roles/designer.md`](https://github.com/VisionPZ/Nidvue-Teamwork/blob/main/roles/designer.md).

### Capability

| field | value |
|---|---|
| probe | `python3 scripts/teamwork.py imaging probe` -> `provider=local`, `model=qwen-image-2.1`, `source=ambient environment`, `ranked: qwen-image-2.1 > sdxl > sd3.5-large` |
| provider ranking check | the configured LLM provider is `ollama-cloud`; its catalog is text/vision **input** only (checked 2026-10-17), so no cloud text-to-image model is available to the team |
| model used | Qwen-Image 2.1 + Fix LoRA, run locally on an RTX 4090 (23.5 GiB) |
| model licence | used locally for this repository's own asset; no third-party image is redistributed and no real person is depicted |
| local fallback | `qimg` (text-to-image and instruction-driven image editing) |
| cloud prompt policy | no private data, no real people, metadata stripped before commit |
| medium decision | vector first: the README banner, logo and terminal demo are hand-authored SVG; a raster exists only for the one surface that requires one - the GitHub social preview |

### Assets

| id | asset | medium | purpose / surface | path | size | candidates | status |
|---|---|---|---|---|---|---|---|
| IMG-1 | social preview | raster | GitHub repo social preview (OG image) for link shares | `assets/social-preview.png` | 1280x640 | 4 | integrated |
| IMG-2 | README banner | svg | README hero strip | `assets/banner.svg` | 2:1, viewBox | - | integrated |
| IMG-3 | logo | svg | repo mark in README/docs | `assets/logo.svg` | square, viewBox | - | integrated |
| IMG-4 | terminal demo | svg | README "what it looks like" animation | `assets/demo.svg` | 2:1, viewBox | - | integrated |

#### IMG-1 - social preview

- medium: raster, because the GitHub social preview/OG surface must be a raster
  image; there is no vector channel for it
- prompt: `A dark navy technical blueprint illustration of an autonomous engineering
  team: a central luminous hub connected by glowing circuit traces to a ring of
  eight smaller specialised nodes, each marked with a simple abstract glyph; on the
  right a vertical stack of translucent document panes linked by a visible chain of
  glowing links; faint grid and constellation lines in the background, cyan and
  violet accents on deep navy, clean modern vector-like rendering, crisp, high
  detail, cinematic rim light, wide banner composition with generous negative space
  on the left, absolutely no text, no letters, no words, no logos`
- negative: `text, letters, words, watermark, signature, logo, blurry, low quality, deformed, extra limbs`
- seed base: `20261017` (candidate *i* uses seed+i)
- acceptance criteria: composition and safe area (subject clear of the crop edges,
  negative space on the left), no rendered text or lettering, no watermark or
  signature, palette match (deep navy + cyan/violet), 1280x640 exactly, sharp,
  under 1 MiB as a plain (non-LFS) file
- licence / terms: generated locally with Qwen-Image 2.1 + Fix LoRA; no third-party
  asset is redistributed, no real person is depicted
- candidates reviewed: 4 / 4
- selected: `social-2.png` -> `assets/social-preview.png`
- evidence: `qimg t2i "<prompt>" --quality fix --size 1280x640 -n 4 --seed 20261017
  --local-files-only -o social @worktree -> 4 candidates in 158.7s; reviewed 4/4;
  improved (1 round); integrated as assets/social-preview.png`

#### IMG-2..IMG-4 - vector

- medium: SVG, hand-authored - the surfaces are a banner, a mark and a mocked
  terminal, all of which need to scale, diff and stay accessible
- acceptance criteria: valid XML, a `viewBox`, no embedded raster or base64, no
  external font dependency, `<title>` present, legible at 16 px and at 2x,
  `role="img"`
- evidence: `python3 -c "import xml.etree.ElementTree as ET; [ET.parse(p) for p in
  ('assets/banner.svg','assets/logo.svg','assets/demo.svg')]" @worktree -> 3/3 valid;
  ui/readme layer test -> OK readme assets + 3 svg valid + social-preview.png present`

### Review log

| candidate | verdict | reason | reviewer |
|---|---|---|---|
| IMG-1-0 | reject | human figures read as generic silhouettes; the ledger idea is weak | Designer-1 |
| IMG-1-1 | reject | hub is small and the panes are ambiguous | Designer-1 |
| IMG-1-2 | **select** | clear hub-and-spoke org with a recognisable linked ledger; clean negative space; no text | Designer-1 |
| IMG-1-3 | reject | busier background, weaker subject separation | Designer-1 |

### Improvement log

| round | what changed | why (criterion) | review after |
|---|---|---|---|
| 1 | flattened RGBA to RGB and re-encoded with metadata stripped (625 KiB -> 516 KiB) | "under 1 MiB as a plain file" and the "strip metadata" red line | pass: 516 KiB, no EXIF/PNG text chunks, still sharp at 1280x640 |

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
