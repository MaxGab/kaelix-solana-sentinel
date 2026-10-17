"""Contract tests for the public KAELIX Data Audit starter."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from csv_audit import inspect_csv, main


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.source = Path(self.folder.name) / "input.csv"

    def write(self, text):
        self.source.write_text(text, encoding="utf-8")

    def test_clean_csv(self):
        self.write("id,email\n1,alice@example.com\n2,bob@example.org\n")
        res = inspect_csv(self.source, required=("id",), email_columns=("email",))
        self.assertEqual(res["issues_detected"], 0)
        self.assertEqual(res["rows"], 2)
        self.assertEqual(res["columns"], 2)

    def test_missing_columns(self):
        self.write("name\nJane\n")
        res = inspect_csv(self.source, required=("id", "name"), email_columns=("email",))
        self.assertEqual(res["schema"]["missing_required"], ["id"])
        self.assertEqual(res["schema"]["missing_email_columns"], ["email"])

    def test_duplicate_rows_after_trim(self):
        self.write("id,status\n1, active\n 1,active\n")
        res = inspect_csv(self.source)
        self.assertEqual(res["quality"]["duplicate_rows"], 1)

    def test_empty_cells(self):
        self.write("a,b\n,ok\n1,\n")
        res = inspect_csv(self.source)
        self.assertEqual(res["quality"]["empty_cells_by_column"], {"a": 1, "b": 1})

    def test_invalid_email(self):
        self.write("email\nwrong_at_example\nvalid@example.org\n\n")
        res = inspect_csv(self.source, email_columns=("email",))
        self.assertEqual(res["quality"]["invalid_nonempty_emails_by_column"]["email"], 1)

    def test_wrong_row_width(self):
        self.write("a,b\n1,2\n3\n")
        self.assertEqual(inspect_csv(self.source)["quality"]["malformed_width_rows"], 1)

    def test_bom(self):
        self.source.write_bytes(b"\xef\xbb\xbfa,b\n1,2\n")
        self.assertEqual(inspect_csv(self.source)["headers"], ["a", "b"])

    def test_duplicate_headers_rejected(self):
        self.write("id, id\n1,2\n")
        with self.assertRaisesRegex(ValueError, "Duplicate headers"):
            inspect_csv(self.source)

    def test_empty_header_rejected(self):
        self.write("id,\n1,2\n")
        with self.assertRaisesRegex(ValueError, "blank"):
            inspect_csv(self.source)

    def test_header_only(self):
        self.write("a,b\n")
        self.assertEqual(inspect_csv(self.source)["rows"], 0)

    def test_empty_file(self):
        self.write("")
        with self.assertRaisesRegex(ValueError, "empty"):
            inspect_csv(self.source)

    def test_symlink_refused(self):
        self.write("a\n1\n")
        link = Path(self.folder.name) / "linked.csv"
        link.symlink_to(self.source)
        with self.assertRaises(ValueError):
            inspect_csv(link)

    def test_big_file_refused(self):
        with self.source.open("wb") as f:
            f.truncate(5_000_001)
        with self.assertRaisesRegex(ValueError, "5 MB"):
            inspect_csv(self.source)

    def test_json_cli_does_not_echo_rows(self):
        self.write("name\nPERSONAL-EXAMPLE-DO-NOT-PRINT\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(self.source), "--json"])
        self.assertEqual(code, 0)
        self.assertNotIn("PERSONAL-EXAMPLE-DO-NOT-PRINT", output.getvalue())
        self.assertIn('"raw_row_data_included": false', output.getvalue())

    def test_bad_unicode_handled(self):
        self.source.write_bytes(b"a\n\xff\n")
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = main([str(self.source)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
