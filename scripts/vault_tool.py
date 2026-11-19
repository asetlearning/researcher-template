#!/usr/bin/env python3
"""Vault maintenance CLI for the research vault.

Subcommands:
  find QUERY...        find existing notes by id, title, url, doi, arXiv id, alias
  tags [--axis AXIS]   tag usage counts from frontmatter (reuse before inventing)
  lint [PATH...]       check notes against vault/_meta/conventions.md
  links                report missing reciprocal links (cites/cited_by, concepts, entities, ...)
  orphans [--loose]    notes with no incoming and/or no outgoing wikilinks
  index [--check]      (re)generate vault/index.md, the one-line-per-note catalog
  search TERMS...      ranked full-text search (BM25) over note titles, tags and bodies

Vault root: --vault, else $RESEARCH_VAULT, else <repo>/vault.
Exit code: 0 clean, 1 problems found (lint errors, link gaps, orphans), 2 usage error.
Standard library only.
"""
# Created by: Alex Myasnikov
# Date: November 19, 2026

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Folders whose notes are content (checked by lint/orphans/index/search).
STRICT_DIRS = {"Sources", "Concepts", "Entities", "Syntheses"}
CONTENT_DIRS = STRICT_DIRS | {"Maps", "Notes", "Outputs"}
# Generated catalog; never counted as a link source (it links to everything).
INDEX_NAME = "index.md"
# Never scanned at all.
SKIP_DIRS = {".obsidian", ".trash", "_templates"}

REQUIRED_PROPS = ("title", "type", "domain", "status", "author", "tags")
# Entities (people, orgs, tools) can span fields: domain is optional for them.
ENTITY_OPTIONAL = {"domain"}
SINGLE_AXES = ("agent", "domain", "status", "type")
GENERIC_STEMS = {
    "paper", "note", "notes", "summary", "results", "data", "overview",
    "ideas", "idea", "log", "untitled", "draft", "readme-copy",
}
WEB_TYPES = {"web", "blog", "doc"}
MIN_LINKS = 3

WIKILINK_RE = re.compile(r"\[\[([^\]\|#\n]+?)(?:[#|][^\]\n]*)?\]\]")
FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.S | re.M)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
ITEM_RE = re.compile(r"^\s+-\s*(.*)$|^-\s+(.*)$")
UNQUOTED_FM_LINK_RE = re.compile(r"(?:^|[\s,\[:-])\[\[")
KEBAB_RE = re.compile(r"^_?[a-z0-9][a-z0-9.\-]*$")


# --------------------------------------------------------------------------- parsing


def _unquote(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    return val


def _strip_comment(val: str) -> str:
    """Drop a trailing ' # comment' that is outside quotes."""
    quote = None
    for i, ch in enumerate(val):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or val[i - 1].isspace()):
            return val[:i].rstrip()
    return val.strip()


def _split_flow_list(inner: str) -> list[str]:
    items, buf, quote, depth = [], [], None, 0
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        elif ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        items.append("".join(buf))
    return [_unquote(i) for i in items if i.strip()]


def parse_frontmatter(text: str) -> tuple[dict | None, str, str]:
    """Return (properties, raw_frontmatter, body). Handles the YAML subset the
    templates use: scalars, inline [a, b] lists, and block '- item' lists."""
    m = FM_RE.match(text)
    if not m:
        return None, "", text
    raw = m.group(1)
    body = text[m.end():]
    data: dict = {}
    current: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = KEY_RE.match(line) if not line[0].isspace() else None
        if km:
            key, val = km.group(1), _strip_comment(km.group(2))
            if val == "":
                data[key] = None
                current = key
            elif val.startswith("[") and val.endswith("]") and not val.startswith("[["):
                data[key] = _split_flow_list(val[1:-1])
                current = None
            else:
                data[key] = _unquote(val)
                current = None
            continue
        im = ITEM_RE.match(line)
        if im and current:
            item = _strip_comment(im.group(1) if im.group(1) is not None else im.group(2))
            if not isinstance(data.get(current), list):
                data[current] = []
            if item:
                data[current].append(_unquote(item))
    return data, raw, body


def strip_code(text: str) -> str:
    text = FENCE_RE.sub("", text)
    text = HTML_COMMENT_RE.sub("", text)
    return INLINE_CODE_RE.sub("", text)


def link_stem(target: str) -> str:
    stem = target.strip().split("/")[-1]
    if stem.lower().endswith(".md"):
        stem = stem[:-3]
    return stem.lower()


def links_in(value) -> list[str]:
    """Wikilink stems inside a property value (string or list)."""
    values = value if isinstance(value, list) else [value] if isinstance(value, str) else []
    out = []
    for v in values:
        out += [link_stem(t) for t in WIKILINK_RE.findall(v)]
    return out


# --------------------------------------------------------------------------- model


@dataclass
class Note:
    path: Path
    rel: str
    stem: str  # lowercase
    top: str  # first folder under the vault ("" for root files)
    props: dict | None
    raw_fm: str
    body: str
    out_links: set[str] = field(default_factory=set)

    @property
    def tags(self) -> list[str]:
        t = (self.props or {}).get("tags") or []
        if isinstance(t, str):
            t = [t]
        return [x.lstrip("#") for x in t if x]

    def axis(self, name: str) -> list[str]:
        return [t.split("/", 1)[1] for t in self.tags if t.startswith(name + "/")]

    def prop_links(self, key: str) -> list[str]:
        return links_in((self.props or {}).get(key))

    @property
    def is_content(self) -> bool:
        return self.top in CONTENT_DIRS

    @property
    def is_strict(self) -> bool:
        return self.top in STRICT_DIRS or self.rel.startswith("Notes/extracted/")

    @property
    def is_human(self) -> bool:
        return self.rel.startswith(("Notes/ideas/", "Notes/logs/"))


class Vault:
    def __init__(self, root: Path):
        self.root = root
        self.notes: list[Note] = []
        self.files: dict[str, list[Path]] = defaultdict(list)  # lowercase name/stem -> paths
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                rel = p.relative_to(root).as_posix()
                if fn.endswith(".md"):
                    self.files[fn[:-3].lower()].append(p)
                    self.notes.append(self._load(p, rel))
                else:
                    self.files[fn.lower()].append(p)
        self.by_stem: dict[str, Note] = {}
        for n in self.notes:
            self.by_stem.setdefault(n.stem, n)

    def _load(self, p: Path, rel: str) -> Note:
        text = p.read_text(encoding="utf-8", errors="replace")
        props, raw, body = parse_frontmatter(text)
        top = rel.split("/", 1)[0] if "/" in rel else ""
        note = Note(p, rel, p.stem.lower(), top, props, raw, body)
        links = {link_stem(t) for t in WIKILINK_RE.findall(strip_code(body))}
        for val in (props or {}).values():
            links.update(links_in(val))
        links.discard(note.stem)
        note.out_links = links
        return note

    def resolves(self, stem: str) -> bool:
        return stem in self.files

    def registry(self, axis: str) -> set[str]:
        """Values registered as list items in _meta/tags.md: '- `axis/value`'
        (preferred), '- axis/value' or '- #axis/value'. HTML comments are ignored."""
        path = self.root / "_meta" / "tags.md"
        if not path.exists():
            return set()
        text = HTML_COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
        pat = re.compile(rf"^\s*-\s+[`#]?{axis}/([a-z0-9][a-z0-9\-]*)", re.M)
        return set(pat.findall(text))


def resolve_vault(arg: str | None) -> Path:
    root = Path(arg or os.environ.get("RESEARCH_VAULT") or REPO_ROOT / "vault").expanduser()
    if not root.is_dir():
        sys.exit(f"vault not found: {root} (use --vault or RESEARCH_VAULT)")
    return root.resolve()


# --------------------------------------------------------------------------- find


def cmd_find(vault: Vault, args) -> int:
    words = [w.lower() for w in args.query]
    hits = []
    for n in vault.notes:
        p = n.props or {}
        fields = [n.stem, n.rel]
        for key in ("title", "url", "doi", "arxiv", "aliases", "authors"):
            v = p.get(key)
            fields += v if isinstance(v, list) else [v] if v else []
        hay = " ".join(str(f) for f in fields).lower()
        if all(w in hay for w in words):
            hits.append(n)
    if not hits:
        print("No matches.")
        return 0
    for n in sorted(hits, key=lambda n: n.rel):
        print(f"{n.rel}\t{(n.props or {}).get('title', '')}")
    return 0


# --------------------------------------------------------------------------- tags


def cmd_tags(vault: Vault, args) -> int:
    counts: Counter = Counter()
    for n in vault.notes:
        if n.is_content:
            counts.update(n.tags)
    prefix = f"{args.axis}/" if args.axis else ""
    rows = [(c, t) for t, c in counts.items() if t.startswith(prefix)]
    if args.axis in ("topic", "domain", "project"):
        used = {t.split("/", 1)[1] for _, t in rows}
        rows += [(0, f"{args.axis}/{v}") for v in vault.registry(args.axis) - used]
    for c, t in sorted(rows, key=lambda r: (-r[0], r[1])):
        print(f"{c:5d}  {t}")
    if not rows:
        print("No tags in use yet.")
    return 0


# --------------------------------------------------------------------------- lint


def lint_note(n: Note, vault: Vault, domains: set[str], topics: set[str], names: Counter):
    out: list[tuple[str, str, str]] = []  # (severity, code, message)

    def err(code, msg):
        out.append(("E", code, msg))

    def warn(code, msg):
        out.append(("W", code, msg))

    if n.path.name.lower() != "readme.md":
        if names[n.stem] > 1:
            err("duplicate-name", f"'{n.stem}' exists {names[n.stem]} times; [[links]] are ambiguous")
        if n.stem.lstrip("_") in GENERIC_STEMS:
            err("generic-name", f"'{n.path.name}' is generic; qualify it (conventions § Naming)")
        if not KEBAB_RE.match(n.path.stem):
            warn("name-case", f"'{n.path.name}' is not lowercase kebab-case")

    if "[[<" in strip_code(n.body):
        err("placeholder-link", "bare [[<placeholder>]] in body; wrap it in backticks")
    for line in n.raw_fm.splitlines():
        if UNQUOTED_FM_LINK_RE.search(_strip_comment(line)):
            err("unquoted-fm-link", f"quote wikilinks in frontmatter: {line.strip()!r}")

    for stem in sorted(n.out_links):
        if not vault.resolves(stem):
            warn("unresolved-link", f"[[{stem}]] does not resolve to a note or file")

    if n.props is None:
        (err if n.is_strict else warn)("no-frontmatter", "missing frontmatter")
        return out

    p = n.props
    if n.is_human:
        if not p.get("author"):
            warn("missing-author", "personal note has no author:")
        if not n.axis("topic"):
            warn("missing-topic", "no topic/* tag (run process-notes)")
        return out

    report = err if n.is_strict else warn
    entity = n.top == "Entities"
    for key in REQUIRED_PROPS:
        if not p.get(key) and not (entity and key in ENTITY_OPTIONAL):
            report("missing-property", f"missing '{key}'")
    for axis in SINGLE_AXES:
        vals = n.axis(axis)
        if entity and axis in ENTITY_OPTIONAL and not vals:
            continue
        if len(vals) != 1:
            report("tag-count", f"needs exactly one {axis}/* tag, has {len(vals)}")
        elif axis in ("domain", "status", "type") and p.get(axis) and p[axis] != vals[0]:
            report("mirror-mismatch", f"property {axis}: {p[axis]!r} != tag {axis}/{vals[0]}")
    if not n.axis("topic"):
        (warn if entity else report)("missing-topic", "needs at least one topic/* tag")
    for d in n.axis("domain"):
        if d not in domains:
            report("unregistered-domain", f"domain/{d} is not registered in _meta/tags.md")
    for t in n.axis("topic"):
        if t not in topics:
            warn("unregistered-topic", f"topic/{t} is not listed in _meta/tags.md")

    real_links = {s for s in n.out_links if vault.resolves(s)}
    if len(real_links) < MIN_LINKS:
        # A warning, not an error: the first notes in a fresh vault have nothing
        # to link to yet. The skills ask the agent to find links or flag the note.
        warn("few-links", f"{len(real_links)} resolving outgoing links; want >= {MIN_LINKS}")

    if n.top == "Sources":
        if not p.get("url") and not p.get("doi"):
            warn("missing-url", "source has neither url nor doi")
        if p.get("type") in WEB_TYPES and not p.get("accessed"):
            warn("missing-accessed", "web content needs accessed: YYYY-MM-DD")
        if p.get("citation_count") and not p.get("citation_count_date"):
            warn("undated-citations", "citation_count without citation_count_date")
    return out


def cmd_lint(vault: Vault, args) -> int:
    names = Counter(n.stem for n in vault.notes if n.path.name.lower() != "readme.md")
    domains, topics = vault.registry("domain"), vault.registry("topic")
    targets = vault.notes
    if args.paths:
        wanted = {Path(p).resolve() for p in args.paths}
        targets = [n for n in vault.notes if n.path.resolve() in wanted]
        missing = wanted - {n.path.resolve() for n in targets}
        for m in sorted(missing):
            print(f"{m}: not a note inside {vault.root}")
        if missing:
            return 2
    else:
        targets = [n for n in targets if n.is_content]
    n_err = n_warn = 0
    for n in sorted(targets, key=lambda n: n.rel):
        for sev, code, msg in lint_note(n, vault, domains, topics, names):
            if sev == "W" and args.errors_only:
                continue
            print(f"{n.rel}: {sev} {code}: {msg}")
            n_err += sev == "E"
            n_warn += sev == "W"
    print(f"\n{len(targets)} notes checked: {n_err} errors, {n_warn} warnings")
    return 1 if n_err else 0


# --------------------------------------------------------------------------- links

# (property on A, property on B that must list A)
RECIPROCAL = [
    ("cites", "cited_by"),
    ("cited_by", "cites"),
    ("contradicts", "contradicts"),
    ("key_concepts", "appears_in"),
    ("entities", "appears_in"),
]


def reciprocal_pairs(note: Note) -> list[tuple[str, str]]:
    """Pairs that apply to a note; a hub's appears_in points back through
    key_concepts (concepts) or entities (entities)."""
    pairs = list(RECIPROCAL)
    if note.top == "Concepts":
        pairs.append(("appears_in", "key_concepts"))
    elif note.top == "Entities":
        pairs.append(("appears_in", "entities"))
    return pairs


def cmd_links(vault: Vault, args) -> int:
    gaps = []
    for a in vault.notes:
        if not a.is_content:
            continue
        for prop, back in reciprocal_pairs(a):
            for stem in a.prop_links(prop):
                b = vault.by_stem.get(stem)
                if b is None or b is a:
                    continue
                if a.stem not in b.prop_links(back):
                    gaps.append(f"{b.rel}: {back} is missing \"[[{a.path.stem}]]\"  (from {a.rel} {prop})")
        for stem in a.prop_links("sources_synthesized"):
            b = vault.by_stem.get(stem)
            if b is not None and a.stem not in b.out_links:
                gaps.append(f"{b.rel}: no link back to synthesis [[{a.path.stem}]]")
    for g in sorted(set(gaps)):
        print(g)
    print(f"\n{len(set(gaps))} missing reciprocal links")
    return 1 if gaps else 0


# --------------------------------------------------------------------------- orphans


def cmd_orphans(vault: Vault, args) -> int:
    incoming: dict[str, set[str]] = defaultdict(set)
    for n in vault.notes:
        if n.rel == INDEX_NAME:
            continue
        for s in n.out_links:
            incoming[s].add(n.stem)
    found = []
    for n in sorted(vault.notes, key=lambda n: n.rel):
        if not n.is_content or n.path.name.lower() == "readme.md":
            continue
        out = {s for s in n.out_links if vault.resolves(s)}
        inc = incoming[n.stem] - {n.stem}
        isolated = not out and not inc
        if isolated or (args.loose and (not out or not inc)):
            label = "isolated" if isolated else "no-out" if not out else "no-in"
            found.append(f"[{label}] {n.rel}  ({len(inc)} in, {len(out)} out)")
    mode = "loose: no incoming OR no outgoing" if args.loose else "strict: no links either way"
    for f in found:
        print(f)
    print(f"\n{len(found)} orphans ({mode})")
    return 1 if found else 0


# --------------------------------------------------------------------------- index

# Section whose first paragraph summarizes each kind of note in the index.
SUMMARY_SECTION = {
    "Sources": "TL;DR", "Concepts": "Definition", "Entities": "Summary",
    "Syntheses": "Question", "Maps": None, "Outputs": None, "Notes": None,
}
INDEX_ORDER = ["Syntheses", "Concepts", "Entities", "Sources", "Maps", "Outputs", "Notes"]
SECTION_RE = r"^##\s+{}\s*$\n(.*?)(?=^#{{1,2}}\s|\Z)"


def section_summary(body: str, heading: str | None, limit: int = 160) -> str:
    if not heading:
        return ""
    m = re.search(SECTION_RE.format(re.escape(heading)), body, re.M | re.S)
    if not m:
        return ""
    for para in re.split(r"\n\s*\n", strip_code(m.group(1))):
        text = " ".join(para.split())
        if text and not text.startswith(("<", ">")):
            return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
    return ""


def render_index(vault: Vault) -> str:
    groups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    count = 0
    for n in sorted(vault.notes, key=lambda n: n.stem):
        if not n.is_content or n.path.name.lower() == "readme.md":
            continue
        p = n.props or {}
        meta = ", ".join(str(x) for x in (p.get("type"), p.get("year")) if x)
        line = f"- [[{n.path.stem}]]"
        if p.get("title") and p["title"].lower() != n.stem:
            line += f" {p['title']}"
        if meta:
            line += f" ({meta})"
        summary = section_summary(n.body, SUMMARY_SECTION.get(n.top))
        if summary:
            line += f": {summary}"
        sub = ""
        if n.top == "Sources":
            sub = p.get("domain") or "unclassified"
        elif n.top == "Notes":
            sub = n.rel.split("/")[1] if n.rel.count("/") >= 2 else ""
        groups[n.top][sub].append(line)
        count += 1
    out = ["---", "tags: [meta, index]", "---", "", "# Index", "",
           "> Generated by `python3 scripts/vault_tool.py index`; do not edit by hand.",
           f"> {count} notes. Agents: read this first, then `vault_tool.py search` for detail.", ""]
    for top in INDEX_ORDER:
        if top not in groups:
            continue
        out += [f"## {top}", ""]
        for sub in sorted(groups[top]):
            if sub:
                out += [f"### {sub}", ""]
            out += groups[top][sub] + [""]
    return "\n".join(out).rstrip() + "\n"


def cmd_index(vault: Vault, args) -> int:
    path = vault.root / INDEX_NAME
    text = render_index(vault)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.check:
        stale = current != text
        print(f"{INDEX_NAME} is {'out of date: run vault_tool.py index' if stale else 'up to date'}")
        return 1 if stale else 0
    if current != text:
        path.write_text(text, encoding="utf-8")
    print(f"wrote {path.relative_to(vault.root)} ({text.count(chr(10) + '- [[')} entries)")
    return 0


# --------------------------------------------------------------------------- search

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]*[a-z0-9]|[a-z0-9]")
STOPWORDS = set("""a an and are as at be by for from has have in is it its of on or that the
this to was were with which what how why when who not no can do does""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def cmd_search(vault: Vault, args) -> int:
    docs = [n for n in vault.notes if n.is_content and n.path.name.lower() != "readme.md"
            and (not args.dir or n.top == args.dir)]
    terms = tokenize(" ".join(args.terms))
    if not terms or not docs:
        print("No matches.")
        return 0
    k1, b = 1.5, 0.75
    tfs, lengths = [], []
    for n in docs:
        p = n.props or {}
        # Title, aliases and tags count three times: they are deliberate retrieval fields.
        boosted = " ".join(str(x) for x in [p.get("title") or "", n.stem, *n.tags,
                                            *(p.get("aliases") or [])])
        toks = tokenize(boosted) * 3 + tokenize(strip_code(n.body))
        tfs.append(Counter(toks))
        lengths.append(len(toks) or 1)
    avg = sum(lengths) / len(lengths)
    df = {t: sum(1 for tf in tfs if t in tf) for t in set(terms)}
    scored = []
    for n, tf, length in zip(docs, tfs, lengths):
        score = 0.0
        for t in terms:
            if not tf[t]:
                continue
            idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * length / avg))
        if score > 0:
            scored.append((score, n))
    if not scored:
        print("No matches.")
        return 0
    for score, n in sorted(scored, key=lambda x: -x[0])[: args.limit]:
        snippet = ""
        for line in strip_code(n.body).splitlines():
            if any(t in line.lower() for t in terms) and not line.startswith("#"):
                snippet = " ".join(line.split())[:140]
                break
        print(f"{score:6.2f}  {n.rel}\t{(n.props or {}).get('title', '')}")
        if snippet:
            print(f"        {snippet}")
    return 0


# --------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: $RESEARCH_VAULT or <repo>/vault)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("find", help="find notes by id, title, url, doi, arXiv id")
    s.add_argument("query", nargs="+")
    s = sub.add_parser("tags", help="tag usage counts")
    s.add_argument("--axis", help="agent | domain | topic | status | type | project")
    s = sub.add_parser("lint", help="check notes against the conventions")
    s.add_argument("paths", nargs="*", help="only these notes (default: all content notes)")
    s.add_argument("--errors-only", action="store_true")
    sub.add_parser("links", help="missing reciprocal links")
    s = sub.add_parser("orphans", help="notes without links")
    s.add_argument("--loose", action="store_true", help="also report one-way orphans")
    s = sub.add_parser("index", help="regenerate vault/index.md")
    s.add_argument("--check", action="store_true", help="only report whether it is up to date")
    s = sub.add_parser("search", help="ranked full-text search")
    s.add_argument("terms", nargs="+")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--dir", choices=sorted(CONTENT_DIRS), help="only notes in this top folder")
    args = ap.parse_args(argv)
    vault = Vault(resolve_vault(args.vault))
    return {"find": cmd_find, "tags": cmd_tags, "lint": cmd_lint, "links": cmd_links,
            "orphans": cmd_orphans, "index": cmd_index, "search": cmd_search}[args.cmd](vault, args)


if __name__ == "__main__":
    sys.exit(main())
