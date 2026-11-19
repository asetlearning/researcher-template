---
name: literature-scan
description: "Run a literature scan: find candidate sources on a topic or question, get the user's approval, ingest them, and write a synthesis. Use when the user asks what is known about a topic, to review the literature, or to research a question without giving specific sources."
---

# literature-scan

Topic in, approved sources ingested, synthesis out. Conventions:
`vault/_meta/conventions.md`.

## Steps

1. **Restate** the question in one sentence. Ambiguous → ask before searching.
2. **Check the vault.** Read `vault/index.md` and run
   `python3 scripts/vault_tool.py search <keywords>`. Report what's already covered and what's missing; the gap is
   often the real scan.
3. **Search.** `WebSearch` with several phrasings; follow citation trails from the
   best hits (surveys, highly cited work, recent replications). Use
   `lookup_metadata.py --title` to confirm bibliographic details.
4. **Propose 3–7 candidates**, numbered, one line each:
   `author (year), venue: one-line claim; why it's on the list`. Mix foundational
   and recent work, and include dissent if it exists. Fewer real sources beat a
   padded list.
5. **Wait for approval.** The user may add, drop, or reorder. Fetch nothing until
   they confirm.
6. **Ingest** the approved list with the `ingest-source` skill's batch workflow
   (`.claude/skills/ingest-source/batch.md`).
7. **Synthesize** with the `synthesize` skill, using the question from step 1.

**Done when** every approved source has a note (or is recorded unread with a reason)
and the synthesis links all of them.

## Report

Synthesis path, source note paths, hubs created, top 1–3 open questions. If the
literature is thin, say so; recommending "no synthesis yet" is a valid result.
