# researcher-template

A starting point for AI-assisted research: collect, read, and connect papers,
web pages, PDFs, books, videos, and your own notes in an Obsidian vault, with a
researcher agent and skills for Claude Code.

Distilled from the research setup of the `math-agents` vault, with the
math-specific, multi-user, and multi-agent (Maestri) parts removed.

## Quick start

1. Copy or clone this repo (or use it as a GitHub template).
2. Open the folder in Claude Code. Skills and the agent are project-scoped,
   so there's nothing to install.
3. Open `vault/` in Obsidian (File → Open folder as vault).
4. Run `/setup` (Claude also offers it on first use): records your owner
   handle, registers your first research domains, checks tools.
5. Ask:
   - `/ingest-source https://arxiv.org/abs/1706.03762`, or just "add this paper to the vault: …"
   - "process the inbox" (after dropping PDFs, link lists, or Web Clipper pages into `vault/Inbox/`)
   - `/query-vault` "what do I know about X?" (cited answers from your notes)
   - `/literature-scan` "what is known about X?"
   - `/synthesize` "compare what the vault says about X"
   - `/connect-vault` "relink everything tagged topic/X"
   - `/process-notes` (tags, links, and mines `vault/Notes/`)
   - `/vault-check`

Requirements: Python ≥ 3.10 (stdlib only), `pdftotext`/`pdftoppm` (poppler-utils) for PDFs.
Optional: the `defuddle` CLI gives cleaner web extraction; `yt-dlp` gives video and
podcast captions; the Obsidian Web Clipper feeds `vault/Inbox/`;
`SEMANTIC_SCHOLAR_API_KEY` / `OPENALEX_API_KEY` raise API rate limits.

## Layout

```
.
├── CLAUDE.md / AGENTS.md        agent context (AGENTS.md points other agents at CLAUDE.md)
├── .claude/
│   ├── settings.json            pre-approves the scripts in scripts/ and the test command
│   ├── agents/researcher.md     researcher subagent: role, toolbelt, write scope, stop conditions
│   └── skills/                  one skill per workflow
│       ├── setup/               first run: owner handle, domains, tool check
│       ├── ingest-source/       sources → notes + hub claims (single with check-in, batch.md, Inbox)
│       ├── query-vault/         question → cited answer from the vault; offers to save it
│       ├── literature-scan/     topic → candidates → approve → ingest → synthesis
│       ├── synthesize/          existing notes → cross-source synthesis
│       ├── connect-vault/       retag / relink / migrate / restructure existing notes
│       ├── process-notes/       your ideas & logs → tags, links, extracted ideas/questions
│       └── vault-check/         mechanical checks + semantic audit (contradictions, staleness, gaps)
├── scripts/
│   ├── fetch_source.py          URL / arXiv id / PDF / HTML / video → clean text (or local snapshot)
│   ├── lookup_metadata.py       arXiv id / DOI / URL / title → metadata + dated citation count
│   └── vault_tool.py            find · search · tags · lint · links · orphans · index
├── tests/                       offline unit tests for scripts/
└── vault/                       the Obsidian vault
    ├── Sources/ Concepts/ Entities/ Syntheses/ Maps/ Outputs/ Notes/{ideas,logs,extracted}/
    ├── Inbox/ Attachments/      local only (gitignored): PDFs, clips, web snapshots
    ├── index.md                 generated one-line-per-note catalog (vault_tool.py index)
    ├── _meta/conventions.md     THE rules (naming, properties, tags, linking, discipline)
    ├── _meta/tags.md            registered domains / topics
    ├── _meta/research-log.md    append-only log of passes and restructures
    ├── _templates/              source, concept, entity, synthesis, personal, extract
    └── Research.base            Obsidian Bases dashboard
```

## Design choices

- **Rules live in one place.** `vault/_meta/conventions.md` is the single source of
  truth; the agent and skills point to it instead of restating it. Change a rule
  there and every workflow follows.
- **One skill per workflow** rather than one `/research` skill with mode flags:
  each skill triggers on its own words, stays short, and new workflows are added
  as new folders without touching the others. The `researcher` subagent ties them
  together for long, delegated runs.
- **Skill names avoid `research`**, so they don't collide with a personal
  `~/.claude/skills/research` skill installed for another vault.
- **Properties mirror tags** (`domain`, `status`, `type`) because Obsidian Bases
  filters on properties.
- **Sources are rigorous, hubs accumulate.** Each source gets one note with verbatim,
  located claims; every concept or entity hub it touches gets a cited *What sources
  say* bullet, so cross-source knowledge builds up without rewriting anyone's claims
  (a hybrid of a literature database and Karpathy's "LLM wiki").
- **Generated, not maintained, index.** `vault/index.md` is rebuilt from frontmatter
  by a script, so it can't drift; agents read it first, then use ranked `search`.
- **Source-agnostic notes.** One `source-note` template with a `type` property
  (paper, web, book, video, dataset, …); fields that don't apply stay empty.
- **Scripts are deterministic helpers**, stdlib-only, with no network in tests.
  Judgment (what to tag, which links are real) stays with the agent; checks
  (`lint`, `links`, `orphans`) are mechanical.

## Checks

```sh
python3 -m unittest discover -s tests       # script tests
python3 scripts/vault_tool.py lint          # conventions
python3 scripts/vault_tool.py links         # reciprocal links
python3 scripts/vault_tool.py orphans --loose
python3 scripts/vault_tool.py index --check  # catalog up to date
```

## License

[CC BY-NC 4.0](LICENSE): free to use, adapt, and share with attribution, not for commercial purposes.

## Extending

- **New workflow** → `.claude/skills/<name>/SKILL.md` (frontmatter `name` and a
  trigger-focused `description`; steps ending in a "Done when" criterion; rules
  referenced from `conventions.md`). Add it to the table in
  `.claude/agents/researcher.md`.
- **New note kind** → template in `vault/_templates/`, a row in
  `conventions.md` § Note kinds, and (if it needs checks) a folder rule in
  `scripts/vault_tool.py`.
- **Another agent role** (e.g. experimenter, reviewer) → `.claude/agents/<role>.md`
  with its own write scope.
