"""Offline tests for scripts/: frontmatter parsing, vault checks, id detection.

Run: python3 -m unittest discover -s tests
"""
# Created by: Alex Myasnikov
# Date: November 19, 2026

import contextlib
import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_source  # noqa: E402
import lookup_metadata  # noqa: E402
import vault_tool  # noqa: E402

TAGS_MD = """\
# Tag registry
## Domains
<!-- Format: - `domain/<value>`: scope -->
- `domain/machine-learning`: ML (registered 2026-11-19)
## Topics
- `topic/attention`: attention mechanisms
- #domain/biology-plain: registered without backticks
"""


def source_note(title, links_fm="", body_links="", domain="machine-learning", extra=""):
    return textwrap.dedent(f"""\
        ---
        title: {title}
        type: paper
        url: https://example.org/{title}
        domain: {domain}
        status: draft
        author: tester
        {extra}
        tags:
          - agent/research
          - type/paper
          - domain/{domain}
          - topic/attention
          - status/draft
        """) + links_fm + "---\n\n# " + title + "\n\n## Related material\n\n" + body_links + "\n"


class VaultFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "_meta").mkdir()
        (self.root / "_meta" / "tags.md").write_text(TAGS_MD)
        for d in ("Sources/Machine learning", "Concepts", "Syntheses"):
            (self.root / d).mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def run_cmd(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vault_tool.main(["--vault", str(self.root), *argv])
        return code, buf.getvalue()


class FrontmatterTests(unittest.TestCase):
    def test_block_and_flow_lists_and_comments(self):
        text = textwrap.dedent("""\
            ---
            title: "A: title"   # trailing comment
            url: https://x.org/a#frag
            aliases: [one, "two, three"]
            cites:
              - "[[smith-2020]]"
              - "[[doe-2021|Doe]]"
            empty: []
            ---
            body
            """)
        props, _, body = vault_tool.parse_frontmatter(text)
        self.assertEqual(props["title"], "A: title")
        self.assertEqual(props["url"], "https://x.org/a#frag")
        self.assertEqual(props["aliases"], ["one", "two, three"])
        self.assertEqual(props["empty"], [])
        self.assertEqual(vault_tool.links_in(props["cites"]), ["smith-2020", "doe-2021"])
        self.assertEqual(body.strip(), "body")

    def test_no_frontmatter(self):
        self.assertIsNone(vault_tool.parse_frontmatter("# just text\n")[0])

    def test_code_is_ignored_for_links(self):
        body = "see `[[<placeholder>]]` and\n```\n[[in-fence]]\n```\n[[real]]"
        found = vault_tool.WIKILINK_RE.findall(vault_tool.strip_code(body))
        self.assertEqual(found, ["real"])


class LintTests(VaultFixture):
    def make_linked_pair(self):
        self.write("Concepts/self-attention.md", textwrap.dedent("""\
            ---
            title: self-attention
            type: concept
            domain: machine-learning
            status: draft
            author: tester
            appears_in:
              - "[[smith-2020]]"
              - "[[doe-2021]]"
            tags: [agent/research, type/concept, domain/machine-learning, topic/attention, status/draft]
            ---
            [[smith-2020]] [[doe-2021]] [[tags]]
            """))
        self.write("Sources/Machine learning/smith-2020.md", source_note(
            "smith-2020",
            links_fm='key_concepts:\n  - "[[self-attention]]"\ncited_by:\n  - "[[doe-2021]]"\n',
            body_links="- [[self-attention]]\n- [[doe-2021]]\n- [[tags]]"))
        self.write("Sources/Machine learning/doe-2021.md", source_note(
            "doe-2021",
            links_fm='key_concepts:\n  - "[[self-attention]]"\ncites:\n  - "[[smith-2020]]"\n',
            body_links="- [[self-attention]]\n- [[smith-2020]]\n- [[tags]]"))

    def test_clean_vault_passes(self):
        self.make_linked_pair()
        code, out = self.run_cmd("lint")
        self.assertEqual(code, 0, out)
        self.assertIn("0 errors", out)
        code, out = self.run_cmd("links")
        self.assertEqual(code, 0, out)

    def test_errors_detected(self):
        self.make_linked_pair()
        self.write("Sources/Machine learning/summary.md", source_note(
            "summary", domain="biology",
            links_fm='cites:\n  - [[smith-2020]]\n',
            body_links="[[<placeholder>]]"))
        code, out = self.run_cmd("lint")
        self.assertEqual(code, 1)
        for c in ("E generic-name", "E unregistered-domain", "E placeholder-link",
                  "E unquoted-fm-link", "W few-links"):
            self.assertIn(c, out)

    def test_mirror_mismatch_and_unresolved(self):
        self.make_linked_pair()
        self.write("Sources/Machine learning/lee-2022.md", source_note(
            "lee-2022", extra="",
            body_links="- [[self-attention]]\n- [[smith-2020]]\n- [[tags]]\n- [[ghost-note]]"
        ).replace("status: draft", "status: review", 1))
        code, out = self.run_cmd("lint", str(self.root / "Sources/Machine learning/lee-2022.md"))
        self.assertEqual(code, 1)
        self.assertIn("mirror-mismatch", out)
        self.assertIn("unresolved-link", out)

    def test_registry_formats(self):
        v = vault_tool.Vault(self.root)
        self.assertEqual(v.registry("domain"), {"machine-learning", "biology-plain"})

    def test_duplicate_names(self):
        self.make_linked_pair()
        self.write("Syntheses/smith-2020.md", "---\ntitle: dup\n---\n")
        code, out = self.run_cmd("lint")
        self.assertIn("duplicate-name", out)

    def test_links_reports_missing_reciprocal(self):
        self.make_linked_pair()
        p = self.root / "Sources/Machine learning/smith-2020.md"
        p.write_text(p.read_text().replace('cited_by:\n  - "[[doe-2021]]"\n', ""))
        code, out = self.run_cmd("links")
        self.assertEqual(code, 1)
        self.assertIn("smith-2020.md: cited_by is missing", out)

    def test_orphans_and_find_and_tags(self):
        self.make_linked_pair()
        self.write("Sources/Machine learning/lonely-2019.md", source_note("lonely-2019"))
        code, out = self.run_cmd("orphans")
        self.assertEqual(code, 1)
        self.assertIn("lonely-2019", out)
        code, out = self.run_cmd("find", "doe")
        self.assertIn("doe-2021.md", out)
        code, out = self.run_cmd("tags", "--axis", "topic")
        self.assertIn("topic/attention", out)

    def test_human_notes_are_lenient(self):
        self.write("Notes/ideas/my-idea.md", "---\ntitle: x\nauthor: me\ntags: [agent/human]\n---\ntext")
        code, out = self.run_cmd("lint", "--errors-only")
        self.assertEqual(code, 0, out)


class IndexSearchEntityTests(VaultFixture):
    make_linked_pair = LintTests.make_linked_pair

    def add_entity(self, appears=("smith-2020",)):
        items = "".join(f'  - "[[{a}]]"\n' for a in appears)
        self.write("Entities/acme-lab.md",
                   "---\ntitle: Acme Lab\ntype: org\nstatus: draft\nauthor: tester\n"
                   f"appears_in:\n{items}"
                   "tags: [agent/research, type/org, status/draft]\n---\n\n## Summary\n\n"
                   "Research lab studying attention.\n\n[[smith-2020]] [[tags]] [[self-attention]]\n")

    def test_entity_lint_relaxed_and_reciprocity(self):
        self.make_linked_pair()
        self.add_entity()
        code, out = self.run_cmd("lint", "--errors-only")
        self.assertEqual(code, 0, out)  # no domain, no topic: fine for an entity
        code, out = self.run_cmd("links")
        self.assertEqual(code, 1)
        self.assertIn("smith-2020.md: entities is missing", out)

    def test_index_generation_and_check(self):
        self.make_linked_pair()
        p = self.root / "Sources/Machine learning/smith-2020.md"
        p.write_text(p.read_text().replace("## Related material",
                     "## TL;DR\n\n<placeholder>\n\nAttention replaces recurrence.\n\n## Related material"))
        self.assertEqual(self.run_cmd("index", "--check")[0], 1)
        code, out = self.run_cmd("index")
        self.assertEqual(code, 0, out)
        text = (self.root / "index.md").read_text()
        self.assertIn("## Concepts", text)
        self.assertIn("### machine-learning", text)
        self.assertIn("- [[smith-2020]] (paper): Attention replaces recurrence.", text)
        self.assertEqual(self.run_cmd("index", "--check")[0], 0)
        # the index links to everything but must not rescue orphans
        self.write("Sources/Machine learning/lonely-2019.md", source_note("lonely-2019"))
        self.run_cmd("index")
        code, out = self.run_cmd("orphans")
        self.assertIn("lonely-2019", out)

    def test_search_ranks_title_and_body(self):
        self.make_linked_pair()
        p = self.root / "Sources/Machine learning/doe-2021.md"
        p.write_text(p.read_text() + "\nWe study sparse transformers and sparse kernels.\n")
        code, out = self.run_cmd("search", "sparse", "kernels")
        self.assertEqual(code, 0)
        first = out.splitlines()[0]
        self.assertIn("doe-2021.md", first)
        self.assertIn("sparse transformers", out)
        self.assertIn("No matches.", self.run_cmd("search", "zzzunknown")[1])


class IdTests(unittest.TestCase):
    def test_fetch_arxiv_ids(self):
        self.assertEqual(fetch_source.arxiv_id("2410.12345"), "2410.12345")
        self.assertEqual(fetch_source.arxiv_id("arXiv:2410.12345v2"), "2410.12345v2")
        self.assertEqual(fetch_source.arxiv_id("https://arxiv.org/abs/2410.12345"), "2410.12345")
        self.assertEqual(fetch_source.arxiv_id("https://arxiv.org/pdf/2410.12345v1.pdf"), "2410.12345v1")
        self.assertIsNone(fetch_source.arxiv_id("https://example.org/page"))

    def test_lookup_classify(self):
        self.assertEqual(lookup_metadata.classify("2410.12345v3"), ("arxiv", "2410.12345"))
        self.assertEqual(lookup_metadata.classify("https://doi.org/10.1145/123.456"),
                         ("doi", "10.1145/123.456"))
        self.assertEqual(lookup_metadata.classify("https://example.org/x")[0], "url")
        self.assertEqual(lookup_metadata.classify("Some paper title")[0], "title")

    def test_vtt_to_text(self):
        vtt = ("WEBVTT\nKind: captions\n\n00:00:01.000 --> 00:00:03.000\nhello <c>world</c>\n\n"
               "00:00:02.000 --> 00:00:04.000\nhello world\n\n00:00:40.500 --> 00:00:42.000\n"
               "second part\n")
        self.assertEqual(fetch_source.vtt_to_text(vtt),
                         "[00:00:01] hello world\n\n[00:00:40] second part")

    def test_html_to_text(self):
        title, text = fetch_source.html_to_text(
            "<html><head><title>T</title><script>x()</script></head>"
            "<body><h2>Head</h2><p>Para &amp; more</p><ul><li>a</li></ul></body></html>")
        self.assertEqual(title, "T")
        self.assertIn("## Head", text)
        self.assertIn("Para & more", text)
        self.assertIn("- a", text)
        self.assertNotIn("x()", text)


if __name__ == "__main__":
    unittest.main()
