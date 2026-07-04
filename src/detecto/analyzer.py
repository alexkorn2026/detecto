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
    PATH_PREFIXES, MIN_LEN_REGEXP, MIN_LEN_FIELD,
    STRIP_CHARS, PREFILTER_MARKERS, CHUNK_THRESHOLD_BYTES,
)
from detecto.loaders import RegexpPattern, FieldPattern, SearchPattern
from detecto.tokenizer import (
    tokenize, find_field_value, split_inline_field, _TOKEN_RE,
)
from detecto.utils import normalize

__all__ = ["LogAnalyzer"]

log = logging.getLogger(__name__)

_ASTERISK_RE = re.compile(r"\*+$")
# Pre-filter: lines with >=5 consecutive digits may contain numeric PII
# (VSNR, KVNR, Steuer-ID, IBAN, Telefon, PLZ, ...) and must pass the filter.
_DIGIT_RUN_RE = re.compile(r"\d{5}")

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
                _iter_file_lines(logfile), basename, results,
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

        worker_args = [
            (logfile, self.regexp, self.field, self.search,
             self.sw_regexp, self.sw_field, self.sw_search,
             self.parse_json, self.prefilter, self.max_examples)
            for logfile in logfiles
        ]

        is_tty = sys.stderr.isatty()
        with multiprocessing.Pool(num_workers) as pool:
            for i, (file_results, file_lines, basename) in enumerate(
                pool.imap_unordered(_analyze_file_worker, worker_args), 1
            ):
                line_count += file_lines
                self._merge_results(results, file_results)
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

        worker_args = [
            (filepath, byte_start, byte_end,
             self.regexp, self.field, self.search,
             self.sw_regexp, self.sw_field, self.sw_search,
             self.parse_json, self.prefilter, self.max_examples)
            for byte_start, byte_end in chunks
        ]

        is_tty = sys.stderr.isatty()
        with multiprocessing.Pool(num_workers) as pool:
            for i, (chunk_results, chunk_lines) in enumerate(
                pool.imap_unordered(_analyze_chunk_worker, worker_args), 1
            ):
                line_count += chunk_lines
                self._merge_results(results, chunk_results)
                if is_tty:
                    hits = sum(len(r[2]) for r in results.values())
                    print(
                        f"\r\033[K[{i}/{len(chunks)}] {basename}: "
                        f"{line_count:,} Zeilen | {hits} Findings",
                        end="", flush=True, file=sys.stderr,
                    )

        total_hits = sum(len(r[2]) for r in results.values())
        print(
            ("\r\033[K" if is_tty else "")
            + f"Fertig: {line_count:,} Zeilen, {total_hits} Findings",
            file=sys.stderr,
        )
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
        """Merge file-level results into the global results."""
        max_examples = self.max_examples
        max_hits = _const.MAX_HITS_PER_PATTERN
        for name, (typ, krit, hits) in source.items():
            if name not in target:
                target[name] = (typ, krit, {})
            target_hits = target[name][2]
            for value, entries in hits.items():
                if max_hits and len(target_hits) >= max_hits:
                    continue  # skip this value but keep iterating others
                if value not in target_hits:
                    target_hits[value] = []
                remaining = max_examples - len(target_hits[value])
                if remaining > 0:
                    target_hits[value].extend(entries[:remaining])

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
                analyze(line, basename, results)
        return line_count

    def _analyze_line(
        self, line: str, filename: str, results: OrderedDict,
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
        max_examples = self.max_examples
        max_hits = _const.MAX_HITS_PER_PATTERN
        _normalize = normalize
        _find_field = find_field_value
        _is_path = self._is_path_or_mask

        # --- Line-scope regexp check (patterns containing whitespace) ---
        for name, _, _, pat in self._regexp_line:
            for m in pat.finditer(line):
                value = m.group(0).strip()
                if len(value) < MIN_LEN_REGEXP:
                    continue
                if _normalize(value) in sw_regexp:
                    continue
                hits = results[name][2]
                if max_hits and len(hits) >= max_hits:
                    break
                if value not in hits:
                    hits[value] = []
                if len(hits[value]) < max_examples:
                    hits[value].append((filename, line, None))

        # --- Multi-word search phrases (line-based, normalized) ---
        if self._search_phrases:
            norm_line = _normalize_plain(line)
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
                for name in names:
                    hits = results[name][2]
                    if max_hits and len(hits) >= max_hits:
                        continue
                    if phrase not in hits:
                        hits[phrase] = []
                    if len(hits[phrase]) < max_examples:
                        hits[phrase].append((filename, line, None))

        for i, token in enumerate(tokens):
            norm = _normalize(token)
            tlen = len(token)

            # --- Inline regexp check ---
            if tlen >= MIN_LEN_REGEXP and regexp_patterns:
                for name, _, _, pat in regexp_patterns:
                    m = pat.search(token)
                    if m is None:
                        continue
                    # store the actual match, not the whole token
                    # ('contact=<alice@example.com>' -> 'alice@example.com')
                    value = m.group(0)
                    if _normalize(value) in sw_regexp or norm in sw_regexp:
                        continue
                    hits = results[name][2]
                    if max_hits and len(hits) >= max_hits:
                        continue
                    if value not in hits:
                        hits[value] = []
                    if len(hits[value]) < max_examples:
                        hits[value].append((filename, line, None))

            # --- Inline field check ---
            if tlen >= MIN_LEN_FIELD and field_patterns:
                # ':' ist kein Token-Separator; '=' normalerweise schon,
                # kann aber in JSON-Fragment-Tokens vorkommen.
                inline_kv = (
                    split_inline_field(token)
                    if ":" in token or "=" in token else None
                )
                for name, _, _, pat, offset in field_patterns:
                    if not pat.search(token):
                        continue
                    # key:value in one token (tokenizer keeps ':' intact)
                    if inline_kv is not None and offset == 1 and \
                            pat.search(inline_kv[0]):
                        value = inline_kv[1]
                    else:
                        value, _ = _find_field(tokens, i + offset)
                    if not value or _is_path(value):
                        continue
                    if _normalize(value) not in sw_field:
                        hits = results[name][2]
                        if max_hits and len(hits) >= max_hits:
                            continue
                        if value not in hits:
                            hits[value] = []
                        if len(hits[value]) < max_examples:
                            hits[value].append((filename, line, token))

            # --- Inline string search ---
            if norm not in sw_search:
                names = search_index.get(norm)
                if names:
                    for name in names:
                        hits = results[name][2]
                        if max_hits and len(hits) >= max_hits:
                            continue
                        if token not in hits:
                            hits[token] = []
                        if len(hits[token]) < max_examples:
                            hits[token].append((filename, line, None))

    @staticmethod
    def _is_path_or_mask(value: str) -> bool:
        """Check if a value is a file path or asterisk mask."""
        if value.startswith(PATH_PREFIXES):
            return True
        if len(value) >= 2 and value[1] == ":":
            return True
        return bool(_ASTERISK_RE.fullmatch(value))


# ---------------------------------------------------------------------------
# Shared I/O helpers (used by sequential and worker paths)
# ---------------------------------------------------------------------------

def _iter_file_lines(filepath: str) -> Iterator[str]:
    """Iterate over decoded, stripped lines from a file.

    Handles UTF-8 decoding with replace fallback and logs first encoding error.
    """
    encoding_warned = False
    try:
        with open(filepath, "rb") as raw:
            for raw_line in raw:
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    if not encoding_warned:
                        log.warning("%s: Non-UTF-8 bytes detected", filepath)
                        encoding_warned = True
                    line = raw_line.decode("utf-8", errors="replace")
                yield line.strip()
    except (IOError, OSError) as e:
        log.warning("Error reading %s: %s", filepath, e)


def _iter_chunk_lines(filepath: str, byte_start: int, byte_end: int) -> Iterator[str]:
    """Iterate over decoded, stripped lines from a byte range of a file.

    Aligns to line boundaries within the [byte_start, byte_end) range.
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
                    if not encoding_warned:
                        log.warning("%s: Non-UTF-8 bytes in chunk", filepath)
                        encoding_warned = True
                    line = raw_line.decode("utf-8", errors="replace")
                yield line.strip()
    except (IOError, OSError) as e:
        log.warning("Error reading chunk %s: %s", filepath, e)


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
    (logfile, regexp, field, search,
     sw_regexp, sw_field, sw_search, parse_json, prefilter,
     max_examples) = args

    analyzer = LogAnalyzer(
        regexp=regexp, field=field, search=search,
        sw_regexp=sw_regexp, sw_field=sw_field, sw_search=sw_search,
        parse_json=parse_json, prefilter=prefilter,
        max_examples=max_examples,
    )
    results = analyzer._init_results()
    basename = os.path.basename(logfile)
    line_count = analyzer._process_lines(
        _iter_file_lines(logfile), basename, results,
    )
    return results, line_count, basename


def _analyze_chunk_worker(args: tuple) -> tuple[OrderedDict, int]:
    """Worker function for chunk-based single-file parallelism.

    Reads a byte range from the file and analyzes each line.
    Returns (results, line_count).
    """
    (filepath, byte_start, byte_end,
     regexp, field, search,
     sw_regexp, sw_field, sw_search,
     parse_json, prefilter, max_examples) = args

    analyzer = LogAnalyzer(
        regexp=regexp, field=field, search=search,
        sw_regexp=sw_regexp, sw_field=sw_field, sw_search=sw_search,
        parse_json=parse_json, prefilter=prefilter,
        max_examples=max_examples,
    )
    results = analyzer._init_results()
    basename = os.path.basename(filepath)
    line_count = analyzer._process_lines(
        _iter_chunk_lines(filepath, byte_start, byte_end), basename, results,
    )
    return results, line_count
