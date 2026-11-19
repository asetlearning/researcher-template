---
tags: [meta, convention]
---

# Vault conventions

Single source of truth for how notes in this vault are named, placed, tagged,
and linked. The researcher agent (`.claude/agents/researcher.md`) and every
skill in `.claude/skills/` follow this file. Change the rules here, not in the
skills.

## Goal

A note's value is **retrieval over time**. Each note should be findable again
(tags, properties, unique name) and connected to what it relates to (wikilinks).
A note nobody can find, or that links to nothing, is reading, not research.

## Layout

```
vault/
├── Sources/<Domain>/<source-id>.md   one note per source (paper, article, book, web page, video, …)
├── Concepts/<concept-name>.md        hubs: ideas many sources rely on; accumulate what each source says
├── Entities/<entity-name>.md         hubs: people, orgs, tools, products, projects
├── Syntheses/_synthesis-<topic>.md   cross-source views on one question
├── Maps/_moc-<topic>.md              optional Maps of Content (curated entry points)
├── Outputs/                          derived artifacts: reports, Marp decks, canvases, charts
├── Notes/ideas/                      human-owned idea notes
├── Notes/logs/                       human-owned work logs (dated entries)
├── Notes/extracted/                  agent-written ideas / open questions pulled from ideas/ and logs/
├── Inbox/                            drop zone: PDFs, link lists, clippings waiting to be ingested
├── Attachments/                      local PDFs, images, snapshots/ (not committed; see Attachments below)
├── index.md                          generated catalog, one line per note (never edit by hand)
├── _meta/                            conventions, tag registry, research log
└── _templates/                       note templates
```

- `<Domain>` is the folder form of a registered `domain/*` value (see
  [[tags]]): `domain/machine-learning` → `Sources/Machine learning/`.
- Create a sub-folder under a domain only when 3+ sources cluster there.
  Folders are for browsing; tags and properties are the retrieval layer.
- Never put files at the vault root except `README.md`, `index.md`, and `.base` dashboards.

## Note kinds

| Kind | Folder | Template | `type` property |
|---|---|---|---|
| Source | `Sources/` | `_templates/source-note.md` | `paper`, `preprint`, `article`, `book`, `chapter`, `thesis`, `web`, `blog`, `video`, `podcast`, `talk`, `dataset`, `repo`, `report`, `doc` |
| Concept hub | `Concepts/` | `_templates/concept-note.md` | `concept` |
| Entity hub | `Entities/` | `_templates/entity-note.md` | `person`, `org`, `tool`, `product`, `project` |
| Synthesis | `Syntheses/` | `_templates/synthesis.md` | `synthesis` |
| Map of content | `Maps/` | (free form) | `moc` |
| Output | `Outputs/` | (free form) | `report`, `deck`, `canvas`, `chart` |
| Personal note | `Notes/ideas`, `Notes/logs` | `_templates/personal-note.md` | `idea`, `log` |
| Extraction | `Notes/extracted/` | see `extract-note.md` | `idea`, `question` |

## Naming

1. **Lowercase kebab-case**, globally unique **without folder context**: Obsidian
   resolves `[[name]]` by filename alone.
2. Source ids:
   - Papers / books: `<first-author>-<year>` or `<first-author>-<coauthor>-<year>`;
     add a slug word on collision (`smith-2021-attention`).
   - Preprints without a stable venue: `arxiv-<id>` (e.g. `arxiv-2410.12345`).
   - Web pages, blogs, docs: `<site>-<slug>` (`distill-feature-visualization`).
   - Videos / talks / podcasts: `<speaker-or-channel>-<year>-<slug>`.
3. Never use generic names alone: `paper`, `note`, `notes`, `summary`,
   `results`, `data`, `overview`, `ideas`, `log`. Qualify them.
4. The `_` prefix is reserved for index-like notes: `_synthesis-*`, `_moc-*`.
5. Check uniqueness before writing:
   `python3 scripts/vault_tool.py find <stem>`.

## Properties (frontmatter)

Obsidian Bases filters on **properties**, not tags, so key tag axes are
mirrored as properties. Every Sources/, Concepts/, Syntheses/ note has:

- `title`, `type`, `author` (the human owner's handle), `language`
- `domain` — mirrors the single `domain/*` tag
- `status` — mirrors the single `status/*` tag
- `tags` — see below

Wikilinks inside frontmatter **must be quoted**: `- "[[note-name]]"`.
Unquoted `[[x]]` is parsed by YAML as a nested list.

Sources add: `authors`, `year`, `venue` (journal / publisher / site / channel),
`url`, and when known `doi`, `arxiv`, `accessed` (date read, required for web
content that can change), `citation_count` + `citation_count_date`. Fields that
don't apply to a type stay empty; don't invent values.

### Connection-graph properties (sources)

| Property | Meaning | Reciprocal |
|---|---|---|
| `key_concepts` | concept hubs this source introduces or relies on | hub's `appears_in` |
| `entities` | entity hubs central to this source (authors' lab, tool used, …) | hub's `appears_in` |
| `cites` | other vault sources this one cites | target's `cited_by` |
| `cited_by` | vault sources that cite this one | target's `cites` |
| `extends` | builds directly on | — |
| `supports` | provides evidence for the claims of | — |
| `contradicts` | disagrees with the results or claims of | target's `contradicts` |

Frontmatter is the source of truth; the body's *Related material* section
mirrors it. `python3 scripts/vault_tool.py links` checks reciprocity.

## Hubs (concepts and entities)

Hubs are where knowledge **accumulates across sources**:

- Create a hub when 2+ sources rely on the concept or involve the entity (or the
  user asks to track it). Entities need no `domain`; add one only if obvious.
- Every ingest that links a hub appends one bullet to its `## What sources say`:
  `` `[[source]]` (location): claim``. Bullets are never rewritten; a source that
  disagrees adds its own bullet plus a `**Conflict:**` line naming both sources.
- *Definition* / *Summary* stay short and are revised only when sources warrant it;
  full arguments belong in syntheses.

## Index and search

`index.md` at the vault root is **generated** by `python3 scripts/vault_tool.py
index`: one line per content note (title, type, year, TL;DR / definition /
summary / question). Regenerate it after every write pass; never edit it. Agents
read it first to navigate, then use `python3 scripts/vault_tool.py search <terms>`
(ranked full-text) for detail. Past several hundred notes, a dedicated search tool
such as qmd is an optional upgrade.

## Tags

Every content note carries:

1. exactly one `agent/*` — who wrote it: `agent/research` (AI) or `agent/human`
2. exactly one `domain/*` — registered in [[tags]] **before** use, as a list
   item: ``- `domain/<value>`: <scope> (registered YYYY-MM-DD)``
3. one or more `topic/*` — see the substance test below
4. exactly one `status/*` — `draft`, `review`, `validated`, `superseded`, `rejected`
5. one `type/*` matching the `type` property (`type/paper`, `type/web`, …)

Optional: `project/*` when the note belongs to a named workstream; `question`
for open-question extractions; `risk/high` when a source contradicts a result
you rely on.

**Substance test for topics:** "Would I want this note to surface when someone
searches this topic?" Passing mentions don't count. 4–10 topics is typical; no
upper bound if every tag passes. Lowercase, hyphenated, specific
(`topic/contrastive-learning`, not `topic/learning`). **Reuse before inventing**:
`python3 scripts/vault_tool.py tags --axis topic` lists what exists. Register a
new topic in [[tags]] when you create it.

## Linking

- Every Sources/, Concepts/, Syntheses/ note ends with `## Related material`
  holding **at least 3 substantive wikilinks** (concept hubs, related sources,
  a synthesis or map). A note with no outgoing links is incomplete. If a source
  is genuinely the first of its kind, flag it to the user instead of padding.
- Links are **bidirectional** where the table above says so: when you add the
  forward link, add the back-link on the target in the same pass.
- Substance test for links: would a reader following it land somewhere
  genuinely relevant? No aspirational links.
- **Placeholders must be backticked.** In templates and examples write
  `` `[[<note>]]` ``, never a bare `[[<note>]]`: Obsidian parses it as a real
  link and creates a phantom node. The same applies to any literal text
  containing `[[`, including inside `$…$` math; backticks are the only safe escape.

## Content discipline

- **Cite or it didn't happen.** Every claim in a note traces to a location in
  the source (section, page, timestamp, heading).
- **Numbers, theorems, definitions, quotes: verbatim**, with location. The
  TL;DR is your distillation; the Abstract section is the author's own words.
- **No invented relevance.** Don't add "this could apply to X" unless the user
  gave you a project brief.
- **No invented quality verdicts.** `quality_notes` only when there's something
  specific (retraction, replication failure, single-group citations, known errata).
- **Vault language is English.** Translate non-English source text; mark
  translated abstracts and quotes with `[trans.]`; record the source language
  in `language:`. On first use of a term without a clean English equivalent,
  keep the original in parentheses.
- **Figures and tables.** Results that live in a figure or table are written out
  in text with the figure/table number. When text extraction mangles a table,
  render the page (`pdftoppm -png -r 110 -f N -l N file.pdf <out-prefix>`, output in
  `.cache/`) and read the image.
- **Unread is not summarized.** If a source can't be fetched, record it as
  unread (title + url) rather than summarizing from the title or memory.

## Ownership

- `author:` names the human who owns the note (the person who asked for it).
  Never strip or change it.
- Bodies of `Notes/ideas/` and `Notes/logs/` notes belong to their human author.
  Agents may only edit their frontmatter tags and the fenced block between
  `<!-- agent:related -->` and `<!-- /agent:related -->`.
- Restructures (moves, renames, retags across many notes) are logged in
  `_meta/research-log.md` with before → after.

## Attachments

PDFs and the contents of `Inbox/` and `Attachments/` are gitignored: they can be
re-downloaded. So every source note must carry what's needed to recover its file:
`url` and, when they exist, `doi` / `arxiv`. A note whose only copy is a local
file says so in `quality_notes` and names where the file came from.
An `attachment:` link is a local convenience, never the only reference.

**Snapshots.** Web content changes and disappears. For `web`, `blog`, `doc`, and
other changeable sources, save the extracted text with
`fetch_source.py <url> --snapshot <source-id>` (→
`Attachments/snapshots/<source-id>-snapshot.md`, local only) and link it as
`snapshot: "[[<source-id>-snapshot]]"`. Re-check claims against the snapshot, not
the live page.

## Renaming

Renaming outside Obsidian does not update links. After a rename, run
`python3 scripts/vault_tool.py lint` — it reports unresolved links — and fix
each one. Log the rename in `_meta/research-log.md`.

## Related material

- [[tags]]
- [[research-log]]
