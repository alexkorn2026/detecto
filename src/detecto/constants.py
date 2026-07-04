"""Centralized constants for Detecto."""
from __future__ import annotations

__all__ = [
    "COPYRIGHT_YEAR",
    "LABEL_WIDTH",
    "PATTERN_DELIMITER",
    "REGEX_TIMEOUT_SEC",
    "REGEX_LOADCHECK_MS",
    "REGEX_TIMEOUT_MS",
    "REGEX_DISABLE_THRESHOLD",
    "REGEX_TEST_STRING",
    "MAX_HITS_PER_PATTERN",
    "MAX_EXAMPLES_PER_VALUE",
    "MAX_LINE_BYTES",
    "MAX_EXAMPLE_CHARS",
    "MAX_TOTAL_FINDINGS",
    "MAX_TOTAL_EXAMPLES",
    "MAX_VALUES_PER_PATTERN",
    "EXAMPLE_TRUNCATE_MARKER",
    "MIN_LEN_REGEXP",
    "MIN_LEN_FIELD",
    "FIELD_SEPARATORS",
    "FIELD_VALUE_LOOKAHEAD",
    "CHUNK_THRESHOLD_BYTES",
    "NORMALIZE_CACHE_SIZE",
    "PREFILTER_MARKERS",
    "STRIP_CHARS",
    "EXCEL_FORMULA_CHARS",
    "CLR_HEADER",
    "CLR_CUSTOMER",
    "CLR_VALUE",
    "CLR_FIELD",
    "CLR_KRIT",
    "ANSI_RED",
    "ANSI_GREEN",
    "ANSI_DARK_GREEN",
    "ANSI_YELLOW",
    "ANSI_RESET",
    "ANSI_TYPE_MAP",
    "KRIT_LABELS",
]

# --- Application ---
COPYRIGHT_YEAR = "2026"
LABEL_WIDTH = 25

# --- Pattern files ---
PATTERN_DELIMITER = "::"

# --- Security ---
# Load-time compile pre-check (Finding 1): reject obviously catastrophic
# patterns before the scan even starts. This is a *first* line of defence,
# no longer the only one.
REGEX_TIMEOUT_SEC = 2
REGEX_LOADCHECK_MS = 2000  # budget for the load-time pre-check
REGEX_TEST_STRING = "a" * 1000
# Runtime per-match timeout (Finding 1). Enforced while matching real log
# lines when the `regex` package is available.
REGEX_TIMEOUT_MS = 100
# A pattern that times out this many times is disabled for the rest of the
# scan (per worker) to keep a single bad pattern from stalling everything.
REGEX_DISABLE_THRESHOLD = 5
EXCEL_FORMULA_CHARS = ("=", "+", "-", "@", "\t", "\r")

# --- Analysis ---
MAX_HITS_PER_PATTERN = 10_000
MAX_EXAMPLES_PER_VALUE = 100
# --- Global limits (Finding 4) ---
MAX_LINE_BYTES = 1_048_576
MAX_EXAMPLE_CHARS = 4000
MAX_TOTAL_FINDINGS = 100_000
MAX_TOTAL_EXAMPLES = 20_000
MAX_VALUES_PER_PATTERN = 10_000
EXAMPLE_TRUNCATE_MARKER = "…[gekuerzt]"
MIN_LEN_REGEXP = 5    # shortest regexp match: a@b.c (email)
MIN_LEN_FIELD = 3     # shortest field name: pwd
FIELD_SEPARATORS = frozenset({"->", "=>", ":", "=", "==", "-->", "<<", ">>"})
FIELD_VALUE_LOOKAHEAD = 4  # max tokens to look ahead for field value
PATH_PREFIXES = ("/", "\\", "~/")

# --- Performance ---
CHUNK_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MB for single-file parallelism
NORMALIZE_CACHE_SIZE = 100_000  # LRU cache entries for normalize()

# --- Pre-filter markers for field/regexp substring checks ---
STRIP_CHARS = '"\'{}[](),.:;!?=&|<>'
PREFILTER_MARKERS = (
    "passw", "kennw", "pwd", "secret", "credential", "cred",
    "identified", "api_key", "apikey", "api-key", "x-api-key",
    "api_token", "access_token", "accesstoken", "bearer",
    "refresh_token", "refreshtoken", "jsessionid", "session_id",
    "sessionid", "client_secret", "clientsecret",
    "db.password", "jdbc.password", "authorization",
    "proxy_password", "smtp_password", "bind_password",
    "aws_key", "azure_secret", "gcp_key",
    "@", "eyj", "-----begin", "jdbc:", "akia",
    "accountkey", "ghp_", "gho_", "ghu_", "ghs_", "ghr_", "xox",
    "vs-", "nato", "geheim", "restreint", "confidentiel", "hra", "hrb",
)

# --- ANSI terminal colors ---
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_DARK_GREEN = "\033[32m"
ANSI_YELLOW = "\033[93m"
ANSI_RESET = "\033[0m"

ANSI_TYPE_MAP: dict[str, str] = {
    "regexp": ANSI_GREEN,
    "field": ANSI_YELLOW,
    "string": ANSI_GREEN,
}

# --- Criticality ---
KRIT_LABELS: dict[int, str] = {
    1: "kritisch",
    2: "hoch",
    3: "mittel",
    4: "niedrig",
    5: "info",
}

# --- Excel colors (ARGB) ---
CLR_HEADER = "FF2F5496"
CLR_CUSTOMER = "FFFFF2CC"
CLR_VALUE = "FFFFCCCC"
CLR_FIELD = "FFC6EFCE"
CLR_KRIT: dict[int, str] = {
    1: "FFFF9999",
    2: "FFFFCC99",
    3: "FFFFFF99",
    4: "FFE2EFDA",
    5: "FFFFFFFF",
}
