---
name: connect-vault
description: "Re-tag, re-link, and restructure existing vault notes without ingesting anything new: fill missing connections, create concept or entity hubs retroactively, repair one-way links, migrate notes to the current template, or move notes when the folder structure no longer fits. Use when the user asks to reconnect, relink, retag, clean up, or reorganize the vault or a topic in it."
---

# connect-vault

A connection pass over existing notes. The note's content is the source of truth;
re-fetch sources only when a note is too thin to decide a link. Conventions:
`vault/_meta/conventions.md`.

## Steps

1. **Scope.** Agree with the user on the subset (topic, domain, folder, date range)
   and the kind of pass: retag, relink, template migration, restructure. Up to ~20
   notes per pass; split wider scopes into several passes.
2. **Baseline.** Run `python3 scripts/vault_tool.py lint`, `links`, and
   `orphans --loose`; list the in-scope notes and their problems before editing.
3. **Per note**, one at a time:
   - retag: re-derive `topic/*` against the substance test, reusing existing topics;
   - relink: grep the vault for the note's key terms, authors, and references;
     fill connection-graph properties and their reciprocals;
   - migrate: bring frontmatter and section order to the current template, keeping
     the content;
   - keep `author:` untouched.
4. **Hubs.** Any concept or entity involved in 2+ notes without a hub gets one
   (`concept-note.md` / `entity-note.md`). On hubs touched in this pass, refresh
   `appears_in` and backfill a *What sources say* bullet for every source missing
   one, taken from that source note's Key claims (with location).
5. **Restructure** (moves/renames) only within the agreed scope. After each move,
   `lint` reports links left unresolved; fix them all.
6. **Stale notes** not worth migrating → `status/superseded`, flagged to the user,
   never deleted.
7. **Re-run** `lint`, `links`, `orphans --loose`, then `index`; log before → after
   per note in `_meta/research-log.md`. Check in with the user every 5 notes.

**Done when** the in-scope notes have no `lint` errors and no `links` gaps, and
every change is in the log.

## Stop and ask when

A note has no `author:`, contradicts itself (body vs. frontmatter), or isn't the
kind of note the pass is about.

## Report

Notes changed (before → after summary), hubs created, links repaired, notes flagged,
and patterns worth a synthesis or a map (e.g. "8 sources all cite X").
