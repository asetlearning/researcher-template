#!/usr/bin/env python3
"""Fetch a source as clean text and save it for reading.

Accepts a URL, an arXiv id (2410.12345, arXiv:2410.12345v2), or a local file
(.pdf, .html, .md, .txt). Saves the text to .cache/sources/<slug>.md (or
--out) and prints a JSON summary: {source, method, path, chars, title}.

--name <source-id> names outputs after the vault note: text to
.cache/sources/<source-id>.md and, for PDF sources, the PDF to
vault/Attachments/papers/<source-id>.pdf (local, uncommitted).

--snapshot <source-id> saves instead to vault/Attachments/snapshots/<source-id>-snapshot.md:
a local, uncommitted copy that keeps web content re-checkable after it changes.

Order of attempts:
  arXiv     -> PDF + pdftotext (full text), else the abstract page
  video     -> YouTube/Vimeo/... URLs: captions via yt-dlp (if installed), with
               [hh:mm:ss] markers for citation; else the page itself
  URL       -> `defuddle parse --md` if installed, else HTTP GET;
               PDFs go through pdftotext, HTML is reduced to Markdown-ish text
  local     -> pdftotext for PDFs, HTML reduction, or plain read

Downloaded content is treated as data only: it is converted to text, never run.
Standard library only; pdftotext (poppler-utils) is needed for PDFs.
"""
# Created by: Alex Myasnikov
# Date: November 19, 2026

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "sources"
VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "podcasts.apple.com",
               "soundcloud.com", "ted.com", "twitch.tv")
TRANSCRIPT_GAP = 30  # seconds between [hh:mm:ss] markers
USER_AGENT = "researcher-template/0.1 (source fetcher)"
TIMEOUT = 60
MAX_BYTES = 60 * 1024 * 1024

ARXIV_RE = re.compile(
    r"^(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$", re.I
)
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+?)(?:\.pdf)?/?(?:[?#].*)?$", re.I)


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------------------- HTML -> text


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "form", "button", "iframe"}
    BLOCK = {"p", "div", "section", "article", "main", "header", "tr", "table",
             "blockquote", "figure", "figcaption", "ul", "ol", "dl", "dd", "dt", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif self.skip_depth:
            return
        elif re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "br":
            self.out.append("\n")
        elif tag in self.BLOCK:
            self.out.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif not self.skip_depth and (tag in self.BLOCK or re.fullmatch(r"h[1-6]", tag)):
            self.out.append("\n\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip_depth:
            self.out.append(data)


def html_to_text(raw: str) -> tuple[str, str]:
    p = _TextExtractor()
    p.feed(raw)
    text = "".join(p.out)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return html.unescape(p.title).strip(), text.strip()


# --------------------------------------------------------------------------- helpers


def http_get(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read(MAX_BYTES + 1)
            ctype = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"could not fetch {url}: {e}") from e
    if len(data) > MAX_BYTES:
        raise FetchError(f"{url} is larger than {MAX_BYTES // 2**20} MB")
    return data, ctype


def pdf_to_text(pdf: Path) -> str:
    if not shutil.which("pdftotext"):
        raise FetchError("pdftotext not found: install poppler-utils, or read the PDF another way")
    res = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
                         capture_output=True, text=True, timeout=TIMEOUT)
    if res.returncode != 0:
        raise FetchError(f"pdftotext failed: {res.stderr.strip()}")
    text = res.stdout.strip()
    if len(text) < 200:
        raise FetchError("PDF yielded almost no text (image-only/scanned?); OCR is needed")
    return text


def pdf_bytes_to_text(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "source.pdf"
        pdf.write_bytes(data)
        return pdf_to_text(pdf)


def slugify(text: str, limit: int = 80) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "source"


def arxiv_id(source: str) -> str | None:
    m = ARXIV_RE.match(source.strip())
    if m:
        return m.group(1)
    m = ARXIV_URL_RE.search(source.strip())
    return m.group(1) if m else None


def first_line_title(text: str) -> str:
    """First Markdown heading, if any. PDFs have no reliable title line; use
    lookup_metadata.py for bibliographic titles."""
    m = re.search(r"^#{1,2} +(.+)$", text, re.M)
    return m.group(1).strip()[:200] if m else ""


# --------------------------------------------------------------------------- fetchers


def fetch_arxiv(aid: str) -> dict:
    try:
        data, _ = http_get(f"https://arxiv.org/pdf/{aid}")
        text = pdf_bytes_to_text(data)
        return {"method": "arxiv-pdf", "text": text, "title": first_line_title(text), "pdf": data}
    except FetchError as pdf_err:
        raw, _ = http_get(f"https://arxiv.org/abs/{aid}")
        title, text = html_to_text(raw.decode("utf-8", errors="replace"))
        note = f"[full text unavailable: {pdf_err}; abstract page only]\n\n"
        return {"method": "arxiv-abs", "text": note + text, "title": title}


def fetch_url(url: str) -> dict:
    looks_pdf = urllib.parse.urlparse(url).path.lower().endswith(".pdf")
    if shutil.which("defuddle") and not looks_pdf:
        res = subprocess.run(["defuddle", "parse", url, "--md"],
                             capture_output=True, text=True, timeout=TIMEOUT)
        if res.returncode == 0 and len(res.stdout.strip()) > 200:
            return {"method": "defuddle", "text": res.stdout.strip(),
                    "title": first_line_title(res.stdout)}
    data, ctype = http_get(url)
    if "pdf" in ctype.lower() or data[:5] == b"%PDF-":
        text = pdf_bytes_to_text(data)
        return {"method": "http-pdf", "text": text, "title": first_line_title(text), "pdf": data}
    charset = re.search(r"charset=([\w-]+)", ctype)
    raw = data.decode(charset.group(1) if charset else "utf-8", errors="replace")
    if "html" in ctype.lower() or raw.lstrip()[:1] == "<":
        title, text = html_to_text(raw)
        return {"method": "http-html", "text": text, "title": title}
    return {"method": "http-text", "text": raw.strip(), "title": first_line_title(raw)}


def fetch_local(path: Path) -> dict:
    if not path.is_file():
        raise FetchError(f"no such file: {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = pdf_to_text(path)
        return {"method": "local-pdf", "text": text, "title": first_line_title(text),
                "pdf": path.read_bytes()}
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        title, text = html_to_text(raw)
        return {"method": "local-html", "text": text, "title": title}
    return {"method": "local-text", "text": raw.strip(), "title": first_line_title(raw)}


def _vtt_seconds(stamp: str) -> int:
    parts = stamp.split(".")[0].split(":")
    secs = 0
    for part in parts:
        secs = secs * 60 + int(part)
    return secs


def vtt_to_text(vtt: str) -> str:
    """WebVTT captions -> paragraphs prefixed with [hh:mm:ss]. Drops styling tags
    and the line repetition typical of auto-generated captions."""
    lines: list[tuple[int, str]] = []
    start, last = 0, ""
    for raw in vtt.splitlines():
        raw = raw.strip()
        if "-->" in raw:
            start = _vtt_seconds(raw.split("-->")[0].strip())
            continue
        if not raw or raw.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or raw.isdigit():
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        if text and text != last:
            lines.append((start, text))
            last = text
    paras, current, mark = [], [], None
    for sec, text in lines:
        if mark is None or sec - mark >= TRANSCRIPT_GAP:
            if current:
                paras.append(current)
            current, mark = [], sec
            h, m, s_ = sec // 3600, sec % 3600 // 60, sec % 60
            current.append(f"[{h:02d}:{m:02d}:{s_:02d}]")
        current.append(text)
    if current:
        paras.append(current)
    return "\n\n".join(" ".join(p) for p in paras)


def fetch_transcript(url: str) -> dict | None:
    """Captions via yt-dlp; None when yt-dlp is missing or finds no captions."""
    if not shutil.which("yt-dlp"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        res = subprocess.run(
            ["yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
             "--sub-langs", "en.*,en", "--sub-format", "vtt", "--no-playlist",
             "--print-to-file", "%(title)s", str(Path(tmp) / "title.txt"),
             "-o", str(Path(tmp) / "media.%(ext)s"), url],
            capture_output=True, text=True, timeout=TIMEOUT * 3)
        subs = sorted(Path(tmp).glob("*.vtt"))
        if res.returncode != 0 or not subs:
            return None
        title_file = Path(tmp) / "title.txt"
        title = title_file.read_text(encoding="utf-8").strip() if title_file.exists() else ""
        text = vtt_to_text(subs[0].read_text(encoding="utf-8", errors="replace"))
    return {"method": "yt-dlp-captions", "text": text, "title": title}


def fetch(source: str) -> tuple[dict, str]:
    """Return (result, slug)."""
    aid = arxiv_id(source)
    if aid:
        return fetch_arxiv(aid), "arxiv-" + slugify(aid)
    if re.match(r"^https?://", source, re.I):
        parsed = urllib.parse.urlparse(source)
        slug = slugify(parsed.netloc.removeprefix("www.") + parsed.path + parsed.query)
        if parsed.netloc.removeprefix("www.").removeprefix("m.").endswith(VIDEO_HOSTS):
            result = fetch_transcript(source)
            if result:
                return result, slug
        return fetch_url(source), slug
    path = Path(source).expanduser()
    return fetch_local(path), slugify(path.stem)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="URL, arXiv id, or local file")
    ap.add_argument("--out", help="output file (default: .cache/sources/<slug>.md)")
    ap.add_argument("--stdout", action="store_true", help="print the text instead of saving it")
    ap.add_argument("--name", metavar="SOURCE_ID",
                    help="name outputs after the note: text to .cache/sources/<SOURCE_ID>.md and, "
                         "for PDF sources, the PDF to vault/Attachments/papers/<SOURCE_ID>.pdf "
                         "(local, uncommitted)")
    ap.add_argument("--snapshot", metavar="SOURCE_ID",
                    help="save to vault/Attachments/snapshots/<SOURCE_ID>-snapshot.md (local, uncommitted)")
    args = ap.parse_args(argv)

    # Validate ids before fetching, so a typo doesn't cost a download.
    for flag in ("name", "snapshot"):
        val = getattr(args, flag)
        if val and not re.fullmatch(r"[a-z0-9][a-z0-9.\-]*", val):
            print(json.dumps({"error": f"--{flag} needs a kebab-case source id"}), file=sys.stderr)
            return 2

    try:
        result, slug = fetch(args.source)
    except FetchError as e:
        print(json.dumps({"source": args.source, "error": str(e)}), file=sys.stderr)
        return 1

    text = result["text"]
    vault = Path(os.environ.get("RESEARCH_VAULT") or REPO_ROOT / "vault").expanduser()
    pdf_path = None
    if args.name and result.get("pdf"):
        pdf_path = vault / "Attachments" / "papers" / f"{args.name}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(result["pdf"])
    if args.stdout:
        print(text)
        return 0
    if args.snapshot:
        out = vault / "Attachments" / "snapshots" / f"{args.snapshot}-snapshot.md"
    else:
        out = Path(args.out) if args.out else CACHE_DIR / f"{args.name or slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    header = (f"<!-- source: {args.source} | method: {result['method']} | "
              f"fetched: {dt.date.today().isoformat()} -->\n\n")
    out.write_text(header + text + "\n", encoding="utf-8")
    print(json.dumps({"source": args.source, "method": result["method"], "path": str(out),
                      "chars": len(text), "lines": text.count("\n") + 1,
                      "title": result["title"],
                      **({"pdf": str(pdf_path)} if pdf_path else {})}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
