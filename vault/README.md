# Research vault

Open this folder in Obsidian (File → Open folder as vault).

| Folder | Holds |
|---|---|
| `Sources/` | one note per source, grouped by domain |
| `Concepts/` | concept hubs: what each source says about an idea, accumulated |
| `Entities/` | people, organisations, tools, products, projects across sources |
| `Syntheses/` | cross-source answers to one question |
| `Maps/` | optional curated entry points (`_moc-<topic>.md`) |
| `Outputs/` | reports, slide decks (Marp), canvases, charts made from the vault |
| `Notes/` | your own ideas and logs; `extracted/` holds what the agent pulled out of them |
| `Inbox/` | drop PDFs or link lists here, then ask the agent to process the inbox (not committed) |
| `Attachments/` | local PDFs, images, and web snapshots (not committed; each note's url/doi recovers them) |
| `_meta/` | conventions, tag registry, research log |
| `_templates/` | note templates (point Obsidian's Templates plugin here) |

`index.md` is the generated catalog of every note (`python3 scripts/vault_tool.py index`).
`Research.base` is a dashboard of sources, concepts, entities, and syntheses.
The rules for every note: [[conventions]].
