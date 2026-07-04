"""Findings 29-32: excel optional, config precedence, strict config."""
from __future__ import annotations

from pathlib import Path

import pytest

from detecto.cli import _print_effective_config, _resolve_base_dir
from detecto.config import ConfigError, DetectoConfig, load_config

# --- Finding 29: openpyxl optional -----------------------------------------

def test_pyproject_excel_extra_and_no_hard_openpyxl():
    root = Path(__file__).resolve().parent.parent
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "excel = [" in text
    # openpyxl must not be a hard runtime dependency
    assert 'dependencies = ["regex' in text.replace("'", '"') or "regex" in text
    assert "openpyxl" not in text.split("[project.optional-dependencies]")[0]


# --- Finding 31: config precedence -----------------------------------------

def test_cwd_not_trusted_by_default(tmp_path, monkeypatch):
    (tmp_path / "detecto.ini").write_text("[defaults]\nminlen=9\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    base, source = _resolve_base_dir(None, use_local=False)
    assert source != "local"  # the stray cwd ini is ignored


def test_use_local_config_opt_in(tmp_path, monkeypatch):
    (tmp_path / "detecto.ini").write_text("[defaults]\nminlen=9\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    base, source = _resolve_base_dir(None, use_local=True)
    assert source == "local"
    assert base == tmp_path


def test_explicit_config_wins(tmp_path):
    cfg = tmp_path / "detecto.ini"
    cfg.write_text("[defaults]\nminlen=7\n", encoding="utf-8")
    base, source = _resolve_base_dir(str(cfg), use_local=False)
    assert source == "explicit"
    assert base == tmp_path


# --- Finding 32: strict config ---------------------------------------------

def test_strict_rejects_unknown_key(tmp_path):
    (tmp_path / "detecto.ini").write_text(
        "[defaults]\nbogus_key = 5\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_config(tmp_path, strict=True)


def test_strict_rejects_bad_enum(tmp_path):
    (tmp_path / "detecto.ini").write_text(
        "[defaults]\nprefilter = wat\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_config(tmp_path, strict=True)


def test_strict_rejects_bad_int(tmp_path):
    (tmp_path / "detecto.ini").write_text(
        "[defaults]\nminlen = notanumber\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_config(tmp_path, strict=True)


def test_lenient_allows_unknown_key(tmp_path):
    (tmp_path / "detecto.ini").write_text(
        "[defaults]\nbogus_key = 5\nminlen = 6\n", encoding="utf-8"
    )
    cfg = load_config(tmp_path, strict=False)
    assert cfg.minlen == 6  # loaded despite the unknown key


def test_shipped_ini_passes_strict():
    from importlib.resources import files
    data = Path(str(files("detecto") / "data"))
    cfg = load_config(data, strict=True)
    assert isinstance(cfg, DetectoConfig)


def test_effective_config_redacts_secret(capsys, tmp_path):
    cfg = DetectoConfig(anon_muster="sss**sss")
    _print_effective_config(cfg, tmp_path, "package")
    out = capsys.readouterr().out
    assert "anon_muster = <redacted>" in out
    assert "sss**sss" not in out
