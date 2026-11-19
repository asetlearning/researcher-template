---
name: vault-check
description: "Health-check the research vault: mechanical checks (frontmatter, tags, broken, one-way and placeholder links, duplicates, orphans, stale index) and a semantic audit (contradictions, stale claims, missing hubs, gaps). Use when the user asks to check, lint, validate, or audit the vault, or before committing vault changes."
allowed-tools:
  - Read
  - Grep
  - Glob
  - "Bash(python3 scripts/vault_tool.py *)"
---

# vault-check

Two passes: a mechanical pass the scripts decide, then a semantic pass that
needs reading. Report both; fix only what the user approves.

## 1. Mechanical pass

```
python3 scripts/vault_tool.py lint
python3 scripts/vault_tool.py links
python3 scripts/vault_tool.py orphans --loose
python3 scripts/vault_tool.py index --check
```

## 2. Semantic pass

Work topic by topic (`vault_tool.py tags --axis topic`), reading TL;DRs, Key
claims, and hub *What sources say* sections rather than whole notes:

- **Contradictions**: sources or hub bullets making incompatible claims without
  a `**Conflict:**` line or a `contradicts` link.
- **Stale claims**: a synthesis or hub statement resting only on sources older
  than a newer source on the same topic that it doesn't mention.
- **Missing hubs**: a concept or entity named in 2+ notes, or an unresolved link
  target from `lint` that recurs, with no hub.
- **Missing connections**: notes sharing 2+ topics or a hub with no link between
  them where one clearly bears on the other.
- **Gaps**: topics with one source, open questions repeated across notes, claims
  marked contested: phrase each as a concrete `literature-scan` query.

## 3. Report

Group findings by severity:

- **Errors**: `lint` errors, unresolved links, missing reciprocal links,
  unflagged contradictions.
- **Warnings**: orphans, stale index, stale claims, missing hubs.
- **Info**: missing connections, gaps (with suggested queries), `lint` warnings.

Each finding: what, where (paths), proposed fix.

## 4. Fix (with approval)

Mechanical fixes directly (mirrored property, quoted frontmatter link, reciprocal
link, backticked placeholder, `index`). Contradictions: add `**Conflict:**` lines
and `contradicts` links, never pick a winner. Hubs and restructures go through
`connect-vault`. Re-run the mechanical pass, report before → after counts, and
append a `vault-check` entry to `_meta/research-log.md` (the ingest cadence counts
from it).

**Done when** the mechanical pass is clean or every remaining item is listed with
its reason, and every semantic finding is either fixed or in the report.
