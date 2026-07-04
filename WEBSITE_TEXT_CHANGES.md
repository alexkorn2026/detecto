# Website text corrections (red-database-security.com/detecto)

Apply these replacements to the product page. They remove technically
indefensible absolute claims and align the copy with the v2.0.0 behaviour.
Each block is an exact old → new replacement.

---

## Finding 3 / 42 — Plaintext credentials claim

**Remove:**
> Credentials never appear in plain text.

**Replace with:**
> Detecto anonymizes sensitive findings by default. Explicit options
> (`--show-sensitive-values`) are required to include unredacted values in
> reports, and sensitive report files are written with restrictive permissions
> where the platform supports it.

Document additionally: which outputs are anonymized, which options allow
plaintext, and the risks of plaintext exports.

---

## Finding 42 — Absolute security promises

**Remove:**
> Every input is validated.
> Every output is sanitized.
> Every resource is bounded.

**Replace with:**
> Detecto validates configuration values, restricts pattern-file locations,
> limits selected resources (regex runtime, line and result sizes, worker
> count) and protects spreadsheet exports against common formula-injection
> patterns.

Document the limits: heuristic detection, possible false positives/negatives,
no guarantee of complete PII detection, custom regex may still be problematic
despite runtime timeouts, plaintext output only on explicit opt-in, incomplete
scans are flagged, and the list of supported encodings/file formats.

---

## Finding 41 — Symlink safety claim

**Remove:**
> No symlink attacks.

**Replace with:**
> Pattern-file paths are resolved and restricted to trusted directories and are
> opened without following symlinks (O_NOFOLLOW) to reduce path-traversal and
> symlink-related risks. This mitigates but does not eliminate all filesystem
> race conditions.

---

## Finding 26 — Encoding claims

**Remove:**
> Automatic encoding detection. No data corruption.

**Replace with:**
> Configurable encoding handling (`--encoding auto|utf-8|windows-1252|...`,
> `--encoding-errors strict|replace|ignore`). In `auto` mode Detecto uses
> deterministic rules (BOM detection, UTF-8 validation, documented fallback).
> Decoding errors and replaced characters are counted and reported; in strict
> mode a decoding error marks the scan partial rather than silently replacing
> characters.

---

## Finding 33 — Test count as quality proof

**Remove:**
> 126 tests passing.

**Replace with:**
> Extensive automated test suite (unit, integration, CLI, packaging,
> concurrency, fuzz/property and security-regression tests). Detection quality
> is measured separately via a reproducible precision/recall/F1 benchmark on a
> synthetic gold dataset — the number of passing tests is not a measure of
> detection quality.

---

## Finding 36 — Worksheet count

**Remove:**
> The Excel report contains 6 worksheets.

**Replace with:**
> The Excel report contains 5 standard worksheets (Findings, Tool, Regexp,
> Field, String) plus an optional `Full` worksheet when `--full` is enabled.

---

## Finding 10 / 15 — JSON and email wording

- Distinguish generic text search from structured JSON parsing: "Detecto
  performs generic text/token matching and, for JSON-looking lines, optional
  structured JSON parsing (`parse_json = auto|true|false`)."
- Email: "Detecto detects typical email-address candidates in logs. It does not
  guarantee full RFC compliance; internationalized addresses may be recognized
  only partially depending on their representation." Avoid absolute phrasing
  such as "all email addresses".
