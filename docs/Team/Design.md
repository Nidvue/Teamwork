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
| A4 | Users of any coding agent | "is this just a prompt?" | Recognise a skill they can clone into the host | Clones the skill to `.agents/skills/tw` and names it in a request |

Primary job: **convert a skeptical developer into a first command run.** Everything
above the fold serves A1; the proof sections serve A2-A4.

## 2. Information hierarchy

Order is deliberate: claim, proof, action, depth. The README is the front door,
not the manual: it carries the claim, the one install command and the map, and
each depth block links to its own guide page. The target size is 10 KiB (10,240
bytes) - a reader
who wants the manual follows the documentation map rather than scrolling.

| # | README block | Purpose | Serves |
|---|---|---|---|
| 1 | Centered hero: banner SVG, H1, one-line pitch, badges | State what it is and that it is real in one screen | A1-A4 |
| 2 | Animated terminal demo | Show the skill install and the one-prompt start, not tell | A1, A4 |
| 3 | What makes it different (7 rows: what, why, proof link) | The structural claims a competitor cannot copy cheaply, each with the page that proves it; no unsourced competitor fact | A2, A3 |
| 4 | Install the skill (one clone, one path) | Make the skill, not an app, the thing you install; link to the four-channel comparison | A1, A4 |
| 5 | 30-second quickstart | One runnable block from empty directory to first request | A1 |
| 6 | What you get (five bullets) | The five capabilities that decide adoption, without the full table | A1-A4 |
| 7 | Documentation map | Route each reader to the page that answers their next question | A1-A4 |
| 8 | Contributing / security / license / no personal data | Answer the trust and contribution questions; the star chart closes the page | A3 |

## 3. Visual system

The Teamwork marks are hand-authored SVG (text, no raster); the only
Teamwork-surface raster is `assets/social-preview.png`. `docs/assets/` holds the
Nidvue trademark set (SVG plus PNG/ICO rasters). Nothing enters Git LFS (R-9),
except that `.gitattributes` opts `docs/assets/*` out of LFS at the cost of also
opting the SVGs out of **text diffs** - see the finding in section 9.
No external fonts, no network, no `<script>`.

| Asset | Geometry | Source of the figure | Job |
|---|---|---|---|
| `assets/banner.svg` | 1280 x 360 | declared = viewBox | Wordmark, pitch, role chips, mini org chart |
| `assets/logo.svg` | 128 x 128 | declared = viewBox | Repository mark, not part of the installed bundle; CI prose/media fixture |
| `assets/demo.svg` | 960 x 560 | declared = viewBox | Animated terminal transcript: skill clone (nested `.git` dropped) -> skill-named request -> loop gate |
| `assets/social-preview.png` | 1280 x 640 | IHDR, RGB, no alpha | GitHub social preview / OG image; the only raster on a Teamwork surface |
| `docs/assets/nidvue-icon.svg` | 256 x 256 | declared = viewBox | Nidvue mark: README hero icon, MkDocs theme logo |
| `docs/assets/nidvue-favicon.svg` | 256 x 256 | declared = viewBox | MkDocs favicon (the same mark, standalone) |
| `docs/assets/nidvue-favicon.ico` | 16 / 32 / 48 | PNG frames in an ICO | Windows/legacy favicon container of the same mark |
| `docs/assets/nidvue-apple-touch-icon.png` | 180 x 180 | IHDR, RGB, opaque | iOS home-screen icon, rendered from the mark SVG; trademark set only, no in-tree reference |

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

| Badge | Message | Why it earns a slot | Link target | Alt text | Declared box (8.5) |
|---|---|---|---|---|---|
| CI | Build is green | The first credential a developer checks | Actions `ci.yml` | "CI status" | `height="20"` |
| License | AGPL-3.0-or-later | Copyleft is a deliberate decision (R-11); state it up front | `LICENSE` | "License: AGPL-3.0-or-later" | `width="160" height="20"` |
| Python | 3.11-3.13 | Compatibility is a purchase decision | Architecture | "Python 3.11 to 3.13" | `width="176" height="20"` |
| Skill install | One clone, nothing to build | Sets the install expectation correctly: this is a skill, not an app | Install guide | "Skill: one clone to install" | `width="144" height="20"` |
| PRs welcome | Contributions open | Lowers the barrier for the first PR | `CONTRIBUTING.md` | "PRs welcome" | `width="90" height="20"` |
| Stars | Social proof | Requested conversion signal; never promised (R-1) | Stargazers | "GitHub stars" | `height="20"` |

Rejected: "platform" and "build" badges add noise without a decision; "Made with
Python" duplicates the Python badge.

Every badge declares the height it is served at (20 px in all 9 states measured);
the four whose text is fixed in the URL also declare their width, and the CI and
stars badges declare no width because their width *is* live content (91/101/201 px
for CI passing / no status / not found, 76/90/94 px for 0 stars / `octocat/Hello-World`
/ `torvalds/linux`). Measurements and the bounded residual shift: 8.5.

## 5. Accessibility

| Check | Requirement | Result |
|---|---|---|
| Contrast, body text | >= 4.5:1 (WCAG 2.1 AA) | 13 text pairs over 21 background checks all pass; lowest pair 5.62:1 (`#8b949e` on the `#161b22` title bar), next 6.35:1 (CEO node label on the indigo end of the accent gradient) |
| Contrast, decorative mark | >= 3:1 | Passes at its worst: NIDVUE frame `#8584F0` on white 3.20:1, NIDVUE N `#5857E8` on the README dark ground 3.56:1, logo node 4.24:1 (non-text, so the 3:1 bar applies). The frame used to be drawn at `opacity="0.92"`, which composites to 2.88:1 on white - fixed this sweep. The banner's hierarchy marks are measured **against the composited background, glow included**: CEO connectors 4.05:1 worst along the three lines (they were 2.77:1 until T-0003), Tester/Ledger 3.98:1 |
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
`#5857E8` on `#0b1020` 3.56:1 and on white 5.33:1 - all above the 3:1 bar. In the
banner, measured on the composited background (gradient + grid + glow) rather
than on a flat fill: CEO connectors `#818cf8` 4.05:1 worst (2.77:1 before T-0003),
Tester/Ledger connectors `#22d3ee` at 0.6 3.98:1, logo node strokes 6.35:1.
Rendered on pixels (`cairosvg`, with the connectors stripped for the background
pass) the same three lines read 3.94 / 4.10 / 4.07:1.

## 6. Conversion checklist

Assertable by a Tester on the merged README.

- [ ] Pitch and project name visible before the first scroll (hero block).
- [ ] Animated demo is the first element after the hero and needs no JS/network.
- [ ] Six badges present, each with alt text and a working link target.
- [ ] Every badge declares `height="20"`; the four static badges (License,
      Python, Skill, PRs) also declare their width, and CI and stars declare none
      (8.5) - a Tester can assert this with a regex over the six tags.
- [ ] Install section installs the skill first (project or user skills directory, or `AGENTS.md` where the host has no skill loader) and demotes pipx/uvx/pip/source to an optional engine.
- [ ] Quickstart is no more than four commands and names the workspace path.
- [ ] Comparison table has 5 alternatives x 6 decision columns, with sources.
- [ ] License (AGPL-3.0-or-later) and the "no personal data" statement are present.
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
  host request `use the tw skill: ...` - the product is a skill, so the demo must not open
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
- README images are sized by their `width`/`height` **attributes**, never by CSS
  alone: github.com's README pipeline rewrites every `<img>` `style`, keeps
  `width`/`height`/`alt`, and generates `max-width: 100%; height: auto;
  max-height: Hpx;` from the two attributes. The attribute pair is therefore what
  reserves the box before the SVG arrives and what caps the demo at 820 px; a CSS
  `max-width` may refine a non-GitHub preview but must never be the only place a
  width is declared.
- A third-party badge declares what the repository owns: its `height` always, its
  `width` only when the URL fixes the text the badge renders. A badge whose width
  is live content (CI status, star count) gets no `width` - a stale pair distorts
  it, an absent one only re-wraps the row by one line (8.5).

## 8. Verification

Three passes are on record: the README/assets deliverable at `e5efc5f`, the
graphics sweep of T-0001, the OG-card generator of T-0005 (8.3), and the badge
row of T-0006 (8.5). The sweep rows were run in the worktree immediately before
the commit that carries this file and re-run at that commit, so the tree they
measured is the tree that landed.

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
- **contrast over a real background** - `Artifacts/T-0003/Scripts/probe_marks.py`
  (T-0003): the flat-fill model above cannot see a gradient, a grid or a glow, so
  this one composites `banner.svg`'s whole background stack at every sample point
  along every mark before compositing the stroke over it, and
  `render_marks.py` (WSL, `cairosvg`) renders the file twice - as shipped and with
  the connectors stripped - so the ratio is measured on painted pixels too.
- **render and look** - `Scratch/render_review.py` under WSL, where the repo's
  `.venv` has `cairosvg` and Pillow: every SVG rasterised at 1x, 2x and 16 px and
  opened; every raster decoded.
- **diagram** - `Scratch/check_mermaid.py`, because no mermaid renderer exists on
  this host and fetching one is not allowed.

All of these scripts live in the agent's gitignored `Scratch/` and `Artifacts/`;
the repository holds no audit code for this.

| Check | Command | Result |
|---|---|---|
| Structure and semantics, all 5 SVGs | `venv\Scripts\python.exe Scratch\verify_assets.py <worktree>` | 5/5 well-formed; 5/5 `role="img"` with `<title>`, `<desc>` and every `aria-labelledby` token resolving; 5/5 declared `width`/`height` = `viewBox`; every `font-family` stack ends in a generic family; 0 `<script>`, `@font-face`, `@import`, `xlink:href`, `<image>`, `base64`, external `href`/`src`/`url()`; geometry inside the viewBox; 13 `<text>` elements in the banner and 11 in the demo (129 and 516 characters of real text), no text drawn as a path |
| Raster container and size | same script | `social-preview.png` 1280x640 colourtype 2 (RGB), chunks `IHDR IDAT IDAT IEND`, no metadata chunk; `nidvue-apple-touch-icon.png` 180x180 colourtype 2; `nidvue-favicon.ico` header `0,1,3`, 16-byte entries, 3 PNG frames 16/32/48, 0 trailing bytes |
| ICO decodes in a real decoder | `.venv/bin/python Scratch/render_review.py` (WSL, Pillow 13.0.0) | `PIL.Image.open` -> `sizes [(16, 16), (32, 32), (48, 48)]`, every frame RGBA (before the repair: `OSError: Truncated File Read`) |
| Contrast | same stdlib script, plus the glow-aware probe `Artifacts/T-0003/Scripts/probe_marks.py` | 13 text pairs over 21 background checks, all >= 4.5:1, worst 5.62:1; marks all >= 3:1, worst 3.20:1 (NIDVUE frame on white). The SVG marks are now measured against the **composited** background (linear gradient + 1 px grid + radial glow), because the flat-fill model this document used first cannot see the glow: banner CEO connectors 2.77 -> 4.05:1, cyan 3.98 / 4.09:1, logo mark 6.35:1 |
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

### 8.3 Social preview generator (T-0005, 2026-10-31)

Host: WSL, the repository's `.venv` (Python 3.14.4, Pillow 13.0.0, cairosvg
2.9.1). The Windows `venv` has neither Pillow nor cairosvg.

| Check | Command | Result |
|---|---|---|
| Rebuild | `.venv/bin/python scripts/render_social_preview.py` | 1280x640 RGB, 73 345 B, sha256 `29615f1a57c54a8d9fac59a5b78002f3bf122a585e9365a51604834ced3916c2` |
| Determinism | the same command run twice | byte-identical, same sha256 |
| Container | stdlib PNG chunk parse | IHDR 1280x640 depth 8 colourtype 2; chunks `IHDR IDAT IDAT IEND`; 0 metadata chunks |
| Pitch input | `README.md:5` (`<p><strong>...</strong></p>`) | `One prompt in. A whole company of agents out.` - period, no comma |
| Windows run | `venv\Scripts\python.exe scripts\render_social_preview.py` | exit 1, `ModuleNotFoundError: No module named 'cairosvg'`; the generator must run in the WSL `.venv` |
| Asset contract | `verify_assets.py <worktree>` | social-preview 1280x640 colourtype 2, chunks `IHDR IDAT IDAT IEND`, 0 metadata; every other asset unchanged |
| Old -> new | `Scratch/t0005/verify_card.py` | 22 660 of 819 200 pixels (2.77%) differ by >8: mark frame `#8f8ef0` -> `#8584f0` (2.88:1 -> 3.20:1), pitch comma -> period, and antialiasing; every content band keeps its box (section 9, IMG-1) |

### 8.4 README layout stability (T-0004, 2026-11-01)

The reviewer's fail at `a00c92c` was correct: the demo's
`style="width:100%;max-width:820px;height:auto"` never reaches github.com, so the
demo rendered `880x513.33` in an 880 px column instead of the reviewed
`820x478.33`, and "renders at 820 px" was false on the product page. The fix moves
the 820 px cap into the attribute pair, where GitHub keeps it.

| Check | Command | Result |
|---|---|---|
| Intrinsic size from each SVG root | `venv\Scripts\python.exe <Artifacts>/T-0004/Scripts/check_sizes.py <worktree>` | banner header `1280x360` = viewBox, declared `1280x360`, both ratios 3.5556, deviation 0.00%; demo header `960x560` = viewBox, declared `820x478`, ratio 1.7155 vs 1.7143, deviation 0.07% (exact height at 820 px is 478.33, so 0.33 px sub-pixel) |
| Served tag shape | `GET api.github.com/repos/Nidvue/Teamwork/readme`, `Accept: application/vnd.github.html`, 2026-11-01 | the icon's author declarations are already gone: served as `width="88" height="88" style="max-width: 100%; height: auto; max-height: 88px;"` - `width`/`height` survive, `style` is GitHub's, no `aspect-ratio` is generated |
| Reserved vs loaded box | `github_harness.py` -> Chrome `--headless=new --dump-dom`, columns 1280/880/820/375, renderers `local` / `github` / `github+aspect-ratio` | `github` renderer (what this repository's pipeline serves), current tags: 8/8 cells reserved == loaded - 7 at `delta_height 0.00`, the demo at a 375 px column at `218.59` reserved vs `218.75` loaded (0.16 px); demo `820x478` at 1280/880/820 columns, i.e. the reviewed width survives; banner `880x247.5` / `820x230.63` / `375x105.47`, unchanged. The same renderer on the pre-fix tag from `a00c92c` reproduces `880x513.33` at an 880 px column |
| Author-CSS renderer | same harness, `local` renderer | demo `820x478.33` loaded against a `820x478` reserved box (0.33 px sub-pixel, no visible reflow); the cap still applies where author CSS is honoured |
| Links | `python scripts/teamwork.py --project <worktree> links` | 0 issues (75 markdown files, 388 internal links) |

Not measured here: a full github.com render (Mermaid, camo image proxy). The
emulation covers the `<img>` box, which is what the finding was about.

### 8.5 README badge row (T-0006, 2026-11-01)

R-18 was titled "a README `<img>` carries no intrinsic height" and T-0004 fixed
the hero and the demo; the six shields.io badges still declared nothing, so the
statement was broader than the fix. Decision, taken as the asset owner:

**Size every badge the repository can size truthfully, and exempt the two whose
width is live content, with the residual shift measured.** 4 of 6 badges now
carry the pair they are served at; the CI and stars badges carry only
`height="20"` because their width changes with the message and the count, so a
declared pair would distort the badge the moment CI fails or a star arrives. No
criterion is relaxed for the hero or the demo (8.4 is unchanged).

| Check | Command | Result |
|---|---|---|
| Served size, shields.io vs camo | `Scripts/badge_sizes.py`, `Scripts/camo_badges.py` 2026-11-01 | 6/6 identical through `camo.githubusercontent.com` (`image/svg+xml`): CI `91x20`, License `160x20`, Python `228x20`, Skill `144x20`, PRs `90x20`, stars `76x20`; no badge has a `viewBox`, the root `width`/`height` is the intrinsic size |
| Is the width a constant of the URL? | same, other states | **no for CI**: 91 passing, 101 no status, 201 repo/workflow not found. **no for stars**: 76 (0), 90 `octocat/Hello-World`, 94 `torvalds/linux`, 146 repo not found. **yes for the four static badges**: 160 / 228 / 144 / 90, unchanged across fetches (the text is in the URL, shields renders it) |
| Height is constant | same, all 9 states | 20 px in every state; `height="20"` is true for all six and cannot distort a scaled badge |
| Reserved == loaded, per badge | `Scripts/badge_harness.py` + Chrome `--headless=new --dump-dom` + `Scripts/report_boxes.py 1280` (and `880`, `340`) | License, Python, Skill, PRs: reserved == loaded, `dW 0.00 dH 0.00`; CI and stars: `0x20` reserved vs `91x20`/`76x20` loaded - the height is reserved for all six, the width of two is not |
| Page shift while the row loads | `Scripts/sweep_shift.py` over 101 column widths, 300-1300 px | **73/101 columns stable at 0.00 px**, including every width >= 820 px (the badge row fits one line at desktop); worst **+26.00 px** (exactly one line) at 28 of 101 widths in 300-810 px, where the two unsized badges push the row onto one more line |
| The same sweep before the change | same harness, `served` variant + the pre-change tags | **0/101 stable**: +2.00 px at >= 820, +28.00 at 490-810, +54.00 at 320-480, +80.00 at 300-310 |
| Why not size all six | `stale-ci` variant (CI declared `91x20`, file 201 px wide) | the box holds at `91x20` and the badge is drawn squashed - a wrong pair is worse than an absent one, which is why the two variable badges get no width |
| Author attributes survive github.com | `GET api.github.com/repos/Nidvue/Teamwork/readme`, `Accept: application/vnd.github.html`, 2026-11-01 | the pipeline reads `width`/`height` per `<img>`: the icon is served `width="88" height="88" style="max-width: 100%; height: auto; max-height: 88px;"`, the banner `width="100%" style="max-width: 100%;"`; the camo rewrite replaces `src`, adds `data-canonical-src` and keeps every other attribute, so a declared pair reaches the reader |
| Links | `python scripts/teamwork.py --project <worktree> links` | 0 issues |

Not measured: the same row on a real github.com page render (the emulation uses
github's `markdown-body` metrics, not its published stylesheet byte for byte),
and the pre-load state of a request that is still in flight rather than one that
has not started - a replaced element with no intrinsic size is the same box in
both, which is the box this row is about.

The residual is real and bounded, not hidden: a reader on a 400-480 px or
650-810 px viewport sees the content below the badge row move by one 26 px line
once, while the two live badges download cold. Removing even that needs a width
the repository does not own, so it stays a recorded, accepted risk (R-24), not a
claim that the row is stable.

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
| generator | `scripts/render_social_preview.py` (Pillow + cairosvg) - rebuilds the raster from the committed mark SVG and the pitch at `README.md:5`; two runs are byte-identical |
| model licence | the shipped social preview was composed programmatically on the earlier host; no third-party image is redistributed and no real person is depicted |
| local fallback | `qimg` (text-to-image and instruction-driven image editing) exists on the authoring host only |
| cloud prompt policy | no private data, no real people, metadata stripped before commit |
| medium decision | vector first: the README banner, logo and terminal demo are hand-authored SVG; a raster exists only for the surfaces that must be raster - the GitHub social preview and the iOS touch icon - and the touch icon is rendered from the SVG rather than drawn |

### Assets

Inventory, measured 2026-10-30 in this worktree and the social preview
re-measured 2026-10-31 (T-0005; `git grep -l -F <path>` = who references it,
`wc -c` = size). "Referenced by" counts the document that records the asset, not
only the surface that displays it.

| id | asset | medium | size | bytes / mode | referenced by | review result |
|---|---|---|---|---|---|---|
| IMG-1 | `assets/social-preview.png` | raster | 1280 x 640 | 73 345 B (71.6 KiB), RGB | `scripts/build_pi_package.py:30` (`PREVIEW`), `scripts/render_social_preview.py` (generator), `.gitattributes:82` (LFS opt-out), Design/Plan/Decisions/Archive, `roles/designer.md` | pass - template layout, real text, measured on white: name 18.55:1, description 8.29:1, accent rule 5.33:1; only IHDR/IDAT/IEND chunks; inside the 40 pt safe area. Pitch now matches the README (period); rebuilt from the current mark, so the frame is full-opacity `#8584F0` (3.20:1) instead of the stale 0.92 composite (2.88:1) |
| IMG-2 | `assets/banner.svg` | svg | 1280 x 360 | declared, 5 027 B | `README.md:2` (hero), Design/Plan/Archive | pass - two defects fixed: the tagline collided with the org chart at the widest font of the stack (25 -> 22 px), and the three CEO connectors sat at 2.78:1 under the glow (found by Reviewer-1 at `1cfb8abd25c812274c06efed20ee75f270c91ad8`; `stroke-opacity` 0.7 -> 1 on that one group -> 4.05:1 worst, measured along each line) |
| IMG-3 | `assets/logo.svg` | svg | 128 x 128 | declared, 964 B | `tests/unit/test_skill_contracts.py:251` (`PROSE_AND_MEDIA_EXAMPLES`), Design/Plan/Archive | pass - the standalone Teamwork mark; **kept, not dead**: it is the fixture that proves `assets/**` is treated as prose/media, and the mark the banner draws at 132 px. It is not on a product surface by design (README shows the *Nidvue* mark) |
| IMG-4 | `assets/demo.svg` | svg | 960 x 560 | declared, 4 778 B | `README.md:19`, Design/Plan/Project/Pi-Packaging/Archive, `tests/unit/test_{skill_contracts,privacy_scan}.py` | pass - one stale line fixed (`12 roles staffed` -> `5 roles staffed, 2 lanes running`, matching the `slim` roster tier) |
| IMG-5 | `docs/assets/nidvue-icon.svg` | svg | 256 x 256 | declared, 608 B | `README.md:3`, `mkdocs.yml:30` (theme logo), `tests/unit/test_skill_contracts.py:1262-1276` | pass - `role=img`, `<title>` + `<desc>`, no external resource, geometry centred in the viewBox; intrinsic size declared and the frame drawn at full opacity this sweep |
| IMG-6 | `docs/assets/nidvue-favicon.svg` | svg | 256 x 256 | declared, 602 B | `mkdocs.yml:31` (favicon), `tests/unit/test_skill_contracts.py:1263,1277` | pass - `<desc>` + `aria-labelledby` added earlier, intrinsic size declared and frame at full opacity this sweep; legible at 16 px on light and dark grounds |
| IMG-7 | `docs/assets/nidvue-favicon.ico` | raster (ICO) | 16 + 32 + 48 | 1 892 B, PNG frames | Plan/Archive only (the trademark set, `NOTICE:14`); no page loads it | **repaired earlier this task** - the directory used 12-byte entries with offsets 12 short, so `PIL.Image.open` raised `OSError: Truncated File Read`; rebuilt with 16-byte entries over the same three frames. Re-verified this sweep: `sizes [(16, 16), (32, 32), (48, 48)]`, all RGBA |
| IMG-8 | `docs/assets/nidvue-apple-touch-icon.png` | raster | 180 x 180 | 1 952 B, RGB | Plan/Archive only, `NOTICE:14` | **repaired this sweep** - it shipped RGBA (alpha 0..255), so iOS composited the transparent ground on black and the indigo N fell to 3.56:1; now rendered opaque from `nidvue-favicon.svg` on the mark's white ground |

#### IMG-1 - social preview

- medium: raster, because the GitHub social preview/OG surface must be a raster
  image; there is no vector channel for it
- design source: **GitHub's official `repository-open-graph-template.png`**, followed
  strictly - 1280x640, white ground, the whole composition inside the template's
  40 pt safe border, and the template's centred stack: icon, then the name in bold,
  then a short two-line description
- composition: the Nidvue mark (168 px on the card, rasterised from the mark SVG
  at 600 px then resized) above **Nidvue Teamwork** in DejaVu Sans Bold 72 px, an
  8 px accent rule, then the pitch read from `README.md:5` and the description in
  DejaVu Sans 32 px - all text drawn with a real font, never generated by an image
  model
- acceptance criteria: 1280x640 exactly, nothing outside the 40 pt safe area, no
  model-rendered lettering, legible at thumbnail size, under 1 MiB as a plain
  (non-LFS) file
- licence / terms: the Nidvue mark is Nidvue's trademark (NOTICE); no third-party
  asset is redistributed and no real person is depicted
- candidates reviewed: the earlier generated illustration was **rejected** for this
  surface - it did not follow the template
- selected: the template-conformant card, rebuilt programmatically
- generator: `scripts/render_social_preview.py` (committed by T-0005), with
  `docs/assets/nidvue-icon.svg` and `README.md:5` as its inputs. Run it in the
  repository's WSL `.venv` (`.venv/bin/python scripts/render_social_preview.py`);
  the Windows `venv` stops at `ModuleNotFoundError: No module named 'cairosvg'`,
  so that host cannot render the card
- evidence (T-0005): two consecutive runs -> byte-identical 1280x640 RGB,
  73 345 B (71.6 KiB), sha256 `29615f1a57c54a8d...`; chunks `IHDR IDAT IDAT IEND`, 0 metadata;
  the generator reads the pitch `One prompt in. A whole company of agents out.`
  from README.md:5, so the card's copy is the README's copy. Against the old card
  (`96ff20db69bc9ae2...`, 71 004 B, comma) 22 660 of 819 200 pixels (2.77%) differ
  and every content band keeps its box: mark 574..705 x 136..267 (identical), title
  281..1004 x 332..387 (identical), rule 276..1003 x 400..406 (was 275..1004 x
  400..407), pitch 256..1020 x 443..473 (was 258..1019; the period replaces the
  comma), description 106..1169 x 488..518 (identical). The rebuild also carries
  the mark's current full-opacity frame `#8584F0` (3.20:1 on white) where the stale
  card held the pre-T-0001 0.92 composite `#8f8ef0` (2.88:1); the frame colour is
  the only intended non-copy change, the rest of the difference is antialiasing
- evidence (T-0001): `PIL` composition @worktree -> 1280x640, 71 004 B (69 KiB; the
  33 KiB figure recorded here earlier was measured before the round-3
  supersampling), content bottom 510 of a 600 safe bottom; re-measured 2026-10-30
  -> 1280x640, colortype 2 (RGB, no alpha), no EXIF or `tEXt` chunk; reviewed
  visually before commit and again in the T-0001 sweep

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
| 8 | banner: `stroke-opacity` 0.7 -> 1 on the CEO connector group only, after Reviewer-1 measured 2.78:1 at `1cfb8abd25c812274c06efed20ee75f270c91ad8` | the 3:1 non-text bar on a mark *required to understand* the content: the connectors are the only element that says Tester hangs off Architect and Ledger off Reviewer, and the glow under the top of the stem lifted the background | pass: 4.05 / 4.31 / 4.18:1 analytic worst per line, 3.94 / 4.10 / 4.07:1 rendered; 1 090 pixels changed, all inside the connector strips; geometry, colour token, width and glow untouched |

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
  checks >= 4.5:1 and every mark >= 3:1, measured against the composited
  background and not a flat fill (section 5, T-0003)

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
| 1 | flattened RGBA to RGB and re-encoded with metadata stripped (625 KiB -> 516 KiB) | "under 1 MiB as a plain file" and the "strip metadata" red line - measured on the generated illustration of that round, not on the shipped card | superseded with the round; the shipped card is 71.6 KiB with only IHDR/IDAT/IEND chunks |

### 2026-10-30 graphics sweep (T-0001)

Every asset was parsed and measured with the stdlib script, rendered with
`cairosvg` at 1x / 2x / 16 px and opened as an image, and the rasters decoded with
Pillow. The rows below are the findings that produced a change or a decision.

| asset | finding (measured) | change |
|---|---|---|
| IMG-2 banner | the tagline overran its column: at the widest member of the font stack (the DejaVu Sans fallback, 601 px) it ended at x = 849 while the org chart's first box starts at x = 832, so the copy collided with `Architect` on any renderer whose font is wider than Arial's | tagline 25 px -> 22 px: worst case 529 px, ends at x = 777, 55 px clear of the chart; copy unchanged |
| IMG-2 banner | **found by Reviewer-1 at `1cfb8abd25c812274c06efed20ee75f270c91ad8`, not by me**: the three CEO connectors (`assets/banner.svg:68-70`, `#818cf8` at `stroke-opacity` 0.7, 2 px) measured **2.78:1** at (1010,124) where the bar is 3:1, and 3.08:1 at y = 180 - the radial glow lifts the background under the top of the stem. My own probe reproduces it: 2.77 / 2.89 / 2.83:1 worst along the three lines analytically, and 2.70 / 2.79 / 2.73:1 on a `cairosvg` render (2.79:1 at (1010,124), 3.07:1 at y = 180, matching the finding). My earlier 3.46:1 came from a flat-canvas model that could not see the glow | `stroke-opacity` 0.7 -> **1** on that one `<g>` - geometry, colour token, width and the glow unchanged, so the chart still reads as one indigo system under the accent-filled CEO node. After: **4.05 / 4.31 / 4.18:1** analytically (worst along each line) and **3.94 / 4.10 / 4.07:1** on the render; the change moves 1 090 pixels of 460 800, all inside the three connector strips (bbox 889,122 - 1130,199, 0 outside), and 5 029 -> 5 027 B |
| IMG-2 banner | measured this pass, no defect fixed: the five role chips (`#818cf8` at 0.6 on the 8 % white pill) sit at 2.47-2.71:1 and the six org boxes at 2.95:1 against their own fill, so they are also under the 3:1 bar | **no change - scoped out, recorded, not waved through**: each pill and box is named by the label inside it (`#e0e7ff` at 11.0-14.2:1), so the outline is a grouping affordance rather than a mark *required to understand* the content under the WCAG 2.1 non-text bar (SC 1.4.11: parts of a graphic required to understand the content) - unlike the connectors, which the CEO ruled are the only element that says Tester hangs off Architect and Ledger off Reviewer. The numbers and the one-attribute fix (`stroke-opacity` ~0.8 on the five pills, ~0.75 on the six boxes) stay here for anyone who disagrees. **Ruled by the CEO on 2026-10-31: decorative, keep them at 2.47-2.95:1** - SC 1.4.11 covers graphics *required to understand* the content, and every one of these shapes is named by a label measured at 11.0-14.2:1, so the outline carries nothing a reader needs |
| IMG-4 demo | `objective accepted: 12 roles staffed, 3 lanes running` matched no roster tier - `ROSTER_TIERS` (`src/teamwork/config.py:367-374`) is `slim` (5 roles: ceo, architect, developer, tester, reviewer), `standard` (8) and `full` (15), and `docs/guide/cli.md:55` states `slim` is the default | corrected to `5 roles staffed, 2 lanes running`. The two lanes are **developer and tester**: the only execution roles in the slim tier (`src/teamwork/config.py:367-374`), against `README.md:52`, which names developer, tester and designer as the parallel lanes and `slim` does not staff the designer. Five roles, six agents - the reviewer is staffed twice (`docs/guide/cli.md:55`); "roles" is the unit the sentence counts. The rest of the transcript is untouched |
| IMG-6 favicon.svg | `role="img"` and a `<title>` but no `<desc>` and no `aria-labelledby`, unlike IMG-5 | added `<desc>` + `aria-labelledby="ft fd"` |
| IMG-7 favicon.ico | the directory used 12-byte entries, so the image offsets were 12 short and `wPlanes` / `wBitCount` read as garbage; `PIL.Image.open` raised `OSError: Truncated File Read` | container rebuilt (6 + 3 x 16 B) over the same three PNG frames; `PIL` now reports frames 16/32/48 |
| IMG-5, IMG-6 (both NIDVUE SVGs) | `viewBox` only, no `width`/`height`, so a bare `<img>` gives the mark a 300x150 default box before CSS runs; and the `#8584F0` frame carries `opacity="0.92"`, which composites to **2.88:1** on white - under the 3:1 bar this document asserts for a meaningful graphic | `width="256" height="256"` declared; `opacity` removed -> 3.20:1 on white, 5.91:1 on `#0d1117`; the two files stay identical apart from their `<desc>` |
| IMG-8 touch icon | shipped RGBA with `alpha` 0..255, so iOS composites the transparent ground on black: the indigo N drops to 3.56:1 and the mark loses its white ground | re-rendered from `nidvue-favicon.svg` at 180x180 on white, saved colourtype 2 (RGB), metadata-free, 1 952 B |
| IMG-1 social preview | pitch read "One prompt in**,** a whole company of agents out." while the README, the banner and the `<h1>` subtitle read "One prompt in**.** A whole company of agents out."; no generator was committed, so the card could not be replayed | superseded by T-0005 (2026-10-31): the committed generator rebuilds the card, the pitch is now the README's (period), and the frame carries the current full-opacity mark (3.20:1) |
| README mermaid flowchart | the flow showed lanes -> self-check -> review -> merge -> loop and sent every fail back to `LANES`, omitting the two steps the protocol is built on: a recorded result at the same revision is **credited** (`--credit`) rather than re-run, and a failed review is re-reviewed as a **delta** by the reviewer that raised the finding | block edited: `REC[(Recorded runs at that revision)]`, `REC -.->|verify once - cite with --credit| RV`, `RV -- fail + findings --> FX[Owner fixes]`, `FX --> SC`; lane group labelled "one per staffed role" |
| IMG-3 logo | measured, no defect: `role=img`, title + desc, no text, no external reference, geometry inside the 128 viewBox | none - the fixture usage is the reason it ships |

Resolved (T-0005) - the card is now replayable and its pitch matches the README.
The comma deviation was accepted in T-0001 only because no generator was
committed; T-0005 commits `scripts/render_social_preview.py` and its inputs,
rebuilds the card from the current mark and the README pitch, and removes the
hand-edit risk. A stranger reproduces the shipped bytes with
`.venv/bin/python scripts/render_social_preview.py` in the repository's WSL
`.venv` (two runs -> the same sha256); the Windows `venv` has no cairosvg and
reports `ModuleNotFoundError: No module named 'cairosvg'`.

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
| F-1 | `.gitattributes:86` | `docs/assets/* -filter -diff -merge -text` marks the NIDVUE **SVGs** as binary too, so `git diff` prints "Binary files differ" for a hand-authored text asset; every change to IMG-5/IMG-6 in this sweep is invisible in the diff a Reviewer reads | Architect / Release Engineer | split the rule: `docs/assets/*.svg -filter -merge` (keep text/diff) and `docs/assets/*.png -filter -diff -merge -text`; `-filter` alone is enough to stay out of LFS |
| F-2 | `README.md:2,19` | the hero `<img>` tags declared no intrinsic height (`width="100%"` and `width="820"`), so the two largest assets shifted the page while loading | Designer | resolved in T-0004: `README.md:2` carries `width="1280" height="360"` (native) and `README.md:19` `width="820" height="478"` (ratio 1.7155 vs the asset's 1.7143, 0.33 px at 820 px wide); the attributes are the whole contract on github.com, whose pipeline replaces every author `style` and derives the box from `width`/`height` alone - measurements in 8.4 |
| F-3 | `assets/social-preview.png` | the pitch on the OG card used a comma where the README uses a full stop, and no generator was committed | closed by T-0005 (Designer): `scripts/render_social_preview.py` rebuilds the card from the current mark and the README pitch; the pitch is now the README's |
| F-4 | `README.md:9-14` | the six third-party badges declared no intrinsic size, so the badge paragraph re-flowed while they loaded - the residual R-18/T-0004 left | closed by T-0006 (Designer): every badge declares `height="20"`; the four with text fixed in the URL also declare `width`; CI and stars declare none because their width is live content. Page shift 0.00 px at 73 of 101 column widths (all >= 820 px), worst +26.00 px where the two live badges cross a line - measurements in 8.5, bound recorded as R-24 |

### Notes

- Generated lettering is the failure mode this surface is most exposed to; every
  candidate was checked explicitly for stray glyphs before selection.
- The raster is committed as a normal binary (opted out of Git LFS in
  `.gitattributes`) so a plain `git clone` has the real file, not a pointer.
- GitHub's social preview is uploaded in repository **Settings**; there is no API
  for it, so the file lives here and the CEO uploads it as a manual release step.

## 10. Agent-state widget (the pi status surface)

Owner: Designer. The developer-ready spec for `extensions/tw-status.ts`:
what the operator must be able to answer, in what order, in how many lines, and
what happens when the terminal is too narrow. It consumes `status --json`
schema 4 and changes no engine behaviour.

Grounding: the reviewer's recorded findings on this path (T-0130 F1-F3, T-0064
F1, the T-0065 narrow-width finding) plus a measured render of the real payload
on this team at 2026-11-15 21:06 (`scripts/teamwork.py status --json` -> schema
4, count 6, counts `{busy 3, idle 3, ready 3, review 0, activated 14, retired
13, lanes_live 1, lanes_ended 124, lanes 6}`). The full defect census is
Reviewer T-0006; the rows below are the ones this pass measured,
and T-0006's list supersedes them where it disagrees.

### 10.1 Information hierarchy

The operator reads the widget at a glance while doing something else. Five
questions, in this order, each answerable without a second glance:

| # | question | answered by | never |
|---|---|---|---|
| H1 | is the machine working, and how much of it? | header: busy, live lanes, reviews | a count of seats that no longer exist |
| H2 | who, and on what task? | the row's glyph + instance + task id | a row with no instance |
| H3 | how long, and is it healthy? | elapsed, progress, lane state | a clock that ticks in place of a state |
| H4 | what is it doing right now? | the activity column, clipped from the right | a command that repeats the elapsed time |
| H5 | what is waiting for me? | review count in the header, `+N more busy`, the idle aggregate | history: ended lanes are not drawn |

`role` is redundant with `instance` in this roster and is not drawn. History
(`retired`, `lanes_ended`, ended lanes) is not drawn: it is the Board's job.

### 10.2 Layout

One row per instance, one line per row, columns in this fixed order - 10.8 holds
the authoritative table with the widths, their derivation and the drop order:

```
<glyph:1> <instance:6-15> <task:7> <used:5> <sep:1><left:4-5> <bar:5> <activity:flex> [<model:<=20>]
```

| column | rule |
|---|---|
| glyph | one per state, 10.3 |
| instance | left, never clipped below 6 characters; the widest busy instance sets the column, capped at 15 - `ReleaseEngineer` is 15 and renders whole |
| task | derived, never drawn raw: take the segment after the last `/` of the payload's `task` (`designer/T-0001` -> `T-0001`, `reviewer/T-0006` -> `T-0006`; a value with no `/` is already the id). A row whose `role` is `reviewer` is a review lane and is drawn `↳` + id (`↳T-0006`) in all 7 cells; every other row is the bare id in 6 cells plus the separator. A `T-nnnn` id is never clipped; a derived value that is not a `T-nnnn` token is clipped to 6 with `…`, because it is not an identity |
| used | the running lane's elapsed clock, right-aligned, 5, `-` when no lane |
| sep + left | `▸` then the estimated time left, right-aligned, 4-5, `-` when no budget is known |
| bar | 5 cells, no percentage text, 5 empty cells when no budget |
| activity | `last · <age>`, the compact state string, clipped from the right with `…`; this is the only elastic column |
| model | last path segment only (not `provider/model`), `<=20`; dropped below 80 columns |

Every column is fixed width except the activity, so the used/left/bar tail starts
at the same index on every row, with or without a budget (D-2). The header and
the idle aggregate are single lines with no columns.

Interface copy, exactly: `teamwork · <busy> busy · <stalled> stalled · <live> live · <review> review`
(a zero count is omitted) and `+<n> more busy`. The widget is the only surface the
extension draws: there is no footer status line (D-21).

### 10.3 Glyph and colour language

The glyph carries the meaning and the word confirms it, so the widget reads the
same in a monochrome terminal and through a screen reader.

| glyph | state | word on the same line | colour token (redundant) |
|---|---|---|---|
| `●` | busy | — (the row is the word) | ok `#3fb950` |
| `▲` | stalled: a task is claimed but no lane is running | `stalled` | warn `#d29922` |
| `◐` | review lane, as the line prefix; `↳` moves into the task column | `↳T-nnnn` | warn `#d29922` |
| `◇` | live lane, no instance row | lane id | ok `#3fb950` |
| `○` | idle aggregate - deleted, never drawn | - | - |
| `‖` `✕` | paused, failed | `pause` / `fail` | warn / danger `#f85149` |
| `▸` | the separator before the time left | — | inherited |
| `+N` | hidden busy rows | `more busy` | inherited |
| `…` | clipped text | — | inherited |

Rules: colour is never the only carrier; the renderer emits no ANSI today, so a
host that adds colour must keep every glyph and word intact. Contrast is the
host theme's obligation at 4.5:1 for body text; the widget ships no escape
sequences and no animation, so `prefers-reduced-motion` and 200% zoom are the
terminal's, not the widget's. **No glyph is emoji-capable**: `⏸` (U+23F8) and `▶`
(U+25B6) carry `Emoji_Presentation=Yes`, so a terminal draws them two cells wide
and every column after the first shifts, and `⚠` (U+26A0) and `⚙` (U+2699) are
emoji-capable, so a font that prefers colour emoji widens them too. 10.10 replaces
them and a test reads the glyph table for the class.

### 10.4 Overflow policy

Applied in this order until the line fits; each step is a whole column, never a
partial glyph:

1. Below 80 columns, drop the model column.
2. Below 72, drop the bar (5 cells of derived data).
3. Below 56, drop the activity and keep its `· <age>` tail.
4. Below 48, drop the `▸` + left column. The used clock is never dropped
   above 48 columns: it is H3.
5. Clip the activity, then the task title, from the right with `…`.
6. Never clip the instance below 6 characters, the task id, the glyph or the
   used clock: a row that cannot fit identity is not rendered at all - it is
   counted in `+N more busy` instead. A line with no subject is the defect this
   rule exists to prevent (measured: at width 40 the current renderer prints
   ` 1m05s ░░░░░   9% deepinfra/deepseek-ai…` with no instance).
7. Never wrap: every emitted line is at most the requested width, including the
   lane lines and the aggregates.
8. Below 32 columns the widget renders the header, the `<glyph> <instance>
   <task>` rows and the `+N more busy` line when rows were dropped. There is no
   footer status line and no idle aggregate.

### 10.5 Line budget

One frozen arithmetic (CEO arbitration M-0001, 2026-11-15). 10.4 step 7 and 10.6
restate it and cite its invariants by name; neither computes a second one.

**BUDGET - the widget is the only surface the extension draws.**
Total `<= 12` lines.

| # | block | lines | rule |
|---|---|---|---|
| 1 | header | 1 | always |
| 2 | busy rows | `k` | `k = min(busy + stalled, 12 - 1 - 1(overflow if hidden > 0) - lane_lines)`; 10.8 puts the stalled rows in the drawn set |
| 3 | `+N more busy` | 0-1 | only when `hidden > 0`; `N = busy - shown`, exact; reserved width, never clipped, and never itself counted as a row |
| 4 | idle aggregate | 0 | deleted: a reconciled roster has no idle seat to count, so the widget draws no idle line |
| 5 | lane-only lines | 0-3 | drawn only from the room left after rows + overflow; first to yield |
| | total widget | `<= 12` | |
| | footer status line | 0 | deleted (D-21): the widget is the only surface, so no `teamwork <busy>/<total> busy` line exists |

**Order, which is the whole of D-9.** Space for the overflow line is subtracted
**before** any row is dropped, so a dropped seat always leaves a visible `+N`.
The overflow line is emitted after the rows: it is
the last row-bearing line, and no row line follows it. Lane lines
are drawn **last**, from what is left - the shipped renderer draws them first
(`extensions/tw-status.ts:196`) and that is D-10.

**INVARIANTS a Tester asserts** (10.6 names them, nothing else does):

- `TOTAL` - `len(lines) <= 12` for every fixture.
- `CONSERVATION` - `shown + hidden == busy`.
- `AGREEMENT` - the header's busy count is `counts.busy`, the one count the
  widget prints; there is no footer to agree with.
- `OVERFLOW` - when `hidden > 0` the `+N` line is present, its `N` is exact and
  not truncated, and no row follows it.

Derivation, computed by `Scratch/accept_t0001_r3.py` from this table (L-0029):
21 busy, 0 idle, 3 lane-only -> rows room `12 - 1 - 1 = 10`, so `k = 10`,
`hidden = 11`, the overflow line is the 12th, and `lane_lines = 0` because no
room is left; 5 busy, 0 idle, 3 lane-only -> `k = 5`, `hidden = 0`, no overflow
line, 6 lines left, `lane_lines = min(3, 6) = 3`, total 9; 1 busy, 1 idle,
0 lanes -> `k = 1`, total 3. The cap binds on lane lines first, never on the
`+N` line: the overflow line is reserved before any row is dropped.

### 10.6 The checks a Tester can assert on

These are the **target** assertions. `tests/unit/test_pi_status_render.py` is
where they run - it imports the extension through node's type stripping - and the
payload is a fixture with busy, idle and lane-only rows. `TOTAL` and `OVERFLOW`
are **red** against the shipped renderer today: `MAX_LINES = 24` at `:8` (D-10)
and the overflow line is sliced after the row loop at `:210`/`:214` (D-9). A
Tester adds them with the fix, not before it; 10.5 is the frozen target, 10.7
names the delta.

| check | assertion |
|---|---|
| no wrap | for width in 24/40/60/80/100: `max(len(line)) <= width` |
| identity survives | at width 40 columns every busy row begins with the busy glyph and carries at least 6 characters of the instance |
| no headless row | every line begins with `●`, `◇`, `○`, `+`, or is the header |
| column alignment | on a payload with one null and one numeric `progress_pct`, the elapsed/bar/model tail starts at the same index in both rows |
| count agreement | header `busy` equals `counts.busy`, and `live` equals `counts.lanes_live` |
| `TOTAL` (10.5) | `len(render(payload, 100)) <= 12` for every fixture in the payload matrix, not only the 21-busy one |
| `CONSERVATION` (10.5) | `shown + hidden == busy`, where `shown` is the count of lines beginning with the busy glyph and `hidden` is the `N` parsed from the `+N more busy` line, or 0 when that line is absent |
| `AGREEMENT` (10.5) | header busy equals `counts.busy` on every fixture |
| `OVERFLOW` (10.5) | when `hidden > 0`: the `+N more busy` line exists, `N == busy - shown`, it is not truncated by the width clip, and no row line follows it (only the idle aggregate may) - on the 21-busy fixture that is 10 rows, `+11 more busy`, and 0 lane lines |
| `LEFT-IS-REAL` (10.8) | on every fixture `left == budget_seconds - elapsed_seconds`, clamped at 0, and `-` when either field is absent; `remaining_text` wins when the engine sends it |
| `NO-INSTANCE-CLIP` (10.8) | `ReleaseEngineer` (15 characters) renders whole at width 100 |
| `STALLED-NOT-BUSY` (10.8) | a stalled row carries `▲` and the word `stalled`, no left and no bar, the header's busy count excludes it and its stalled count includes it |
| `ONE-LINE-PER-AGENT` (10.8) | the count of lines beginning with a row glyph equals the number of distinct instances drawn, and no instance appears twice |
| no colour-only meaning | stripping ANSI from every line leaves each state's word intact |
| determinism | two calls on one payload return identical lines |
| `EMPTY-FEED` | no instances and no lanes -> `[]`, and the extension exports no footer |
| `QUIET-CLEAR` | every seat idle, no live lane and `counts.review == 0` -> `[]`: the panel clears when the last job is done instead of keeping a bare `teamwork` line (`extensions/tw-status.ts`, `tests/unit/test_pi_status_render.py::test_an_all_idle_roster_with_nothing_in_flight_clears_the_table`) |

### 10.7 Defects measured in this pass

Measured at 2026-11-15 21:06 on the real payload; each is a code change in
`extensions/tw-status.ts` and belongs to its owner, not to this document.

| # | defect | where | fix the spec asks for |
|---|---|---|---|
| D-1 | at 40 columns a row loses its glyph and instance: `clip()` gives the tail absolute priority (`room <= 0` returns the tail alone) | `extensions/tw-status.ts:227` | overflow rule 5: drop the row, never render it headless |
| D-2 | the optional progress bar makes the tail width per-row, so columns do not align | `bar()`, `:122` | render a fixed 9-column slot even when `progress_pct` is null |
| D-3 | `provider/model` clipped to 22 reads `deepinfra/deepseek-ai…` on every row: the provider is constant, the model is the signal | `modelLabel()`, `:151` | model name only, provider in the tooltip or dropped |
| D-4 | the header counts activated/live/review while the footer counts busy/total; `busy` is in neither header count and `activated 14` counts 13 retired seats against 6 live rows | `:191`, `:217` | header carries busy/live/review; `activated` is history |
| D-5 | the row title is resolved by task id alone, so the Designer row rendered Tester's `T-0001` title ("Systematic audit of tests/…") | engine status title resolver | resolve by (role, task) or (branch, task); filed as a finding, not a widget change |
| D-6 | the activity column repeats the elapsed time (`1m · lane.start …` on a row whose elapsed is `-`) and clips mid-token | the clock is carried in the tail at `:203` and re-derived as `age · latest` in the middle at `:206`; the mid-token clip is the row call at `:207` | activity is `age · last`; drop the duplicated clock |
| D-7 | unread fields: `role`, `ready`, `retired`, `lanes_ended`, `progress` (text), lane `attempt`, `last_at` | payload vs `render()` | draw or explicitly declare as not drawn (10.1) |
| D-8 | no colour is emitted at all, and `●` and `⚙` share "working" without a word | whole renderer | glyph+word pairs in 10.3 |
| D-9 | a seat disappears with no signal: the overflow line is pushed after the row loop and then cut by the final slice, because the lanes were pushed first and the room formula reserved only the idle line - at 21 busy + 3 lane lines the room is 20, 20 rows are drawn, `+1 more busy` becomes the 25th line and is sliced away | `:196`, `:201`, `:210`, `:214`; repro `Scratch/accept_t0001_r2_21busy.mjs` @15a404da -> `len=24 busyRowsDrawn=20 rowsDropped=1 hiddenLine=[]` | reserve the overflow line before any row is dropped (10.5 step 3, `OVERFLOW`) |
| D-10 | the lane lines are budgeted before the busy rows, so they can starve a row, and the block is capped at 24 lines, not the frozen 12 | lane loop at `:196` runs before the room formula at `:201`; `MAX_LINES = 24` at `:8` | draw rows + overflow + idle first, then lanes from the room left, first to yield (10.5 step 5); cap the block at 12 |
| D-11 | a derived task value that is not a `T-nnnn` token is clipped to 8, while 10.2 fixes that column at 6 | `task_label()`, `text(clean, 8)` at `:132` | clip to 6, or state 8 in 10.2 and widen the column to 8 - the spec asks for 6 so the column stays fixed |

### 10.8 Round 2 - the operator brief (2026-11-15)

Supersedes 10.2-10.4 where they disagree: this row is the layout, 10.3 is the
glyph language, and the numbers below are derived, not assumed. Requirement is
the operator's own words at 2026-11-15 (D-20261115-CEO-7): one line per agent, a
compact state, used and left time, an icon prefix, nothing misleading.

**The row.** One line, never wrapped, these columns in this order and nothing else:

```
<glyph:1> <instance:6-15> <task:7> <used:5> <sep:1><left:4-5> <activity:<=28> [<model:<=20>]

10.9 deletes the bar column, caps the activity at 28 and forbids padding it.
```

| column | width | rule |
|---|---|---|
| glyph | 1 | one per state, table below; the row's word confirms it |
| instance | `max(6, widest busy instance)`, capped at 15 | `ReleaseEngineer` is 15 and is never clipped; below the cap it pads. A clipped instance is a defect |
| task | 7 | the `T-nnnn` tail only. A bare id fills 6 and its 7th cell is the separator; a review row is `↳` + id in all 7. Shipped `task_label()` clips to 8 at `:132` (D-11) |
| used | 5 | the running lane's elapsed, right-aligned, `42s` / `3m01s` / `1h05m`, `-` when no lane |
| sep | 1 | `▸` |
| left | `max(4, widest rendered)`, capped at 5 | the estimated time left, right-aligned, same format as used, `-` when no budget is known |
| activity | flex | the compact state string, clipped from the right at a word boundary with `…`, ending `· 12s` (the age of the last event) when the payload carries it |
| model | `<=20` | last path segment only; dropped below 80 columns |

Width arithmetic, derived (L-0029): `1+1+15+1+7+1+5+1+1+1+5+1+5+1 = 46` fixed
columns at the widest instance and left; 45 when left sits at its 4 floor; the
model tail adds `1+20 = 21`. At 80 columns the activity therefore gets
`80-46-21 = 13`, the narrowest the brief is drawn with every column present.
Derivation: `python3 -c "print(1+1+15+1+7+1+5+1+1+1+5+1+5+1, 80-46-21)"` -> `46 13`.
`left` is 4-5, not 4, because `len('1h05m') = 5`: a fixed 4 would either break the
shared tail index or truncate the clock.

**used and left are clocks, never decoration.** `left = budget_seconds -
elapsed_seconds`, clamped at 0: never negative, never invented. No budget in the
payload means `-` and an empty bar. `remaining_text` wins over the arithmetic
when the engine sends it (it carries its own rounding); the arithmetic is the
fallback.

**Glyph is the line prefix, one per state, the word on the row confirms it.**

| glyph | state | word on the row |
|---|---|---|
| `●` | busy | — (the row is the word) |
| `⚠` | stalled | `stalled` |
| `◐` | review lane, as the prefix | `↳T-nnnn` in the task column |
| `○` | idle aggregate | `idle` |
| `⚙` | lane with no instance row | lane id |
| `⏸` | paused | `pause` |
| `✕` | failed | `fail` |
| `+N` | hidden rows | `more busy` |

**The stalled state.** A row whose payload state is `stalled` is never drawn as
busy: glyph `⚠`, the word `stalled`, no left, no bar, and the activity is the
terminal lane event that killed it (`lane.finish L-0123 · lost`). It is counted
in the header separately, so the operator reads a seat that needs a lane, not
work in flight.

**Header**, one line, a zero count omitted:
`teamwork · <busy> busy · <stalled> stalled · <live> live · <review> review`.
The footer status line is deleted: the widget is the only surface, so the extension
exports no `footer()` and draws no `teamwork <busy>/<total> busy` line (D-21).

**Budget.** 12 lines total, 10.5 unchanged. In 10.5's arithmetic `busy` is the
number of state rows the widget must draw, which is now `busy + stalled`; the four
INVARIANTS keep their spelling and are asserted over that set. Overflow ladder,
applied in order until the line fits:

| width | drops |
|---|---|
| below 80 | the model column |
| below 56 | the activity |
| below 48 | the `▸` + left column |
| below 32 | `<glyph> <instance> <task>` only |

The used clock is never dropped above 48 columns: it is H3.

**Payload contract (schema 5).** `render(payload, width)` keeps its signature
(`extensions/tw-status.ts:158`; the shipped file has no third parameter)
and schema 4 still renders - a missing field degrades to `-`, never to a crash
or an invented value.

| field | type | drawn as | when absent |
|---|---|---|---|
| `budget_seconds` | int \| null | the left clock's budget | left `-`, bar empty |
| `remaining_seconds` | int \| null | the left clock, preferred over the arithmetic | falls back to `budget - elapsed` |
| `remaining_text` | string | the left clock verbatim | falls back as above |
| `elapsed_seconds` | int \| null | the used clock | falls back to `elapsed_text` (schema 4) |
| `started_at` | ISO string | not drawn; row order only | not drawn |
| `activity` | string | the activity column | falls back to `last` (schema 4) |
| `stalled` | bool | the stalled state | the row is busy |
| `state: "stalled"` | string | glyph `⚠` and the word `stalled` | — |
| `counts.stalled` | int | the header's stalled count | counted from the rows |

**Delta from the shipped renderer** (each is a code change, not this document):

| # | measured | where | the spec asks for |
|---|---|---|---|
| D-12 | `ReleaseEngine…`: the instance column caps at 14, so a 15-character instance is clipped | `widthOf()` caps at `INSTANCE_MAX`, `:223`; `text(row.instance, INSTANCE_MAX)`, `:161` | cap at 15, as in the row above |
| D-13 | the bar is `5 cells + " 42%"` = 9 columns and is empty when `progress_pct` is null, so the tail shifts per row | `bar()`, `:122` | 5 cells, no text, 5 cells when empty |
| D-14 | there is no used clock and no left time: `Instance` carries no budget field and the row draws `elapsed_text` only | `Instance` type, `:39`; `elapsed()`, `:135` | the schema-5 fields and `LEFT-IS-REAL` |
| D-15 | there is no stalled state: an instance row is drawn busy whenever it exists, and the header prints `activated` | `stateAbbrev()`, `:146`; `state`, `:42`; header `:191` | `⚠` plus the header's separate stalled count |

**The checks a Tester asserts** are recorded in 10.6: `LEFT-IS-REAL`,
`NO-INSTANCE-CLIP`, `STALLED-NOT-BUSY`, `ONE-LINE-PER-AGENT`.

### 10.9 Round 3 - less ink, and the roster tracks live work

Supersedes 10.8's row template, its bar and its 72-column rung where they
disagree; 10.3's glyph language, 10.5's INVARIANTS and 10.6's checks still stand.
Requirement is the operator's brief at 2026-11-16 (D-20261116-CEO-2): drop the bar
and the percentage, shorten the realtime text, stop filling every line to the
edge, and show only the seats that are really live. Every line number below was
re-derived at this revision (L-0029); 10.8's citations predate the schema-5
rewrite of `extensions/tw-status.ts` and are stale where they disagree.

**The row.** One line, never wrapped, one column fewer than 10.8:

```
<glyph:1> <instance:6-15> <task:7> <used:5> <sep:1><left:4-5> <activity:<=28> [<model:<=20>]
```

| column | width | rule |
|---|---|---|
| glyph | 1 | unchanged, 10.3 |
| instance | `max(6, widest busy)`, cap 15 | unchanged: `ReleaseEngineer` is 15 and is never clipped |
| task | 7 | unchanged: the `T-nnnn` tail; a review row is `↳` + id |
| used | 5 | the running lane's elapsed, right-aligned, `42s` / `3m01s` / `1h05m`, `-` when no lane |
| sep+left | `1+max(4, widest)`, left cap 5 | `▸` then the time left, right-aligned, same format, `-` when no budget. `left = clock(max(budget - elapsed, 0))` |
| activity | `<=28` | the compact state string, clipped from the right at a word boundary with `…`, ending `· 12s` when the payload carries it. **Never padded**: the line ends at its last visible character |
| model | `<=20` | last path segment; dropped below 80 columns |

Two clocks are the whole time story. A bar was a third encoding of the same
number, so the bar column and every `%` are gone, not shrunk.

**Width arithmetic, derived (L-0029).** Fixed columns at the widest instance and
left: `1+1+15+1+7+1+5+1+1+5+1 = 39`; the model tail adds `1+20 = 21`; 10.8's bar reserved `1+5 = 6`, no longer reserved.
`python3 -c "print(1+1+15+1+7+1+5+1+1+5+1, 100-39-21, 80-39-21, 60-39, 39-6-1)"`
-> `39 40 20 21 32`.

| width | model | activity gets | the row ends at |
|---|---|---|---|
| 100 | drawn | 28 (the cap) | <= 60 |
| 80 | drawn | 20 | 80 |
| 60 | dropped | 21 | 60 |
| 40 | dropped | 0 (dropped below 56) | 32 |

**Overflow ladder** - the bar rung is retired, because its only action was the bar:

| width | drops |
|---|---|
| below 80 | the model column |
| below 56 | the activity |
| below 48 | the `▸` + left column |
| below 32 | `<glyph> <instance> <task>` only |

72 now drops nothing; the used clock is never dropped above 48 columns (H3).

**Delta from the shipped renderer** (each is a code change, not this document):

| # | measured | where | the spec asks for |
|---|---|---|---|
| D-16 | the bar is 5 cells of `█`/`░` driven by `progress_pct`, and the tail reserves `1 + BAR_W` for it | `bar()` `:196`-`:200`, `:307`, cells `:285`/`:331` | deleted; no bar glyph and no `%` on any line |
| D-17 | a percentage still reaches the surface through the payload: `"progress": "attempt 1/2, 2% of 10m"` | `status --json`, 2026-11-16T01:33:46 | `progress` is not drawn; `%` never appears |
| D-18 | the activity is clipped at 240 and its cell is padded to the free room, so the model is pushed to the right edge and every row is full width | `ACTIVITY_MAX = 240` `:15`, `:274`, `cell.padEnd(room)` `:339`, `trimEnd()` after the tail `:341` | cap 28, clip at a word boundary, no pad |
| D-19 | `counts.activated` is history and reads 14 against 1 busy and 6 idle | `activated?: number` `:90`; `status --json`, same stamp | not a roster count; no surface prints it as one |
| D-20 | the idle aggregate is drawn whenever any seat is idle, finished or not | `if (idle) lines.push(...)` `:396` | deleted - the widget never prints an idle count because a reconciled roster has none; the panel's `- idle: N seat(s)` line keeps its place as the CLI report |
| D-21 | the extension draws a second surface: a footer status line `teamwork <busy>/<total> busy` repeating the count the header already prints, so two surfaces can disagree | `footer()` `:377` and `ctx.ui.setStatus(KEY, footer(payload))` `:425` @22e00336; repro `grep -n busy extensions/tw-status.ts @22e00336` -> `:383 return teamwork ${busy}/${payload.count ?? rows.length} busy` | deleted: the widget is the only surface, the busy count lives in the header, and an unreadable feed renders `⚠ teamwork: status unavailable` inside the widget |

**Header and counts.** Two counts only, zeros omitted:
`teamwork · <live> live · <review> review`
(`:349`-`:352`). The operator's brief at 2026-11-16 (T-0081) drops `<busy> busy`
and `<stalled> stalled` from this line: the rows already say which seat is busy
or stalled, so the header carried the same fact twice, and it read 0 against a
full roster whenever no lane was live. With no live lane and nothing in review
the line is the bare word `teamwork`, never a trailing separator, and `QUIET-CLEAR`
(10.6) deletes the whole panel when every seat is idle too. Every number
the widget and the panel print is the **current staffed set**, never the
historical activated total: `counts.activated` is history, is not a roster count,
and no surface may print it as one. The `+N more busy` overflow line is a row
count, not a header count, and stays.

**The roster follows the work.** A seat is folded when its lane reached a terminal
state **and** it holds no task, no slot lease, no review claim and no ready work
in its role queue. Folding is move-only to `Runtime/Retired/<Instance>/` (role
memory and queue stay), the CEO is never folded, and a seat with ready work or an
unclaimed review in its role is kept. The fold happens at the next reconcile
(`swarm run`, `pulse --commit`, `lane reap`), never inside `status` - status stays
read-only. The next wave re-adds a seat on demand through the existing scale path,
so this is a fold, not a cap.

**What the operator sees**, measured on `status --json` at 2026-11-16T01:33:46
(`busy 1, stalled 0, idle 6, activated 14, retired 17, count 7, lanes_live 1`):

| | before | after |
|---|---|---|
| header | `1 busy · 1 live` plus a `○ idle: 6` line | `1 live`: the idle line and both the busy and the stalled counts are deleted (T-0081) |
| roster | 7 drawn, 6 of them idle, `activated 14` on the surface | the live seat plus any blocked seat; a folded seat is not drawn and `activated` is never shown |
| one row | bar and percentage, activity padded to the edge | two clocks, activity `<=28`, the line ends where its content ends |

**Checks added to 10.6**: `NO-BAR`, `ACTIVITY-CAP`, `NO-FILL`, `ROSTER-TRACKS`,
`HEADER-LIVE-REVIEW` (the header line carries a `live` count and a `review` count
and nothing else; with both zero it is the bare word `teamwork`).

### 10.10 Round 4 - no glyph the terminal can widen

Four glyphs in the 10.3 table are emoji-capable, so the fixed-width contract in
10.4 holds only while the font declines to draw colour emoji:

| was | is | why the old one was wrong |
|---|---|---|
| `⏸` U+23F8 | `‖` U+2016 | `Emoji_Presentation=Yes`: two cells by default, so a paused lane line shifts every column after it |
| `▶` U+25B6 | `▸` U+25B8 | `Emoji_Presentation=Yes`, same two-cell default, drawn on every running lane |
| `⚠` U+26A0 | `▲` U+25B2 | emoji-capable: a font that prefers colour emoji draws it wide and in colour, and the colour then carries meaning on its own |
| `⚙` U+2699 | `◇` U+25C7 | emoji-capable, and it drew the live lane with the same shape family as the busy dot |

The replacements keep the shape language: filled circle busy, filled triangle
stalled, half circle in review, hollow diamond a lane with no seat. Every glyph in
the table is now `Emoji=No`, so a row's cell count is the terminal's locale
question (ambiguous-width shapes) and never a font's emoji decision.

**Check added to 10.6**: `GLYPH-WIDTH` - every value of the renderer's glyph table
is outside the emoji-capable blocks (U+2300-U+23FF, U+2600-U+27BF) and is not one
of the two geometric shapes with emoji presentation (U+25B6, U+25C0). It reads the
glyph table out of `extensions/tw-status.ts`, so a new glyph cannot be added
without passing it.

### 10.11 The panel: what the operator decides from it (T-0004/AC-D4, T-0005/AC-D6)

Criterion: AC-D4 and AC-D6, written in the task records T-0004 and T-0005 (the
`CRITERION` line of each); Project.md carries the AC-R rows only, so it is not the
criterion's home. The Developer implements this in T-0084; the Technical Writer owns
the docs layer. This section is the design record, written before that code, and it
is the row table T-0084 builds to.

#### Three operator questions, one signal each (AC-D6)

| question | the one signal | field it reads | reads bad when | the action then | current value |
|---|---|---|---|---|---|
| Is the team efficient - is work moving? | live lanes against busy seats | `counts.lanes_live`, `counts.busy` | `lanes_live < busy`: a seat is busy with no lane behind it, so nothing is executing | reclaim the claim or start the lane the task names | 9 live / 9 busy -> good |
| Is it effective - does work leave? | deliverables awaiting a verdict | `counts.review`, split by the `review --queue` footer's `unclaimed` and aged by its `oldest` | `unclaimed > 2 * max(lane_count, 1)` - the bound the queue prints, derived from the lane count it prints on the same line - or `oldest` older than the profile lease (fast 20m, standard 40m, deep 80m). Claimed depth alone is not bad: a claimed review has a lane behind it | add a Reviewer lane, or preempt for the oldest | 3 waiting, 0 unclaimed, oldest 1d -> good on depth, act on age |
| What needs my attention now? | stalled seats | `counts.stalled` | `> 0`: a task is claimed and no lane is running it | reclaim the claim or re-lane the task | 1 stalled -> bad, act |

Every bound above is printed by the command beside it, never estimated (L-0029):

```
teamwork.py status --json | jq -c '.counts|{lanes_live,busy,stalled,review,ready}'
  @2026-11-17T17:43:00 -> {"lanes_live":9,"busy":9,"stalled":1,"review":3,"ready":0}
teamwork.py review --queue -> 3 deliverable(s) to review (0 unclaimed, 0 expired claim(s)), oldest 1d
  / lease: fast 20m, standard 40m, deep 80m / 3 lane(s); add a Reviewer lane when unclaimed > 6
```

The `6` is not a constant. The queue computes it as `2 * max(lane_count, 1)`
(`engine.py`, the `review --queue` capacity line), so the same footer prints `8` on a
4-lane team and `2` on a single lane. Re-derive it from the line, never copy the
digit: 6 claimed reviews on 4 lanes are not a bad value while no lane is starved,
and 7 unclaimed on 4 lanes is still under the bound of 8.

#### Panel element -> field -> record -> meaning -> bad value (AC-D4)

| panel element | `status --json` field | the record it comes from | what the number means | what a bad value looks like |
|---|---|---|---|---|
| seats | `count`, `counts.busy`, `counts.stalled`, `counts.idle` | instance records | the roster the rows are drawn from | `busy + stalled + idle != count`: the header would lie about its own rows |
| per-agent state | `instances[].state`, `.lane_state`, `.stalled`, `.elapsed_seconds`, `.remaining_seconds`, `.last_seconds` | the instance row plus its lane record and last ledger event | what one seat is doing, for how long, and how stale the line is | `stalled == true`, or `state == busy` with `lane_state != running` |
| live lanes | `counts.lanes_live` | lane records in state `running` (`engine.py:12189`) | lanes executing right now | below `counts.busy` |
| ready work | `counts.ready` | task records that are executable now (`_ready_for_role`, `engine.py:12207`) | tasks a lane could start this second | `ready > 0` while `lanes_live == 0`: work queued, nothing running |
| review-queue depth | `counts.review` | task records with status `review` (`awaiting_review`, `engine.py:12208`) | deliverables waiting for an independent verdict | `unclaimed > 2 * max(lane_count, 1)` (the printed bound), or older than the profile lease |

#### Row budget and the hidden count rule (T-0084 implements this)

1. The panel is 10.5's 12 lines, header and footer included: 1 header + at most 10
   seat rows + 1 footer.
2. Seats beyond the tenth collapse into ONE final row `+N more`, counted inside
   the 12; `N = count - rows shown`.
3. Rows are ordered stalled first, then busy by elapsed descending, then review
   lanes, then idle, so the truncation drops the least urgent seats.
4. The header always prints the true counts from `counts`, never the shown rows, so
   the hidden count can never be read as an empty team.

#### Empty, partial and no-tree states

| state | what is drawn | why |
|---|---|---|
| empty (`count == 0`) | `teamwork · no seats` and no rows | a blank panel reads as a broken one |
| partial (`instances` present, a `counts` key absent) | the row is drawn and the missing number is `-` | a fabricated `0` reads as a healthy team |
| no tree (no team tree at the path) | one line `teamwork · no team tree at <path>`, exit 0 | the prompt must never be broken by the panel |

**Checks added to 10.6**: `PANEL-SIGNAL` (every field named in the table exists in a
real `status --json`), `PANEL-BUDGET` (rendered lines <= 12), `PANEL-HIDDEN`
(`rows shown + N == count`), `PANEL-EMPTY` (the three states above render without
an error and without a fabricated number).

## 11. Sources

- [WCAG 2.1 - Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) - accessed 2026-10-17
- [MDN - prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) - accessed 2026-10-17
- [W3C - Images tutorial (text alternatives)](https://www.w3.org/WAI/tutorials/images/) - accessed 2026-10-17
- [GitHub Docs - Creating diagrams (mermaid)](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) - accessed 2026-10-17
- [Shields.io - badge service](https://shields.io/) - accessed 2026-10-17
- [Star History](https://star-history.com/) - accessed 2026-10-17
