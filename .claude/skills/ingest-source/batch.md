# Batch ingest

For 2+ sources or the contents of `vault/Inbox/`. The per-source check-in
(step 5) is skipped; step 1 below is the batch's single check-in.

1. **List** the sources with a count (for `Inbox/`: every file and every URL found
   in link-list or clipped Markdown files). Ask whether to proceed with all or a
   subset, and whether anything deserves emphasis.
2. **Order** foundational sources before the ones that build on them when that
   is obvious; say so if you reorder.
3. **Per source**, run the per-source steps in [SKILL.md](SKILL.md) except step 5,
   **sequentially** — later notes link to earlier ones. After each, sweep the
   earlier notes of this batch for `cites` / `extends` / `contradicts`
   relations and add both directions.
4. **Context discipline.** Write each note (and its hub bullets) before fetching
   the next source; keep only one source's full text in view. Past 10 sources,
   check in with the user every 5 ("6/14 done: …").
5. **Hub sweep.** Every concept or entity involved in 2+ notes of the batch (or the
   batch plus existing notes) gets a hub with `appears_in` and one *What sources
   say* bullet per source.
6. **Synthesis?** If the batch answers one question, offer to run the
   `synthesize` skill on it.
7. **Inbox cleanup.** Move ingested Inbox PDFs to `Attachments/` and link them
   from the note (`attachment: "[[file.pdf]]"`). PDFs are not committed, so make
   sure the note's `url` / `doi` / `arxiv` can recover the file. Clipped web pages
   (Markdown from Obsidian Web Clipper) become the note's snapshot: move them to
   `Attachments/snapshots/<source-id>-snapshot.md`. Remove processed URLs from link
   lists. Leave anything that failed in place.
8. **Index once** at the end (`vault_tool.py index`), one `ingest` log entry for the
   batch, and the lint-cadence check from step 11 of SKILL.md.
9. **Report** per source (path + topics), then the batch: hubs created or
   updated, conflicts found, cross-batch links, failures, open questions.

A source that fails to fetch → ask whether to skip it and continue.
