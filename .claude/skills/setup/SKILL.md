---
name: setup
description: "First-time setup of this research workspace: record the owner handle, register the first research domains, check tools. Use when CLAUDE.md shows `Owner handle: <unset>`, or the user asks to set up or configure the workspace."
---

# setup

Run once per copy of the template. Each step is skippable except the handle,
since every note's `author:` depends on it.

## Steps

1. **Owner handle.** Ask the user (AskUserQuestion) for their name and a short
   handle: lowercase letters, digits, hyphens, e.g. a GitHub username. Replace
   `<unset>` on the `Owner handle` line of `CLAUDE.md` with it, keeping the
   backticks. No handle → stop; skills can't write notes without one.
2. **Domains.** Ask which broad fields the research will cover (1–3 to start;
   more get registered as sources arrive). Add each to `vault/_meta/tags.md`
   under *Domains* as ``- `domain/<kebab-value>`: <one-line scope> (registered YYYY-MM-DD)``.
   The folder `vault/Sources/<Domain name>/` is created by the first note, not now.
3. **Tools.** Check and report:
   - `python3 --version` ≥ 3.10;
   - `pdftotext -v` (poppler-utils), needed for PDFs; give the install command
     for the user's OS if missing;
   - `pdftoppm` (same package) to read figure/table pages as images;
   - `defuddle` (optional, cleaner web extraction: `npm install -g defuddle-cli`);
   - `yt-dlp` (optional, video/podcast captions: `pipx install yt-dlp`);
   - `python3 -m unittest discover -s tests` passes.
4. **API keys (optional).** If the user has `SEMANTIC_SCHOLAR_API_KEY` or
   `OPENALEX_API_KEY`, they set them in their shell profile. Keys never go into a
   file in this repo.
5. **Obsidian.** Tell the user: open `vault/` as a vault; in Settings → Files and
   links set *Default location for new attachments* to `Attachments`; enable the
   core Templates plugin with template folder `_templates`.
   **Web Clipper** (optional, recommended): install the Obsidian Web Clipper browser
   extension and set its default save location to this vault's `Inbox` folder; then
   "process the inbox" ingests clipped pages (the clip becomes the local snapshot).
6. **Check.** `python3 scripts/vault_tool.py lint` runs clean.

**Done when** `CLAUDE.md` carries a real handle, and the user has seen the
domains registered and the tool check results.

## Report

```
✓ Owner handle: <handle>
✓ Domains: <list | none yet>
✓ Tools: python <v>, pdftotext/pdftoppm <ok|missing>, defuddle <ok|optional>, yt-dlp <ok|optional>, tests <ok>
→ Open vault/ in Obsidian; try: /ingest-source <url>
```
