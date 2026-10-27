# Documentation standard

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Coordination](Coordination.md)

## Documentation standard (markdown, structured, linked)

Everything the team writes - memory, plans, designs, research, decisions, docs -
is **markdown**, structured for a human reader, and cross-linked both ways.
This is enforced: `teamwork.py links` fails on broken links, malformed URLs, bare
URLs and missing back-links, and `audit` includes link health.

### Structure

- One `# H1` per file; the title states what the document is.
- A one-line `Owner:` line naming the role that maintains it.
- A `Related:` line directly under the header with relative links to every
  document it interacts with (see the link graph below).
- Numbered `##` sections in reading order; `###` only when it earns its depth.
- Prefer tables and short bullets over paragraphs. One idea per bullet.
- Mark placeholders as `<like this>` so unfinished sections are obvious.

### Be concise (hard)

Saved content is read by humans under time pressure. Every file must be short
enough to scan.

- Lead with the conclusion; put the detail under it, never before it.
- One fact per line. Prefer a table row or a bullet over a paragraph.
- Write the smallest text that is still unambiguous. Delete anything the reader
  already knows, any restatement of the brief, and any sentence that only
  announces what the next sentence does.
- No filler: no "as mentioned above", "it is important to note", "in order to",
  "various", "several", "etc." Lists are exhaustive or they are not lists.
- Numbers over adjectives: "12ms p99", not "quite fast". `<command> -> <result>`,
  not "we verified it".
- A memory entry is **one line**: the fact, plus a key. If it needs three
  paragraphs, it belongs in a document, not in memory.
- Cap each section at roughly one screen. If it grows past that, split the
  document or move detail to a linked file.
- Rewrite, do not append. Documents and memory entries are kept current, not
  accumulated; stale text is deleted rather than left below new text.

### Links

- **External references always carry a direct, working link plus an access date**:
  `- [title](https://full-url) - accessed YYYY-MM-DD`. Never cite a search page,
  a bare domain, or "the docs" without a URL. A claim without a link is
  `UNVERIFIED` and cannot justify a decision.
- **Internal references are relative markdown links** to the file
  (`[PLAN](Plan.md)`), never absolute paths and never bare file names in prose.
- **Bidirectional**: if A links to B, B links back to A. Put the back-link in the
  `Related:` line, which is why every shared document has one.
- Every decision cites the evidence and the documents it affects; every research
  claim cites its source; every task result cites the artifact and the command.

### Link graph (committed docs, every edge bidirectional)

```text
PROJECT ─ PLAN ─ BOARD ─ ARCHIVE
   │       │      │        │
   │       ├──────┴────────┴── RISKS ─ COSTS
   │       │                     │
   ├── ARCHITECTURE ─ DESIGN     │
   │        │                    │
   ├── RESEARCH ─────────────────┘
   └── DECISIONS  (links to ARCHITECTURE, RESEARCH, RISKS, COSTS, ARCHIVE, PLAN)
```

`teamwork.py links` verifies it. `.pi/` memory files link to `TaskQueue.md`,
`Role.md`, `ShortTermMemory.md`, `LongTermMemory.md`, global memory and the committed docs
they inform.
