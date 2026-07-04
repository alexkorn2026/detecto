"""Log analysis: LogAnalyzer class with multiprocessing support."""
from __future__ import annotations

import logging
import multiprocessing
import os
import re
import sys
import time
from collections import OrderedDict
from typing import Iterator

import detecto.constants as _const
from detecto.constants import (
    MIN_LEN_REGEXP, MIN_LEN_FIELD,
    STRIP_CHARS, PREFILTER_MARKERS, CHUNK_THRESHOLD_BYTES,
    REGEX_TIMEOUT_MS, REGEX_DISABLE_THRESHOLD,
)
from detecto.diagnostics import ScanDiagnostics
from detecto.loaders import RegexpPattern, FieldPattern, SearchPattern
from detecto.regexsafe import RegexTimeout, safe_finditer, safe_search
from detecto.tokenizer import (
    tokenize, find_field_value, split_inline_field, _TOKEN_RE,
)
from detecto.utils import normalize, normalize_with_offsets

__all__ = ["LogAnalyzer"]

log = logging.getLogger(__name__)

# Pre-filter: lines with >=5 consecutive digits may contain numeric PII
# (VSNR, KVNR, Steuer-ID, IBAN, Telefon, PLZ, ...) and must pass the filter.
_DIGIT_RUN_RE = re.compile(r"\d{5}")

# Finding 5: only *unambiguous* filesystem paths should suppress a credential
# value. A password like '/MySecret2026!' or 'C:verySecret' must NOT be
# discarded just because of a leading slash or 'X:' prefix.
_WIN_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
# Finding 5: masked credential values are a *distinct*, lower-severity finding,
# never a plaintext-secret finding. Matches ****, xxxxx, <redacted>, [MASKED].
_MASK_RE = re.compile(
    r"^(?:"
    r"\*{2,}"                                  # ****
    r"|x{3,}"                                  # xxxxx / XXXXX
    r"|[<\[]\s*(?:redacted|masked|hidden|removed|sanitized|filtered|secret|xxxx+)\s*[>\]]"
    r"|(?:redacted|masked|hidden|removed|sanitized|filtered)"  # bare keyword (brackets stripped)
    r")$",
    re.IGNORECASE,
)


def _looks_like_path(value: str) -> bool:
    """True only for values that are clearly filesystem paths (Finding 5)."""
    if value.startswith(("/", "~/")) and "/" in value[1:]:
        return True  # /var/log/app.log, ~/foo/bar
    if value.startswith("\\\\"):
        return True  # UNC \\server\share
    return bool(_WIN_PATH_RE.match(value))  # C:\temp, D:/data


def _is_masked_value(value: str) -> bool:
    """True if a value is an obvious mask/redaction placeholder (Finding 5)."""
    return bool(_MASK_RE.match(value.strip()))

# Uncached normalize for whole lines (the LRU cache is sized for tokens;
# unique log lines would evict useful entries).
_normalize_plain = normalize.__wrapped__


class LogAnalyzer:
    """Analyzes log files against regexp, field and string patterns.

    Supports multiprocessing for parallel analysis of multiple files
    and chunk-based parallelism for single large files.
    Uses a reverse-index dict for O(1) string matching per token.
    """

    def __init__(
        self,
        regexp: list[RegexpPattern] | None = None,
        field: list[FieldPattern] | None = None,
        search: list[SearchPattern] | None = None,
        sw_regexp: set[str] | None = None,
        sw_field: set[str] | None = None,
        sw_search: set[str] | None = None,
        parse_json: bool = True,
        prefilter: str = "off",
        max_examples: int = 100,
        regex_timeout_ms: int = REGEX_TIMEOUT_MS,
        regex_disable_threshold: int = REGEX_DISABLE_THRESHOLD,
        max_values_per_pattern: int = _const.MAX_VALUES_PER_PATTERN,
        max_total_findings: int = _const.MAX_TOTAL_FINDINGS,
        max_total_examples: int = _const.MAX_TOTAL_EXAMPLES,
        max_example_chars: int = _const.MAX_EXAMPLE_CHARS,
        masked_criticality: int = _const.MASKED_VALUE_CRITICALITY,
    ) -> None:
        self.regexp = regexp or []
        self.field = field or []
        self.search = search or []
        self.sw_regexp = sw_regexp or set()
        self.sw_field = sw_field or set()
        self.sw_search = sw_search or set()
        self.parse_json = parse_json
        self.prefilter = prefilter
        self.max_examples = max_examples
        # Finding 1: runtime regex protection.
        self._regex_timeout_ms = regex_timeout_ms
        self._regex_disable_threshold = regex_disable_threshold
        self._disabled: set[str] = set()
        # Finding 4: global memory / result limits + counters.
        self._max_values_per_pattern = max_values_per_pattern
        self._max_total_findings = max_total_findings
        self._max_total_examples = max_total_examples
        self._max_example_chars = max_example_chars
        self._max_examples_per_value = max_examples
        self._masked_criticality = max(1, min(5, masked_criticality))
        self._total_values = 0
        self._total_examples = 0
        self.diag = ScanDiagnostics()
        # Multi-word search values (e.g. 'Multiple Sklerose') can never
        # match a single token - they are checked against the whole
        # normalized line instead (see _analyze_line).
        self._search_phrases: dict[str, list[str]] = {}
        self._search_index: dict[str, list[str]] = self._build_search_index()
        self._prefilter_keywords = self._build_prefilter_keywords()
        # Regexps containing whitespace or '=' can never match a single
        # token (tokens are split on whitespace and '='). They run once
        # per line instead. '=' inside lookarounds ('(?=' etc.) is ignored.
        self._regexp_token: list[RegexpPattern] = []
        self._regexp_line: list[RegexpPattern] = []
        for entry in self.regexp:
            pat_src = entry[3].pattern
            stripped = (pat_src.replace("(?=", "").replace("(?!", "")
                        .replace("(?<=", "").replace("(?<!", ""))
            if ("\\s" in pat_src or " " in pat_src
                    or "\\t" in pat_src or "\t" in pat_src
                    or "=" in stripped):
                self._regexp_line.append(entry)
            else:
                self._regexp_token.append(entry)
        if self._regexp_line:
            log.info("Regexp scopes: %d token-based, %d line-based",
                     len(self._regexp_token), len(self._regexp_line))

    def _build_search_index(self) -> dict[str, list[str]]:
        """Build reverse-index dict from all search patterns for O(1) matching.

        Returns dict mapping each normalized value to a list of pattern names.
        Example: {"hamburg": ["Ort"], "mueller": ["Nachnamen"]}
        Multi-word values go into self._search_phrases (line-based check).
        """
        index: dict[str, list[str]] = {}
        total = 0
        for name, _, values in self.search:
            for val in values:
                target = self._search_phrases if " " in val else index
                if val in target:
                    target[val].append(name)
                else:
                    target[val] = [name]
                total += 1
        if index:
            log.info("Search index built: %d values -> %d entries "
                     "(+%d multi-word phrases)",
                     total, len(index), len(self._search_phrases))
        return index

    def _build_prefilter_keywords(self) -> tuple[tuple[str, ...], frozenset[str]] | None:
        """Build pre-filter data structures for fast filtering.

        Returns None if prefilter is 'off'.
        Returns (substring_markers, token_keywords):
          - substring_markers: Tuple from PREFILTER_MARKERS for substring checks
          - token_keywords: Large frozenset for O(1) token lookup (string search)
        """
        if self.prefilter == "off":
            return None

        token_kw: frozenset[str] = frozenset()
        if self.prefilter == "all":
            all_values: set[str] = set()
            for _, _, values in self.search:
                all_values.update(values)
            token_kw = frozenset(all_values)

        log.info("Pre-filter: %d markers + %d token keywords (mode=%s)",
                 len(PREFILTER_MARKERS), len(token_kw), self.prefilter)
        return PREFILTER_MARKERS, token_kw

    def _passes_prefilter(self, line: str) -> bool:
        """Check if a line should be analyzed (pre-filter).

        Uses two strategies:
        1. Substring check against ~40 field/regexp markers (fast, always)
        2. Token-split + set intersection against search keywords (O(1) per token)
        """
        if self._prefilter_keywords is None:
            return True

        # Numeric PII (VSNR, KVNR, IBAN, Telefon, PLZ, Steuer-ID, ...) has
        # no text marker - lines with a digit run always pass the filter.
        if _DIGIT_RUN_RE.search(line):
            return True

        markers, token_kw = self._prefilter_keywords
        line_lower = line.lower()

        for marker in markers:
            if marker in line_lower:
                return True

        if token_kw:
            # Same tokenization as the analyzer (also splits on = & ? , ; |),
            # otherwise 'ort=hamburg' would never match the keyword set.
            for word in _TOKEN_RE.findall(line_lower):
                cleaned = word.strip(STRIP_CHARS)
                if cleaned and normalize(cleaned) in token_kw:
                    return True
            if self._search_phrases:
                norm_line = _normalize_plain(line)
                for phrase in self._search_phrases:
                    if phrase in norm_line:
                        return True

        return False

    def analyze(
        self, logfiles: list[str], refresh_status: int = 5,
        workers: int = 0,
    ) -> tuple[OrderedDict, int]:
        """Analyze log files and return (results, line_count).

        Chooses the best strategy based on file count, size, and worker count:
        - Multi-file parallel: >1 file and >1 worker
        - Single-file chunk-parallel: 1 large file (>10MB) and >1 worker
        - Sequential: all other cases

        Args:
            logfiles: List of log file paths to analyze.
            refresh_status: Seconds between progress updates (0 = disabled).
            workers: Number of parallel workers (0 = auto, 1 = single-process).
        """
        num_workers = workers if workers > 0 else multiprocessing.cpu_count()

        if len(logfiles) > 1 and num_workers > 1:
            return self._analyze_parallel(logfiles, num_workers)

        if len(logfiles) == 1 and num_workers > 1:
            filepath = logfiles[0]
            try:
                file_size = os.path.getsize(filepath)
            except OSError:
                file_size = 0
            if file_size >= CHUNK_THRESHOLD_BYTES:
                return self._analyze_single_file_parallel(filepath, num_workers)

        return self._analyze_sequential(logfiles, refresh_status)

    def _analyze_sequential(
        self, logfiles: list[str], refresh_status: int,
    ) -> tuple[OrderedDict, int]:
        """Single-process analysis with progress display."""
        results = self._init_results()
        line_count = 0
        # \r/ANSI-Progress nur auf echten Terminals (nicht in Pipes/Cron)
        progress = refresh_status > 0 and sys.stderr.isatty()
        total_files = len(logfiles)
        start_time = time.time()

        for file_idx, logfile in enumerate(logfiles, 1):
            basename = os.path.basename(logfile)
            file_size = os.path.getsize(logfile) if os.path.isfile(logfile) else 0
            log.info("Analyzing: %s", logfile)

            if progress:
                print(
                    f"\r\033[K[{file_idx}/{total_files}] {basename} "
                    f"({file_size // 1024:,} KB) ...",
                    end="", flush=True, file=sys.stderr,
                )

            file_lines = self._process_lines(
                _iter_file_lines(logfile, self.diag), basename, results,
            )
            line_count += file_lines

            if progress:
                elapsed = time.time() - start_time
                rate = line_count / elapsed if elapsed > 0 else 0
                hits = sum(len(r[2]) for r in results.values())
                print(
                    f"\r\033[K[{file_idx}/{total_files}] {basename}: "
                    f"{file_lines:,} Zeilen | Gesamt: {line_count:,} "
                    f"| {rate:,.0f} Z/s | {hits} Findings",
                    end="", flush=True, file=sys.stderr,
                )

        if progress:
            elapsed = time.time() - start_time
            total_hits = sum(len(r[2]) for r in results.values())
            print(
                f"\r\033[K[{total_files}/{total_files}] "
                f"Fertig: {line_count:,} Zeilen in {elapsed:.1f}s "
                f"| {total_hits} Findings",
                file=sys.stderr,
            )

        self._finalize(results)
        log.info("Analysis complete: %d lines, %d files", line_count, len(logfiles))
        return results, line_count

    def _analyze_parallel(
        self, logfiles: list[str], num_workers: int,
    ) -> tuple[OrderedDict, int]:
        """Multi-process analysis using multiprocessing.Pool."""
        print(
            f"Parallele Analyse mit {num_workers} Workern...",
            file=sys.stderr,
        )
        results = self._init_results()
        line_count = 0

        kw = self._worker_kwargs()
        worker_args = [(logfile, kw) for logfile in logfiles]

        is_tty = sys.stderr.isatty()
        with multiprocessing.Pool(num_workers) as pool:
            # Finding 20: ordered imap (not imap_unordered) so results are merged
            # in input-file order -> deterministic, identical to a sequential run.
            for i, (file_results, file_lines, basename, worker_diag) in enumerate(
                pool.imap(_analyze_file_worker, worker_args), 1
            ):
                line_count += file_lines
                self._merge_results(results, file_results)
                self.diag.merge(worker_diag)
                if is_tty:
                    hits = sum(len(r[2]) for r in results.values())
                    print(
                        f"\r\033[K[{i}/{len(logfiles)}] {basename}: "
                        f"{file_lines:,} Zeilen | Gesamt: {line_count:,} "
                        f"| {hits} Findings",
                        end="", flush=True, file=sys.stderr,
                    )

        total_hits = sum(len(r[2]) for r in results.values())
        print(
            ("\r\033[K" if is_tty else "")
            + f"Fertig: {line_count:,} Zeilen, "
            f"{len(logfiles)} Dateien, {total_hits} Findings",
            file=sys.stderr,
        )
        self._finalize(results)
        log.info("Parallel analysis: %d lines, %d files, %d workers",
                 line_count, len(logfiles), num_workers)
        return results, line_count

    def _analyze_single_file_parallel(
        self, filepath: str, num_workers: int,
    ) -> tuple[OrderedDict, int]:
        """Chunk-based parallel analysis of a single large file."""
        basename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        print(
            f"Chunk-Analyse von {basename} ({file_size // 1024:,} KB) "
            f"mit {num_workers} Workern...",
            file=sys.stderr,
        )

        chunks = _compute_chunks(filepath, num_workers)
        results = self._init_results()
        line_count = 0
        errs_before = len(self.diag.file_errors)

        kw = self._worker_kwargs()
        worker_args = [
            (filepath, byte_start, byte_end, kw)
            for byte_start, byte_end in chunks
        ]

        is_tty = sys.stderr.isatty()
        with multiprocessing.Pool(num_workers) as pool:
            # Finding 20: ordered imap so chunks merge in byte order.
            for i, (chunk_results, chunk_lines, worker_diag) in enumerate(
                pool.imap(_analyze_chunk_worker, worker_args), 1
            ):
                line_count += chunk_lines
                self._merge_results(results, chunk_results)
                self.diag.merge(worker_diag)
                if is_tty:
                    hits = sum(len(r[2]) for r in results.values())
                    print(
                        f"\r\033[K[{i}/{len(chunks)}] {basename}: "
                        f"{line_count:,} Zeilen | {hits} Findings",
                        end="", flush=True, file=sys.stderr,
                    )

        # A single file was split into chunks: decide its completion status
        # once (chunks are not files). If any chunk reported a read error the
        # file counts as partial, otherwise complete.
        if len(self.diag.file_errors) == errs_before:
            self.diag.files_complete += 1
        else:
            self.diag.files_partial += 1

        total_hits = sum(len(r[2]) for r in results.values())
        print(
            ("\r\033[K" if is_tty else "")
            + f"Fertig: {line_count:,} Zeilen, {total_hits} Findings",
            file=sys.stderr,
        )
        self._finalize(results)
        log.info("Chunk analysis: %d lines, %d chunks, %d workers",
                 line_count, len(chunks), num_workers)
        return results, line_count

    def _init_results(self) -> OrderedDict:
        """Initialize the results OrderedDict with empty slots for each pattern."""
        results: OrderedDict = OrderedDict()
        for name, krit, _, _ in self.regexp:
            results[name] = ("regexp", krit, {})
        for name, krit, _, _, _ in self.field:
            if name in results:
                log.warning("Duplicate pattern name '%s': hits of both "
                            "patterns land in one slot, but type/criticality "
                            "of 'field' wins over '%s' - rename one pattern",
                            name, results[name][0])
            results[name] = ("field", krit, {})
        for name, krit, _ in self.search:
            if name in results:
                log.warning("Duplicate pattern name '%s': hits of both "
                            "patterns land in one slot, but type/criticality "
                            "of 'string' wins over '%s' - rename one pattern",
                            name, results[name][0])
            results[name] = ("string", krit, {})
        return results

    def _merge_results(self, target: OrderedDict, source: OrderedDict) -> None:
        """Merge worker results into the global results, enforcing limits.

        The global caps (Finding 4) must hold across all workers, so they are
        re-checked here. Example lines were already truncated by the worker.
        """
        for name, (typ, krit, hits) in source.items():
            if name not in target:
                target[name] = (typ, krit, {})
            target_hits = target[name][2]
            for value, entries in hits.items():
                if value not in target_hits:
                    if len(target_hits) >= self._max_values_per_pattern:
                        self.diag.findings_dropped_pattern += 1
                        continue
                    if self._total_values >= self._max_total_findings:
                        if not self.diag.global_limit_hit:
                            self.diag.global_limit_hit = "max_total_findings"
                        self.diag.findings_dropped_global += 1
                        continue
                    target_hits[value] = []
                    self._total_values += 1
                existing = target_hits[value]
                room = self._max_examples_per_value - len(existing)
                for entry in entries[:room] if room > 0 else []:
                    if self._total_examples >= self._max_total_examples:
                        if not self.diag.global_limit_hit:
                            self.diag.global_limit_hit = "max_total_examples"
                        break
                    existing.append(entry)
                    self._total_examples += 1

    @staticmethod
    def _finalize(results: OrderedDict) -> None:
        """Sort each value's examples into a deterministic order (Finding 20).

        Sort key: (filename, line number, start position, original value).
        This guarantees identical output for sequential and parallel runs and
        for any worker count.
        """
        def key(entry: tuple) -> tuple:
            filename = entry[0] if len(entry) > 0 else ""
            orig = entry[3] if len(entry) > 3 else ""
            start = entry[4] if len(entry) > 4 else -1
            lineno = entry[6] if len(entry) > 6 else 0
            return (filename, lineno, start, orig)

        for _typ, _krit, hits in results.values():
            for value, examples in hits.items():
                examples.sort(key=key)

    def _worker_kwargs(self) -> dict:
        """Bundle all constructor kwargs so workers rebuild an identical analyzer.

        Keeping this in one place avoids brittle positional argument tuples as
        more options are added.
        """
        return {
            "regexp": self.regexp,
            "field": self.field,
            "search": self.search,
            "sw_regexp": self.sw_regexp,
            "sw_field": self.sw_field,
            "sw_search": self.sw_search,
            "parse_json": self.parse_json,
            "prefilter": self.prefilter,
            "max_examples": self._max_examples_per_value,
            "regex_timeout_ms": self._regex_timeout_ms,
            "regex_disable_threshold": self._regex_disable_threshold,
            "max_values_per_pattern": self._max_values_per_pattern,
            "max_total_findings": self._max_total_findings,
            "max_total_examples": self._max_total_examples,
            "max_example_chars": self._max_example_chars,
            "masked_criticality": self._masked_criticality,
        }

    def _note_timeout(self, name: str) -> None:
        """Record a regex timeout and disable repeat offenders (Finding 1)."""
        count = self.diag.record_timeout(name)
        if count >= self._regex_disable_threshold and name not in self._disabled:
            self._disabled.add(name)
            self.diag.disabled_patterns.add(name)
            log.warning(
                "Pattern '%s' disabled for the rest of this scan after "
                "%d regex timeouts", name, count,
            )

    def _timed_search(self, pat: object, text: str, name: str) -> object:
        """search() with a runtime timeout; returns None on timeout."""
        try:
            return safe_search(pat, text, self._regex_timeout_ms)
        except RegexTimeout:
            self._note_timeout(name)
            return None

    def _timed_finditer(self, pat: object, text: str, name: str) -> list:
        """finditer() with a runtime timeout; returns [] on timeout."""
        try:
            return safe_finditer(pat, text, self._regex_timeout_ms)
        except RegexTimeout:
            self._note_timeout(name)
            return []

    def _truncate_example(self, line: str) -> tuple[str, bool]:
        """Trim an example line to max_example_chars with a visible marker."""
        limit = self._max_example_chars
        if limit and len(line) > limit:
            return line[:limit] + " " + _const.EXAMPLE_TRUNCATE_MARKER, True
        return line, False

    def _store_hit(
        self, results: OrderedDict, name: str, value: str,
        filename: str, line: str, field_token: str | None = None,
        orig_value: str | None = None, start: int = -1, end: int = -1,
        lineno: int = 0,
    ) -> None:
        """Store one finding example, enforcing all limits (Finding 4).

        Central choke point so per-pattern and global limits are applied
        consistently and every dropped/truncated item is counted for the
        report - no silent data loss.

        The stored example is a 7-tuple (Finding 7 - additive extension):
        ``(filename, line, field_token, orig_value, start, end, lineno)``.
        ``start``/``end`` are character offsets of the match in ``line``
        (``-1`` = not reliably known); ``orig_value`` is the exact substring
        from the original line (falls back to ``value`` for token matches).
        """
        hits = results[name][2]
        if value not in hits:
            if len(hits) >= self._max_values_per_pattern:
                self.diag.findings_dropped_pattern += 1
                return
            if self._total_values >= self._max_total_findings:
                if not self.diag.global_limit_hit:
                    self.diag.global_limit_hit = "max_total_findings"
                self.diag.findings_dropped_global += 1
                return
            hits[value] = []
            self._total_values += 1
            self.diag.findings_stored += 1
        examples = hits[value]
        if len(examples) >= self._max_examples_per_value:
            return
        if self._total_examples >= self._max_total_examples:
            if not self.diag.global_limit_hit:
                self.diag.global_limit_hit = "max_total_examples"
            return
        stored, truncated = self._truncate_example(line)
        if truncated:
            self.diag.examples_truncated += 1
        examples.append((
            filename, stored, field_token,
            value if orig_value is None else orig_value,
            start, end, lineno,
        ))
        self._total_examples += 1

    def _store_masked(
        self, results: OrderedDict, name: str,
        filename: str, line: str, field_token: str | None,
    ) -> None:
        """Record a masked credential value as a distinct low-severity finding.

        The masked value itself is never stored as a would-be secret
        (Finding 5).
        """
        key = name + _const.MASKED_SUFFIX
        if key not in results:
            results[key] = ("field", self._masked_criticality, {})
        self._store_hit(
            results, key, _const.MASKED_STATUS, filename, line, field_token,
        )

    def _process_lines(
        self, lines: Iterator[str], basename: str, results: OrderedDict,
    ) -> int:
        """Process decoded, stripped lines. Returns line count.

        Shared by sequential, chunk-worker, and file-worker paths (DRY).
        """
        passes = self._passes_prefilter
        analyze = self._analyze_line
        line_count = 0
        for line in lines:
            line_count += 1
            if line and passes(line):
                analyze(line, basename, results, line_count)
        return line_count

    def _analyze_line(
        self, line: str, filename: str, results: OrderedDict, lineno: int = 0,
    ) -> None:
        """Analyze a single line against all pattern types in one pass.

        All checks are inlined to eliminate method-call overhead.
        All attribute lookups are cached as local variables.
        """
        tokens = tokenize(line, self.parse_json)

        regexp_patterns = self._regexp_token
        field_patterns = self.field
        search_index = self._search_index
        sw_search = self.sw_search
        sw_regexp = self.sw_regexp
        sw_field = self.sw_field
        _normalize = normalize
        _find_field = find_field_value
        _store = self._store_hit

        disabled = self._disabled

        # --- Line-scope regexp check (patterns containing whitespace) ---
        for name, _, _, pat in self._regexp_line:
            if disabled and name in disabled:
                continue
            for m in self._timed_finditer(pat, line, name):
                raw = m.group(0)
                value = raw.strip()
                if len(value) < MIN_LEN_REGEXP:
                    continue
                if _normalize(value) in sw_regexp:
                    continue
                lead = len(raw) - len(raw.lstrip())
                start = m.start() + lead
                _store(results, name, value, filename, line,
                       orig_value=value, start=start, end=start + len(value),
                       lineno=lineno)

        # --- Multi-word search phrases (line-based, normalized) ---
        if self._search_phrases:
            # Finding 7: keep an offset map so the *original* substring (not the
            # normalized phrase) is stored and highlighted.
            norm_line, offsets = normalize_with_offsets(line)
            for phrase, names in self._search_phrases.items():
                if phrase in sw_search or phrase not in norm_line:
                    continue
                # word-boundary check on the normalized line
                idx, bounded = norm_line.find(phrase), False
                while idx != -1:
                    end = idx + len(phrase)
                    if ((idx == 0 or not norm_line[idx - 1].isalnum())
                            and (end >= len(norm_line)
                                 or not norm_line[end].isalnum())):
                        bounded = True
                        break
                    idx = norm_line.find(phrase, idx + 1)
                if not bounded:
                    continue
                # Map the normalized [idx, end) span back to the original line.
                if 0 <= idx < len(offsets) and end - 1 < len(offsets):
                    o_start = offsets[idx]
                    o_end = offsets[end - 1] + 1
                    orig = line[o_start:o_end]
                else:  # pragma: no cover - defensive
                    o_start = o_end = -1
                    orig = phrase
                for name in names:
                    _store(results, name, phrase, filename, line,
                           orig_value=orig, start=o_start, end=o_end,
                           lineno=lineno)

        for i, token in enumerate(tokens):
            norm = _normalize(token)
            tlen = len(token)

            # --- Inline regexp check ---
            if tlen >= MIN_LEN_REGEXP and regexp_patterns:
                for name, _, _, pat in regexp_patterns:
                    if disabled and name in disabled:
                        continue
                    m = self._timed_search(pat, token, name)
                    if m is None:
                        continue
                    # store the actual match, not the whole token
                    # ('contact=<alice@example.com>' -> 'alice@example.com')
                    value = m.group(0)
                    if _normalize(value) in sw_regexp or norm in sw_regexp:
                        continue
                    pos = line.find(value)
                    _store(results, name, value, filename, line,
                           orig_value=value, start=pos,
                           end=pos + len(value) if pos >= 0 else -1,
                           lineno=lineno)

            # --- Inline field check ---
            if tlen >= MIN_LEN_FIELD and field_patterns:
                # ':' ist kein Token-Separator; '=' normalerweise schon,
                # kann aber in JSON-Fragment-Tokens vorkommen.
                inline_kv = (
                    split_inline_field(token)
                    if ":" in token or "=" in token else None
                )
                for name, _, _, pat, offset in field_patterns:
                    if disabled and name in disabled:
                        continue
                    if self._timed_search(pat, token, name) is None:
                        continue
                    # key:value in one token (tokenizer keeps ':' intact)
                    if inline_kv is not None and offset == 1 and \
                            self._timed_search(pat, inline_kv[0], name) is not None:
                        value = inline_kv[1]
                    else:
                        value, _ = _find_field(tokens, i + offset)
                    if not value:
                        continue
                    # Finding 5: masked values are a distinct, lower-severity
                    # finding - not a plaintext-secret hit, not silently dropped.
                    if _is_masked_value(value):
                        self._store_masked(results, name, filename, line, token)
                        continue
                    # Only *unambiguous* filesystem paths suppress the value.
                    if _looks_like_path(value):
                        continue
                    if _normalize(value) not in sw_field:
                        pos = line.find(value)
                        _store(results, name, value, filename, line, token,
                               orig_value=value, start=pos,
                               end=pos + len(value) if pos >= 0 else -1,
                               lineno=lineno)

            # --- Inline string search ---
            if norm not in sw_search:
                names = search_index.get(norm)
                if names:
                    pos = line.find(token)
                    for name in names:
                        _store(results, name, token, filename, line,
                               orig_value=token, start=pos,
                               end=pos + len(token) if pos >= 0 else -1,
                               lineno=lineno)


# ---------------------------------------------------------------------------
# Shared I/O helpers (used by sequential and worker paths)
# ---------------------------------------------------------------------------

def _iter_file_lines(
    filepath: str, diag: ScanDiagnostics | None = None,
) -> Iterator[str]:
    """Iterate over decoded, stripped lines from a file.

    Handles UTF-8 decoding with replace fallback and logs first encoding error.
    Records file-completion / error status into ``diag`` (Finding 2) so that a
    file that could not be fully read is no longer silently treated as success.
    """
    encoding_warned = False
    yielded = False
    try:
        with open(filepath, "rb") as raw:
            for raw_line in raw:
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    if diag is not None:
                        diag.decode_errors += 1
                    if not encoding_warned:
                        log.warning("%s: Non-UTF-8 bytes detected", filepath)
                        encoding_warned = True
                    line = raw_line.decode("utf-8", errors="replace")
                yielded = True
                yield line.strip()
    except (IOError, OSError) as e:
        log.warning("Error reading %s: %s", filepath, e)
        if diag is not None:
            diag.record_file_error(filepath, str(e), partial=yielded)
        return
    if diag is not None:
        diag.files_complete += 1


def _iter_chunk_lines(
    filepath: str, byte_start: int, byte_end: int,
    diag: ScanDiagnostics | None = None,
) -> Iterator[str]:
    """Iterate over decoded, stripped lines from a byte range of a file.

    Aligns to line boundaries within the [byte_start, byte_end) range.
    File-completion is decided once by the caller (chunks are not files), so
    this helper only records decode errors and read errors into ``diag``.
    """
    encoding_warned = False
    try:
        with open(filepath, "rb") as f:
            f.seek(byte_start)
            while f.tell() < byte_end:
                raw_line = f.readline()
                if not raw_line:
                    break
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    if diag is not None:
                        diag.decode_errors += 1
                    if not encoding_warned:
                        log.warning("%s: Non-UTF-8 bytes in chunk", filepath)
                        encoding_warned = True
                    line = raw_line.decode("utf-8", errors="replace")
                yield line.strip()
    except (IOError, OSError) as e:
        log.warning("Error reading chunk %s: %s", filepath, e)
        if diag is not None:
            diag.file_errors.append((filepath, str(e)))
            diag.other_errors += 1


# ---------------------------------------------------------------------------
# Top-level worker functions (must be picklable for multiprocessing)
# ---------------------------------------------------------------------------

def _compute_chunks(
    filepath: str, num_chunks: int,
) -> list[tuple[int, int]]:
    """Split a file into byte-offset chunks aligned to line boundaries.

    Returns list of (byte_start, byte_end) tuples.
    """
    file_size = os.path.getsize(filepath)
    if file_size == 0 or num_chunks <= 1:
        return [(0, file_size)]

    chunk_size = file_size // num_chunks
    chunks: list[tuple[int, int]] = []

    with open(filepath, "rb") as f:
        start = 0
        for _ in range(num_chunks - 1):
            target = start + chunk_size
            if target >= file_size:
                break
            f.seek(target)
            f.readline()  # skip partial line
            end = f.tell()
            if end >= file_size:
                break
            chunks.append((start, end))
            start = end
        chunks.append((start, file_size))

    return chunks


def _analyze_file_worker(args: tuple) -> tuple[OrderedDict, int, str]:
    """Worker function for multiprocessing.Pool (multi-file mode).

    Must be a top-level function (pickle requirement).
    Returns (results, line_count, basename).
    """
    logfile, kwargs = args
    analyzer = LogAnalyzer(**kwargs)
    results = analyzer._init_results()
    basename = os.path.basename(logfile)
    line_count = analyzer._process_lines(
        _iter_file_lines(logfile, analyzer.diag), basename, results,
    )
    return results, line_count, basename, analyzer.diag


def _analyze_chunk_worker(args: tuple) -> tuple[OrderedDict, int]:
    """Worker function for chunk-based single-file parallelism.

    Reads a byte range from the file and analyzes each line.
    Returns (results, line_count).
    """
    filepath, byte_start, byte_end, kwargs = args
    analyzer = LogAnalyzer(**kwargs)
    results = analyzer._init_results()
    basename = os.path.basename(filepath)
    line_count = analyzer._process_lines(
        _iter_chunk_lines(filepath, byte_start, byte_end, analyzer.diag),
        basename, results,
    )
    return results, line_count, analyzer.diag
