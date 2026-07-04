"""Findings 7, 20, 24: original value + positions, determinism, position anon."""
from __future__ import annotations

import re

from detecto.analyzer import LogAnalyzer
from detecto.formatter import highlight
from detecto.utils import normalize, normalize_with_offsets


# ---- Finding 7: normalize_with_offsets maps back to the original ----------

def test_normalize_with_offsets_matches_normalize():
    for text in ["Multiple-Sklerose", "MULTIPLE   SKLEROSE", "Straße", "Müller"]:
        norm, offsets = normalize_with_offsets(text)
        assert norm == normalize(text)
        assert len(offsets) == len(norm)


def test_offset_mapping_umlaut():
    text = "Straße"
    norm, offsets = normalize_with_offsets(text)
    # 'ß' -> 'ss': both s map back to the original 'ß' index (4)
    assert norm == "strasse"
    assert offsets[norm.index("ss")] == text.index("ß")


# ---- Finding 7: phrase findings keep the ORIGINAL text --------------------

def _phrase_analyzer():
    # multi-word search value -> phrase path
    return LogAnalyzer(search=[("Diagnose", 3, {normalize("Multiple Sklerose")})])


def test_phrase_stores_original_not_normalized(tmp_path):
    p = tmp_path / "d.log"
    p.write_text("Patient hat Múltiple Sklerose diagnostiziert\n", encoding="utf-8")
    a = _phrase_analyzer()
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    entries = next(iter(results["Diagnose"][2].values()))
    entry = entries[0]
    orig, start, end, lineno = entry[3], entry[4], entry[5], entry[6]
    line = entry[1]
    assert line[start:end] == orig          # positions map to original
    assert orig.lower().startswith("m")      # original text, accents preserved
    assert "ú" in orig or "Sklerose" in orig
    assert lineno == 1


# ---- Finding 20: deterministic results regardless of worker count ---------

def _make_multi_file(tmp_path, n_files=4, n_lines=50):
    paths = []
    for fi in range(n_files):
        p = tmp_path / f"f{fi}.log"
        p.write_text(
            "\n".join(f"email=user{fi}_{i}@test.de" for i in range(n_lines)) + "\n",
            encoding="utf-8",
        )
        paths.append(str(p))
    return paths


def _snapshot(results):
    return {
        name: {v: [e[:7] for e in ex] for v, ex in hits.items()}
        for name, (_, _, hits) in results.items()
    }


def test_parallel_matches_sequential(tmp_path):
    paths = _make_multi_file(tmp_path)
    ana = LogAnalyzer(regexp=[("email", 4, "e", re.compile(r"[^\s=]+@[^\s=]+\.[a-z]+"))])
    seq, _ = ana.analyze(paths, refresh_status=0, workers=1)
    seq_snap = _snapshot(seq)
    for workers in (2, 4):
        a = LogAnalyzer(regexp=[("email", 4, "e", re.compile(r"[^\s=]+@[^\s=]+\.[a-z]+"))])
        par, _ = a.analyze(paths, refresh_status=0, workers=workers)
        assert _snapshot(par) == seq_snap, f"workers={workers} differs"


# ---- Finding 24: position-based highlight / anonymization -----------------

def test_highlight_uses_exact_position():
    line = "value anna here"
    out = highlight(line, "anna", anon=False, color=False, start=6, end=10)
    assert out == "value anna here"  # no color, exact span, unchanged text


def test_highlight_does_not_mark_substring():
    # 'anna' must not be marked inside 'Susanna'
    line = "user Susanna logged in"
    out = highlight(line, "anna", anon=True, color=False,
                    anonymizer=_Anon())
    assert "Susanna" in out  # substring not redacted due to word boundary


def test_anon_redacts_all_identical_occurrences():
    line = "a=secret and b=secret"
    out = highlight(line, "secret", anon=True, color=False, anonymizer=_Anon())
    assert "secret" not in out  # both occurrences redacted


class _Anon:
    def redact(self, text):
        return "*" * len(text)
