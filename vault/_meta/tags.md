---
tags: [meta, taxonomy]
---

# Tag registry

The registered values for the controlled tag axes. Rules for using them live in
[[conventions]] § Tags. `python3 scripts/vault_tool.py lint` reads the domain
list below and rejects notes whose `domain/*` is not registered here.

**Register before tagging.** When a source belongs to a field not listed, add
the domain here first (one line: value, one-line scope, date), then tag.

## Domains

One per note: the field whose methodology the source contributes to, not the
field it is applied to. Link the other field through topics or wikilinks.

<!-- Format: - `domain/<value>`: <scope> (registered YYYY-MM-DD) -->
<!-- Example (backticked so it doesn't register): `domain/machine-learning` -->

## Topics

Topics are open-vocabulary but **reuse before inventing**: run
`python3 scripts/vault_tool.py tags --axis topic` to see what is in use. List a
topic here when you create it, so future sessions find it even before many
notes carry it.

<!-- Format: - `topic/<value>`: <one-line scope> -->

## Projects (optional axis)

<!-- Format: - `project/<value>`: <one-line description> -->

## Fixed axes

- `agent/research`: written by the AI researcher; `agent/human`: written by a person
- `status/draft` · `status/review` · `status/validated` · `status/superseded` · `status/rejected`
- `type/<value>`: mirrors the `type` property, see [[conventions]] § Note kinds
- `question`: an open question (extractions)
- `risk/high`: contradicts a result the vault relies on

## Related material

- [[conventions]]
- [[research-log]]
