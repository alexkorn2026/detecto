"""Configuration: DetectoConfig dataclass and INI loading."""
from __future__ import annotations

import configparser
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

__all__ = ["DetectoConfig", "load_config"]

log = logging.getLogger(__name__)

INI_FILE = "detecto.ini"
REGEXP_FILE = "regexp.csv"
FIELD_FILE = "field.csv"
SUCHMUSTER_FILE = "suchmuster.csv"
SUCHMUSTER_DIR = "suchmuster"
STOPWORD_REGEXP_FILE = "stopword_regexp.txt"
STOPWORD_FIELD_FILE = "stopword_field.txt"
STOPWORD_SUCHMUSTER_FILE = "stopword_suchmuster.txt"
ANON_PATTERN_DEFAULT = "sss**sss**sss**"


@dataclass
class DetectoConfig:
    """All configurable defaults for Detecto, loaded from detecto.ini."""

    examplecount: int = 3
    minlen: int = 5
    critical: int = 5
    # Finding 3: sensitive findings are anonymized by default. Plaintext
    # requires the explicit --show-sensitive-values flag.
    anon: bool = True
    excelanon: bool = True
    full: bool = False
    nocolor: bool = False
    show_sensitive_values: bool = False
    showskipped: bool = False
    verbose: bool = False
    anon_muster: str = ANON_PATTERN_DEFAULT
    search_regexp: bool = True
    search_field: bool = True
    search_suchmuster: bool = True
    refresh_status: int = 5
    parse_json: bool = False
    workers: int = 0  # 0 = auto (cpu_count), 1 = single-process
    prefilter: str = "off"  # off | regexp_field | all
    max_examples: int = 100  # max example lines stored per unique value
    # Finding 1: runtime regex protection
    regex_timeout_ms: int = 100
    regex_disable_threshold: int = 5

    regexp_file: str = REGEXP_FILE
    field_file: str = FIELD_FILE
    suchmuster_file: str = SUCHMUSTER_FILE
    suchmuster_dir: str = SUCHMUSTER_DIR
    stopword_regexp_file: str = STOPWORD_REGEXP_FILE
    stopword_field_file: str = STOPWORD_FIELD_FILE
    stopword_suchmuster_file: str = STOPWORD_SUCHMUSTER_FILE

    def __post_init__(self) -> None:
        """Validate and clamp values to sane ranges."""
        self.examplecount = max(1, self.examplecount)
        self.minlen = max(2, self.minlen)
        self.critical = max(1, min(5, self.critical))
        self.refresh_status = max(0, self.refresh_status)
        self.workers = max(0, self.workers)
        self.max_examples = max(1, self.max_examples)
        self.regex_timeout_ms = max(0, self.regex_timeout_ms)
        self.regex_disable_threshold = max(1, self.regex_disable_threshold)
        if self.prefilter not in ("off", "regexp_field", "all"):
            self.prefilter = "off"

    def as_dict(self) -> dict[str, object]:
        """Return all fields as a flat dictionary."""
        return asdict(self)


def _safe_getint(section, key: str, fallback: int) -> int:
    """getint with warning instead of crash on malformed values."""
    try:
        return section.getint(key, fallback=fallback)
    except ValueError:
        log.warning("Invalid integer for '%s' in detecto.ini, using %s", key, fallback)
        return fallback


def _safe_getboolean(section, key: str, fallback: bool) -> bool:
    """getboolean with warning instead of crash on malformed values."""
    try:
        return section.getboolean(key, fallback=fallback)
    except ValueError:
        log.warning("Invalid boolean for '%s' in detecto.ini, using %s", key, fallback)
        return fallback


def load_config(base_dir: Path) -> DetectoConfig:
    """Load detecto.ini and return a DetectoConfig object."""
    ini_path = base_dir / INI_FILE
    cfg = DetectoConfig()

    if not ini_path.is_file():
        log.debug("No INI file found: %s", ini_path)
        return cfg

    cp = configparser.ConfigParser()
    try:
        cp.read(str(ini_path), encoding="utf-8")
    except configparser.Error as e:
        log.warning("Invalid detecto.ini (%s) - using defaults", e)
        return cfg

    if cp.has_section("defaults"):
        s = cp["defaults"]
        cfg.examplecount = _safe_getint(s, "examplecount", cfg.examplecount)
        cfg.minlen = _safe_getint(s, "minlen", cfg.minlen)
        cfg.critical = _safe_getint(s, "critical", cfg.critical)
        cfg.anon = _safe_getboolean(s, "anon", cfg.anon)
        cfg.excelanon = _safe_getboolean(s, "excelanon", cfg.excelanon)
        cfg.full = _safe_getboolean(s, "full", cfg.full)
        cfg.show_sensitive_values = _safe_getboolean(
            s, "show_sensitive_values", cfg.show_sensitive_values
        )
        cfg.nocolor = _safe_getboolean(s, "nocolor", cfg.nocolor)
        cfg.showskipped = _safe_getboolean(s, "showskipped", cfg.showskipped)
        cfg.verbose = _safe_getboolean(s, "verbose", cfg.verbose)
        cfg.anon_muster = s.get("anon_muster", fallback=cfg.anon_muster)
        cfg.search_regexp = _safe_getboolean(s, "search_regexp", cfg.search_regexp)
        # 'search_feld' (deutsch) ist der historische INI-Key, 'search_field'
        # der Config-Name - beide akzeptieren.
        cfg.search_field = _safe_getboolean(
            s, "search_field",
            _safe_getboolean(s, "search_feld", cfg.search_field),
        )
        cfg.search_suchmuster = _safe_getboolean(
            s, "search_suchmuster", cfg.search_suchmuster
        )
        cfg.refresh_status = _safe_getint(s, "refresh_status", cfg.refresh_status)
        cfg.parse_json = _safe_getboolean(s, "parse_json", cfg.parse_json)
        cfg.workers = _safe_getint(s, "workers", cfg.workers)
        cfg.prefilter = s.get("prefilter", fallback=cfg.prefilter)
        cfg.max_examples = _safe_getint(s, "max_examples", cfg.max_examples)
        cfg.regex_timeout_ms = _safe_getint(s, "regex_timeout_ms", cfg.regex_timeout_ms)
        cfg.regex_disable_threshold = _safe_getint(
            s, "regex_disable_threshold", cfg.regex_disable_threshold
        )

    if cp.has_section("files"):
        s = cp["files"]
        cfg.regexp_file = s.get("regexp", fallback=cfg.regexp_file)
        cfg.field_file = s.get("field", fallback=cfg.field_file)
        cfg.suchmuster_file = s.get("suchmuster", fallback=cfg.suchmuster_file)
        cfg.suchmuster_dir = s.get("suchmuster_verzeichnis", fallback=cfg.suchmuster_dir)
        cfg.stopword_regexp_file = s.get("stopword_regexp", fallback=cfg.stopword_regexp_file)
        cfg.stopword_field_file = s.get("stopword_field", fallback=cfg.stopword_field_file)
        cfg.stopword_suchmuster_file = s.get(
            "stopword_suchmuster", fallback=cfg.stopword_suchmuster_file
        )

    cfg.__post_init__()
    log.info("Config loaded from %s", ini_path)
    return cfg
