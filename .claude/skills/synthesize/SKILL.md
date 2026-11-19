---
name: synthesize
description: "Write or update a synthesis note that answers one question across sources already in the vault: convergence, disagreement, what's settled, contested, open. Use when the user asks to compare, synthesize, or summarize what the vault knows about a topic."
---

# synthesize

Builds `vault/Syntheses/_synthesis-<topic>.md` from existing source notes using
`vault/_templates/synthesis.md`. Ingests nothing new; if sources are missing,
offer the `literature-scan` skill. Conventions: `vault/_meta/conventions.md`.

## Steps

1. **Question.** One sharp sentence, confirmed with the user.
2. **Gather.** Read `vault/index.md`, then `python3 scripts/vault_tool.py search
   <terms>` and `tags --axis topic` to locate every relevant source note and hub;
   list them to the user. Hubs' *What sources say* sections are a ready-made claim
   list; verify each claim against its source note before relying on it.
   An existing synthesis on the question → update it instead of creating another.
3. **Read** each note's TL;DR, Key claims, Limitations, and Evidence. Go back to the
   source itself only when a note is too thin to support a claim.
4. **Write** the synthesis. Every point in Convergence, Disagreement, Settled, and
   Contested cites the source notes behind it; an uncited point is opinion and
   belongs in Recommendation, labelled as such. Disagreement stays visible;
   don't smooth it into consensus.
5. **Link back.** Add the synthesis to each covered source's Related material.
   Fill `sources_synthesized` and `key_concepts`.
6. `python3 scripts/vault_tool.py lint <path>`, fix errors, `vault_tool.py index`,
   log in `_meta/research-log.md`.

**Done when** every source covered appears in `sources_synthesized` and links back,
and every claim outside Recommendation cites a source note.

## Report

Path, sources covered, the 1–3 most decision-relevant findings, open questions.
