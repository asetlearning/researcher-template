---
name: process-notes
description: "Tag, cross-link, and mine the user's own notes in vault/Notes/ideas and vault/Notes/logs: fill tags, link them to sources and concepts, and extract ideas and open questions into Notes/extracted/. Use when the user asks to process, tag, link, or pull ideas out of their notes or logs."
---

# process-notes

Works on the user's living notes. **The body of an `ideas/` or `logs/` note is
the author's:** edit only frontmatter tags and the text between
`<!-- agent:related -->` and `<!-- /agent:related -->` (append an empty block
under `## Related material` if missing). Conventions: `vault/_meta/conventions.md`.

Arguments: `all` (default) or a vault-relative path.

## Steps

1. **Find changed notes.** State lives in `.cache/notes-index.json`
   (path → sha256). With `all`, process notes whose hash changed or that are new;
   with a path, process it unconditionally. List them before editing; check in every 5.
2. **Tag.** Fill missing `agent/human`, `domain/*`, `topic/*`, `status/*`,
   `type/*` and the mirrored `domain`/`status` properties. Reuse registered topics.
   Domain ambiguous → ask.
3. **Link.** Grep the vault for the note's concepts, sources, authors, and
   methods. Rewrite the `agent:related` block as bullets: `[[link]]` + one-line reason.
   Where a note bears directly on a concept or entity hub, list it in the hub's
   *Related material* (hub bullets under *What sources say* are for sources only).
4. **Extract.** Each distinct idea (proposal, conjecture, approach to try) and open
   question becomes `Notes/extracted/<slug>.md` from `_templates/extract-note.md`.
   Update an existing extraction with the same `source` and meaning instead of
   duplicating. Ideas the author abandoned → `status/superseded`.
5. **Record** new hashes in `.cache/notes-index.json`, run `vault_tool.py index`,
   and add one log entry per note in `_meta/research-log.md`.

**Done when** every listed note has complete tags and a filled related block, and
every idea or question in it has an extraction.

## Stop when

A note has no `author:` or belongs to someone else; a note contains credentials or
private personal data (flag it before anything is committed).

## Report

Notes processed, tags changed, links added, extractions created/updated, and ideas
that look ready to become a synthesis or an experiment.
