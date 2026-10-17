#!/usr/bin/env python3
"""KAELIX Data Audit — local CSV quality report; no uploads or third-party APIs.

Starter demonstration for a custom data QA / automation service.
Python 3.10+ standard library only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys

MAX_INPUT_BYTES = 5_000_000
MAX_ROWS = 50_000
MAX_COLUMNS = 250
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def inspect_csv(path: Path, *, required: tuple[str, ...] = (),
                email_columns: tuple[str, ...] = ()) -> dict:
    """Return counts and schema checks; never include raw customer row values."""
    if not path.is_file() or path.is_symlink():
        raise ValueError("Input must be a regular CSV file, not a symlink")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds 5 MB limit")
    if not path.stat().st_size:
        raise ValueError("Input is empty")
    with path.open(newline="", encoding="utf-8-sig", errors="strict") as stream:
        reader = csv.reader(stream, strict=True)
        try:
            raw_headers = next(reader)
        except StopIteration as exc:
            raise ValueError("Input has no header row") from exc
        except csv.Error as exc:
            raise ValueError("Malformed CSV header") from exc
        if not raw_headers or len(raw_headers) > MAX_COLUMNS:
            raise ValueError("Input must have 1 to 250 columns")
        headers = [head.strip() for head in raw_headers]
        if not all(headers):
            raise ValueError("Headers cannot be blank")
        header_duplicates = [key for key, count in Counter(headers).items() if count > 1]
        if header_duplicates:
            raise ValueError("Duplicate headers after trimming: " + ", ".join(header_duplicates)[:120])
        expected = set(required)
        missing_cols = sorted(expected - set(headers))
        missing_email_cols = sorted(set(email_columns) - set(headers))
        empty_by_col = Counter({c: 0 for c in headers})
        bad_emails_by_col = Counter({c: 0 for c in email_columns if c in headers})
        trim_needed_by_col = Counter({c: 0 for c in headers})
        mismatched_width = 0
        duplicate_rows = 0
        rows_seen = 0
        fingerprints = set()
        for raw in reader:
            rows_seen += 1
            if rows_seen > MAX_ROWS:
                raise ValueError("Input exceeds 50,000-row limit")
            if len(raw) != len(headers):
                mismatched_width += 1
                continue
            row = tuple(value.strip() for value in raw)
            for idx, col in enumerate(headers):
                if raw[idx] != row[idx]:
                    trim_needed_by_col[col] += 1
                if row[idx] == "":
                    empty_by_col[col] += 1
                if col in bad_emails_by_col and row[idx] and not EMAIL_RE.match(row[idx]):
                    bad_emails_by_col[col] += 1
            if row in fingerprints:
                duplicate_rows += 1
            else:
                fingerprints.add(row)
    issues = (mismatched_width + duplicate_rows +
              sum(empty_by_col.values()) + sum(bad_emails_by_col.values()) +
              len(missing_cols) + len(missing_email_cols))
    return {
        "tool": "KAELIX Data Audit starter",
        "input_file_name": path.name,
        "rows": rows_seen,
        "columns": len(headers),
        "headers": headers,
        "schema": {"missing_required": missing_cols, "missing_email_columns": missing_email_cols},
        "quality": {
            "malformed_width_rows": mismatched_width,
            "duplicate_rows": duplicate_rows,
            "empty_cells_by_column": dict(empty_by_col),
            "cells_requiring_whitespace_trim_by_column": dict(trim_needed_by_col),
            "invalid_nonempty_emails_by_column": dict(bad_emails_by_col),
        },
        "issues_detected": issues,
        "raw_row_data_included": False,
        "data_sent_to_remote_service": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Privacy-first local CSV quality audit")
    parser.add_argument("csv_file", type=Path, help="Path to local CSV (5 MB / 50k rows max)")
    parser.add_argument("--required", default="", help="Required columns, comma-separated")
    parser.add_argument("--email-columns", default="", help="Email field names, comma-separated")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    args = parser.parse_args(argv)
    split = lambda value: tuple(x.strip() for x in value.split(",") if x.strip())
    try:
        report = inspect_csv(args.csv_file, required=split(args.required),
                             email_columns=split(args.email_columns))
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print("CSV audit failed: " + str(exc)[:220], file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"KAELIX Data Audit — {report['rows']} rows × {report['columns']} columns")
        print(f"Quality issues detected: {report['issues_detected']}")
        print(json.dumps(report['quality'], indent=2, ensure_ascii=False))
        print("No data uploaded or transmitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
