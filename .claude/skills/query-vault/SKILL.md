---
name: query-vault
description: "Answer a question from what the research vault already contains, with citations to notes and source locations, and offer to save good answers back. Use when the user asks what they know, what the vault says, or any question about topics, sources, people, or tools they've collected."
allowed-tools:
  - Read
  - Grep
  - Glob
  - "Bash(python3 scripts/vault_tool.py *)"
---

# query-vault

Answers from the vault, not from memory. Writes nothing itself: saving an
answer is handed to the `synthesize` skill. Conventions: `vault/_meta/conventions.md`.

## Steps

1. **Restate** the question in one sentence; ambiguous → ask.
2. **Navigate.** Read `vault/index.md` (regenerate first with
   `python3 scripts/vault_tool.py index` if `index --check` says it's stale), then
   `python3 scripts/vault_tool.py search <key terms>` with 2–3 phrasings. Start
   with syntheses and hubs (their *What sources say* sections already gather claims
   across sources), then the source notes they cite.
3. **Read** the notes that bear on the question. Follow wikilinks one hop
   when a cited note is thin. Open a source snapshot or the source itself only when
   a note can't support a needed detail.
4. **Answer** in the form the question calls for (direct answer, table, list,
   short narrative). Every factual statement cites a note `[[note]]`, plus the
   source location the note gives. Keep three things apart:
   - **from the vault**: cited;
   - **conflicting**: both sides, both cited;
   - **not in the vault**: say so plainly. Your own background knowledge appears
     only when labelled as such, never mixed into cited statements.
5. **Offer follow-ups:**
   - the answer compares or connects several sources → offer to save it as a
     synthesis (`synthesize` skill, with this question);
   - gaps → offer a `literature-scan` with concrete search queries;
   - a figure, deck, or report would help → offer to write it to `vault/Outputs/`.

**Done when** every statement in the answer is cited, labelled as conflicting, or
labelled as not in the vault.
