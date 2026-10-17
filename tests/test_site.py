"""Public KAELIX Studio site release smoke checks."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
LANDING = REPO / "docs/index.html"
STUDIO = REPO / "docs/services.html"
REQUEST = REPO / ".github/ISSUE_TEMPLATE/service-request.yml"


class TagAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []
        self.handlers = []
        self.inputs = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])
        for key in values:
            if key.startswith("on"):
                self.handlers.append((tag, key))
        if tag == "script":
            self.inputs.append(values.get("src"))


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.studio = STUDIO.read_text(encoding="utf8")
        self.landing = LANDING.read_text(encoding="utf8")
        self.request = REQUEST.read_text(encoding="utf8")
        self.audit = TagAudit()
        self.audit.feed(self.studio)

    def test_studio_exists_and_has_english_metadata(self):
        self.assertIn('<html lang="en">', self.studio)
        self.assertIn("KAELIX Studio", self.studio)
        self.assertIn('name="description"', self.studio)

    def test_studio_crosslinked_from_solana_home(self):
        self.assertIn('href="services.html"', self.landing)
        self.assertIn('href="index.html"', self.studio)

    def test_all_local_anchors_resolve(self):
        ids = set(self.audit.ids)
        for href in self.audit.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], ids)

    def test_no_duplicate_ids(self):
        self.assertEqual(len(self.audit.ids), len(set(self.audit.ids)))

    def test_no_runtime_remote_scripts_or_inline_handlers(self):
        self.assertFalse([src for src in self.audit.inputs if src])
        self.assertEqual(self.audit.handlers, [])

    def test_checkout_is_free_inquiry_and_not_fake_sales(self):
        self.assertIn("No payment before scope agreement", self.studio)
        self.assertIn("not automatic offers to contract", self.studio)
        self.assertIn("free quote", self.request.lower())

    def test_quote_links_are_real_issue_template_paths(self):
        self.assertIn("service-request.yml", self.studio)
        self.assertTrue(REQUEST.is_file())
        self.assertIn("https://github.com/MaxGab/kaelix-solana-sentinel/issues/new?template=service-request.yml", self.studio)

    def test_mobile_reflow(self):
        self.assertIn("name=\"viewport\"", self.studio)
        self.assertIn("@media(max-width:660px)", self.studio)

    def test_privacy_and_no_secrets(self):
        self.assertIn("No upload", self.studio)
        self.assertIn("No external dependencies or tracking scripts", self.studio)
        self.assertIn("Never include credentials", self.request)

    def test_local_demo_js_syntax(self):
        parts = re.findall(r"<script([^>]*)>(.*?)</script>", self.studio, re.S)
        raw = [body for props, body in parts if "application/ld+json" not in props]
        self.assertEqual(len(raw), 1)
        with tempfile.TemporaryDirectory() as td:
            fn = Path(td) / "script.js"
            fn.write_text(raw[0])
            result = subprocess.run(["node", "--check", str(fn)], capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_jsonld_is_valid(self):
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', self.studio, re.S)
        self.assertEqual(len(scripts), 1)
        record = json.loads(scripts[0])
        self.assertEqual(record["@type"], "WebPage")
        self.assertTrue(record["url"].startswith("https://maxgab.github.io/"))

    def test_public_code_starter_exists(self):
        demo = REPO / "examples/kaelix-data-audit/csv_audit.py"
        self.assertTrue(demo.exists())
        self.assertIn("No data uploaded", demo.read_text())

    def test_social_sales_entry_is_visible_without_github(self):
        self.assertIn('href="#quote"', self.studio)
        self.assertIn('id="quote-heading"', self.studio)
        self.assertIn('https://ig.me/m/kaelix_hq', self.studio)
        self.assertIn('Instagram @kaelix_hq', self.studio)

    def test_local_quote_builder_does_not_submit_details_to_servers(self):
        self.assertIn('id="quote-preview"', self.studio)
        self.assertIn('id="quote-generate"', self.studio)
        self.assertIn('id="quote-copy"', self.studio)
        self.assertIn('navigator.clipboard.writeText', self.studio)
        self.assertNotIn('fetch(', self.studio)
        self.assertNotIn('new XMLHttpRequest', self.studio)
        self.assertNotIn('<form action=', self.studio)

    def test_quote_builder_requires_meaningful_problem(self):
        self.assertIn('description.length < 20', self.studio)
        self.assertIn('description.length > 1000', self.studio)
        self.assertIn('confirm scope, tests, delivery window and pricing', self.studio)

    def test_low_friction_quote_keeps_github_for_engineers(self):
        self.assertIn('service-request.yml', self.studio)
        self.assertIn('Prefer GitHub?', self.studio)
        self.assertIn('No GitHub account required for Instagram messages', self.studio)

    def test_prices_are_indicative(self):
        self.assertIn("From €59", self.studio)
        self.assertIn("From €39", self.studio)
        self.assertIn("300 RON", self.studio)
        self.assertIn("indicative starting prices", self.studio)

if __name__ == "__main__":
    unittest.main(verbosity=2)
