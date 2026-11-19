#!/usr/bin/env python3
"""Look up bibliographic metadata and a dated citation count for a source.

  lookup_metadata.py 2410.12345            # arXiv id (or arxiv.org URL)
  lookup_metadata.py 10.1145/3292500.3330701   # DOI (or doi.org URL)
  lookup_metadata.py https://example.org/paper  # any URL Semantic Scholar knows
  lookup_metadata.py --title "Attention is all you need"

Prints JSON whose keys match the source-note frontmatter: title, authors, year,
venue, url, doi, arxiv, citation_count, citation_count_date, plus abstract,
sources (services that answered) and warnings. Best effort: a field that no
service returned is null, never guessed.

Services, in order: Semantic Scholar, OpenAlex, arXiv API, Crossref. Citation
counts come from the first service that has one (named in
citation_count_source). Optional keys raise rate limits:
SEMANTIC_SCHOLAR_API_KEY, OPENALEX_API_KEY. A 429 is retried once.
Standard library only.
"""
# Created by: Alex Myasnikov
# Date: November 19, 2026

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "researcher-template/0.1 (metadata lookup)"
TIMEOUT = 30
S2 = "https://api.semanticscholar.org/graph/v1/paper"
S2_FIELDS = "title,authors,year,venue,externalIds,citationCount,url,abstract,publicationVenue"

ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf|html)/|^arxiv:|^)(\d{4}\.\d{4,5})(v\d+)?", re.I)
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)")


def get_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 2:
                raise
            wait = e.headers.get("Retry-After", "5")
            time.sleep(min(float(wait) if wait.replace(".", "", 1).isdigit() else 5, 15))
    raise AssertionError("unreachable")


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def classify(ident: str) -> tuple[str, str]:
    ident = ident.strip()
    m = ARXIV_RE.search(ident)
    if m and ("arxiv" in ident.lower() or re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", ident)):
        return "arxiv", m.group(1)
    m = DOI_RE.search(ident)
    if m:
        return "doi", m.group(1).rstrip(".,;)")
    if re.match(r"^https?://", ident, re.I):
        return "url", ident
    return "title", ident


# --------------------------------------------------------------------------- services


def s2_headers() -> dict:
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    return {"x-api-key": key} if key else {}


def from_s2(paper: dict) -> dict:
    ext = paper.get("externalIds") or {}
    venue = paper.get("venue") or (paper.get("publicationVenue") or {}).get("name")
    return {
        "title": paper.get("title"),
        "authors": [a.get("name") for a in paper.get("authors") or [] if a.get("name")],
        "year": paper.get("year"),
        "venue": venue or None,
        "url": paper.get("url"),
        "doi": ext.get("DOI"),
        "arxiv": ext.get("ArXiv"),
        "abstract": paper.get("abstract"),
        "citation_count": paper.get("citationCount"),
    }


def semantic_scholar(kind: str, value: str) -> dict | None:
    if kind == "title":
        q = urllib.parse.urlencode({"query": value, "fields": S2_FIELDS})
        data = get_json(f"{S2}/search/match?{q}", s2_headers())
        papers = data.get("data") or []
        return from_s2(papers[0]) if papers else None
    prefix = {"arxiv": "arXiv:", "doi": "DOI:", "url": "URL:"}[kind]
    pid = urllib.parse.quote(prefix + value, safe=":/")
    return from_s2(get_json(f"{S2}/{pid}?fields={S2_FIELDS}", s2_headers()))


def from_openalex(work: dict) -> dict:
    loc = (work.get("primary_location") or {}).get("source") or {}
    doi = (work.get("doi") or "").removeprefix("https://doi.org/") or None
    arxiv = None
    if doi and doi.lower().startswith("10.48550/arxiv."):
        arxiv, doi = doi.split(".", 2)[2], None
    return {
        "title": work.get("display_name"),
        "authors": [(a.get("author") or {}).get("display_name")
                    for a in work.get("authorships") or [] if (a.get("author") or {}).get("display_name")],
        "year": work.get("publication_year"),
        "venue": loc.get("display_name"),
        "doi": doi,
        "arxiv": arxiv,
        "citation_count": work.get("cited_by_count"),
    }


def openalex(kind: str, value: str) -> dict | None:
    base = "https://api.openalex.org/works"
    sel = "display_name,publication_year,authorships,primary_location,doi,cited_by_count"
    params = {"select": sel}
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    if kind == "arxiv":
        url = f"{base}/doi:10.48550/arXiv.{value}?{urllib.parse.urlencode(params)}"
    elif kind == "doi":
        url = f"{base}/doi:{urllib.parse.quote(value, safe='/')}?{urllib.parse.urlencode(params)}"
    elif kind == "title":
        params.update({"search": value, "per-page": 1})
        results = get_json(f"{base}?{urllib.parse.urlencode(params)}").get("results") or []
        return from_openalex(results[0]) if results else None
    else:
        return None
    return from_openalex(get_json(url))


def arxiv_api(aid: str) -> dict | None:
    # Trusted endpoint over HTTPS; stdlib expat does not resolve external entities.
    xml = get_text(f"https://export.arxiv.org/api/query?id_list={aid}")
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entry = ET.fromstring(xml).find("a:entry", ns)
    if entry is None or entry.find("a:title", ns) is None:
        return None
    text = lambda tag: (entry.findtext(tag, default="", namespaces=ns) or "").strip()
    published = text("a:published")
    doi = text("arxiv:doi") or None
    return {
        "title": re.sub(r"\s+", " ", text("a:title")),
        "authors": [a.findtext("a:name", default="", namespaces=ns).strip()
                    for a in entry.findall("a:author", ns)],
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "venue": text("arxiv:journal_ref") or "arXiv",
        "url": f"https://arxiv.org/abs/{aid}",
        "doi": doi,
        "arxiv": aid,
        "abstract": re.sub(r"\s+", " ", text("a:summary")) or None,
    }


def from_crossref(item: dict) -> dict:
    parts = (item.get("issued") or item.get("published") or {}).get("date-parts") or [[None]]
    title = (item.get("title") or [None])[0]
    venue = (item.get("container-title") or [None])[0] or item.get("publisher")
    authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "")
               for a in item.get("author") or []]
    return {
        "title": title,
        "authors": [a for a in authors if a],
        "year": parts[0][0] if parts and parts[0] else None,
        "venue": venue,
        "url": item.get("URL"),
        "doi": item.get("DOI"),
        "citation_count_crossref": item.get("is-referenced-by-count"),
    }


def crossref(kind: str, value: str) -> dict | None:
    if kind == "doi":
        data = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(value, safe='/')}")
        return from_crossref(data.get("message") or {})
    if kind == "title":
        q = urllib.parse.urlencode({"query.bibliographic": value, "rows": 1})
        items = (get_json(f"https://api.crossref.org/works?{q}").get("message") or {}).get("items")
        return from_crossref(items[0]) if items else None
    return None


# --------------------------------------------------------------------------- main


def lookup(ident: str, force_title: bool = False) -> dict:
    kind, value = ("title", ident) if force_title else classify(ident)
    result: dict = {k: None for k in ("title", "authors", "year", "venue", "url", "doi",
                                      "arxiv", "abstract", "citation_count")}
    result.update({"citation_count_source": None, "query": ident, "query_kind": kind,
                   "sources": [], "warnings": []})

    def merge(name: str, data: dict | None):
        if not data:
            return
        result["sources"].append(name)
        if data.get("citation_count") is not None and result["citation_count"] is None:
            result["citation_count_source"] = name
        for k, v in data.items():
            if v not in (None, "", []) and result.get(k) in (None, "", []):
                result[k] = v

    attempts = [("semantic-scholar", lambda: semantic_scholar(kind, value)),
                ("openalex", lambda: openalex(kind, value))]
    if kind == "arxiv":
        attempts.append(("arxiv", lambda: arxiv_api(value)))
    if kind in ("doi", "title"):
        attempts.append(("crossref", lambda: crossref(kind, value)))
    for name, fn in attempts:
        try:
            merge(name, fn())
        except urllib.error.HTTPError as e:
            hint = " (rate limited; retry later or set SEMANTIC_SCHOLAR_API_KEY)" if e.code == 429 else ""
            result["warnings"].append(f"{name}: HTTP {e.code}{hint}")
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError, OSError) as e:
            result["warnings"].append(f"{name}: {e}")

    if result.get("doi") and "crossref" not in result["sources"] and result["citation_count"] is None:
        try:
            merge("crossref", crossref("doi", result["doi"]))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            result["warnings"].append(f"crossref: {e}")

    if result["citation_count"] is None and result.get("citation_count_crossref") is not None:
        result["citation_count"] = result["citation_count_crossref"]
        result["citation_count_source"] = "crossref"
    result.pop("citation_count_crossref", None)
    result["citation_count_date"] = dt.date.today().isoformat() if result["citation_count"] is not None else None
    if kind == "title" and result["title"]:
        result["warnings"].append("matched by title: confirm it is the right work")
    if not result["sources"]:
        result["warnings"].append("no service returned metadata; fill fields from the source itself")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ident", nargs="?", help="arXiv id, DOI, or URL")
    ap.add_argument("--title", help="search by title instead")
    args = ap.parse_args(argv)
    if not (args.ident or args.title):
        ap.error("give an identifier or --title")
    result = lookup(args.title or args.ident, force_title=bool(args.title))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["sources"] else 1


if __name__ == "__main__":
    sys.exit(main())
