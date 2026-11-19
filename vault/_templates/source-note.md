---
title: <title in English>
type: <paper | preprint | article | book | chapter | thesis | web | blog | video | podcast | talk | dataset | repo | report | doc>
authors: []                      # people or organisation, as credited
year: <YYYY>
venue: <journal | conference | publisher | site | channel>
url: <canonical link>
doi: <optional>
arxiv: <optional arXiv id>
attachment: <optional "[[file.pdf]]" — local only, not committed; url/doi must recover it>
snapshot: <optional "[[source-id-snapshot]]" — local text copy of web content, not committed>
accessed: <YYYY-MM-DD — required for web content that can change>
language: en                     # language of the SOURCE (filtering); the note itself is English
domain: <one registered domain>  # mirrors the domain/* tag (Bases reads this property)
status: draft                    # mirrors the status/* tag
citation_count: <optional, papers/books>
citation_count_date: <YYYY-MM-DD when citation_count was looked up>
key_concepts: []                 # - "[[concept-name]]"
entities: []                     # - "[[entity-name]]" people, orgs, tools central to the source
cites: []                        # vault sources this one cites
cited_by: []                     # vault sources that cite this one
extends: []                      # builds directly on
supports: []                     # gives evidence for
contradicts: []                  # disagrees with
quality_notes:                   # OPTIONAL — only something specific (retraction, failed replication, errata)
author: <owner handle>
tags:
  - agent/research
  - type/<type>
  - domain/<one>
  - topic/<one>
  - topic/<two>
  - status/draft
---

# <title>

## Abstract

<The source's own summary, verbatim: paper abstract, book blurb, page lede,
video description. Translated sources: translate and end with `[trans.]`.
No own summary → write "None provided." and rely on the TL;DR.>

## TL;DR

<2–3 sentences, your distillation: what would someone need to know to decide
whether to read this? Retrieval framing, not the author's framing.>

## Question

<What question or problem does the source address?>

## Approach

<How it answers it: proof strategy, experimental design, method, argument,
or structure of the work. Cite locations (section / page / timestamp).>

## Key claims

<Verbatim numbers, theorems, definitions, and the central claims, each with its
location. Don't paraphrase numbers. Results that live in a figure or table are
written out in text with the figure/table number.>

## Assumptions

<What the source takes for granted: setting, data, scope, premises.>

## Limitations

<What it does not claim or cannot support, as stated by the author or observed.>

## Evidence and reception

<Replications, rebuttals, errata, notable citations. "Unknown" is a valid answer.>

## Why it matters

<1–2 paragraphs: where it sits among what's already in the vault, what it
enables or rules out. No invented project relevance.>

## Quotes

<At most 2, short, verbatim, with location. Translated → `[trans.]`.>

## Open questions

<Concrete, bounded questions the source raises and leaves open.>

## Related material

<At least 3 substantive wikilinks, mirroring the frontmatter.>

- Concepts: `[[<concept>]]`
- Entities: `[[<entity>]]`
- Cites / cited by: `[[<source>]]`
- Extends / supports / contradicts: `[[<source>]]`
- Syntheses / maps: `[[<_synthesis-topic>]]`
