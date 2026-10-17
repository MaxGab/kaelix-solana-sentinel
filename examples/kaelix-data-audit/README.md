# KAELIX Data Audit — free local CSV quality checker

This is a **real, testable starter tool** that evaluates local CSV data quality without sending file contents to a server. Python 3.10+, standard library only.

## Use it

```bash
python3 csv_audit.py sample.csv --required id,email --email-columns email --json
python3 -m unittest -v test_csv_audit.py
```

It reports column consistency, empty fields, duplicate rows (ignoring surrounding whitespace), values requiring trimming, missing required columns, and malformed nonempty emails. Output includes counts and schema names, **never actual customer row values**. It validates up to 5 MB, 50,000 data rows, and 250 columns per file.

**Limits:** This is a lightweight data quality snapshot, not a comprehensive PII detector, sanitization guarantee, secure parsing environment for hostile files, deduplication/export product, warehouse integration, or email deliverability service. It checks only basic email syntax. It does not automatically repair records.

**Custom services:** KAELIX can build a scoped version adapted to your CSV/JSON exports, e-commerce inventory feed, reporting pipeline, file format, or validation contract; request a fixed quotation at [KAELIX Services](https://maxgab.github.io/kaelix-solana-sentinel/services.html). Provide a **synthetic sample** first — never place customer data, API tokens or secrets in a public GitHub issue.

No money is processed by this script. Service quotes are not sales until a client explicitly agrees to the scope, price and payment terms.
