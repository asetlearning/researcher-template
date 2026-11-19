---
name: ingest-source
description: "Ingest sources into the Obsidian research vault as structured, tagged, cross-linked notes. Use when the user gives one or more URLs, arXiv ids, DOIs, PDFs, videos, or local files to summarize or add to the vault, or asks to process vault/Inbox/."
---

# ingest-source

Turns each source into one note in `vault/Sources/` and folds what it says into
the concept and entity hubs it touches. Rules (naming, properties, tags, hubs,
linking, content discipline) are in `vault/_meta/conventions.md`; read it and
`vault/_meta/tags.md` first.

## Inputs

- One source: run the per-source steps below, **with** the takeaways check-in.
- Several sources, or `Inbox/`: read [batch.md](batch.md), which wraps the same
  steps **without** the check-in.
- The user says "no check-in" / "just do it": skip step 5 for this run.

## Per-source steps

1. **Identify.** Echo the source back. Ambiguous ("that attention paper") → ask.
2. **Dedupe.** `python3 scripts/vault_tool.py find <arxiv-id|doi|url|title words>`.
   A hit → ask: update the existing note or skip.
3. **Fetch.** `python3 scripts/fetch_source.py <source>` → read the saved file
   (in chunks if long). Changeable web content (`web`, `blog`, `doc`): add
   `--snapshot <source-id>` and set `snapshot:` in the note. Videos/podcasts come
   back as captions with `[hh:mm:ss]` markers; cite those. Fetch fails or is empty →
   `WebFetch`; still nothing → stop and ask for another copy. Never summarize an
   unread source. Figures/tables that carry results: see conventions § Content discipline.
4. **Metadata.** `python3 scripts/lookup_metadata.py <id>` for papers/books
   (citation count gets today's date). Web/video: take author, site, and date from
   the page; set `accessed:` to today.
5. **Check in** (single-source runs). Before writing anything, give the user:
   3–5 key takeaways (each with its location), the proposed domain and topics, the
   concept and entity hubs you'll link or create, and any conflict with existing
   notes. Ask what to emphasise or skip; wait for the answer.
6. **Extract** into `vault/_templates/source-note.md`, section by section:
   abstract verbatim, numbers/definitions/theorems verbatim with locations,
   TL;DR in your words, applying the user's emphasis. Non-English → translate, mark `[trans.]`.
7. **Classify.**
   - `domain`: one registered value; if none fits, register it in `tags.md` (ask if unsure).
   - `topic/*`: `python3 scripts/vault_tool.py tags --axis topic` first; reuse,
     then invent only what passes the substance test; register new topics.
8. **Connect.**
   - **Concept hubs** (`key_concepts`) and **entity hubs** (`entities`: the
     people, orgs, tools central to the source): link existing hubs; create a hub
     (`concept-note.md` / `entity-note.md`) once a second source involves it. For
     every hub linked, add the source to its `appears_in` **and append one bullet**
     to its `## What sources say` (claim + location). If the claim conflicts with a
     bullet already there, add a `**Conflict:**` line and tell the user.
   - `cites` / `cited_by` / `extends` / `supports` / `contradicts`: grep and
     `search` the vault for the source's references and for notes citing it. Add the
     reciprocal links on the targets in the same pass.
9. **Place and name.** Path `Sources/<Domain folder>/<source-id>.md`; check the
   stem is unique with `find`. Look at sibling notes: if their topics differ
   wildly, the folder is wrong.
10. **Write**, then `python3 scripts/vault_tool.py lint <path>` plus each hub you
    touched, and fix every error. Fewer than 3 related links → find real
    connections, or tell the user it is the first note of its kind.
11. **Index and log.** `python3 scripts/vault_tool.py index`; append an
    `ingest` entry to `_meta/research-log.md`. If this makes 10+ ingests since the
    last `vault-check` entry in the log, run the `vault-check` skill now.

**Done when** the note and its touched hubs pass `lint`, every reciprocal link is
on its target, every hub linked has this source's bullet, the index is
regenerated, and every claim in the note traces to a location in the source.

## Report

Path, topics (new ones marked), hubs created/updated (with conflicts flagged),
links added to other notes, open questions, blockers. Changed files are left for
the user to commit.
