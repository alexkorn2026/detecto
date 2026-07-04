"""Finding 3: sensitive values are anonymized by default.

Plaintext output requires the explicit --show-sensitive-values flag, which
also emits a warning. Report files are created with restrictive permissions.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from collections import OrderedDict

from detecto.anonymizer import Anonymizer
from detecto.config import DetectoConfig
from detecto.exporter import ExportContext, export_log

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = "Sup3rSecretValue42"


def test_default_config_is_anonymized():
    cfg = DetectoConfig()
    assert cfg.anon is True
    assert cfg.excelanon is True
    assert cfg.show_sensitive_values is False


def _ctx(tmp_path):
    results: OrderedDict = OrderedDict()
    results["Passwort"] = ("field", 1, {
        SECRET: [("t.log", f"password={SECRET}", "password")],
    })
    return ExportContext(
        results=results, example_count=3, critical=5, call_str="t",
        logfiles=["t.log"], line_count=1, duration_text="0 sec",
        regexp=[], field=[], search=[], anonymizer=Anonymizer(),
    )


def test_report_file_permissions_restrictive(tmp_path):
    out = tmp_path / "report.log"
    export_log(str(out), _ctx(tmp_path), anon=True)
    mode = stat.S_IMODE(os.stat(out).st_mode)
    if os.name == "posix":
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def _run_cli(tmp_path, *extra):
    logf = tmp_path / "in.log"
    logf.write_text(f"password={SECRET}\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    return subprocess.run(
        [sys.executable, "-m", "detecto", str(logf), "--nocolor", *extra],
        capture_output=True, text=True, env=env, cwd=REPO,
    )


def test_default_run_redacts_secret(tmp_path):
    proc = _run_cli(tmp_path)
    assert SECRET not in proc.stdout, "plaintext secret leaked by default"


def test_show_sensitive_reveals_and_warns(tmp_path):
    proc = _run_cli(tmp_path, "--show-sensitive-values")
    assert SECRET in proc.stdout, "explicit opt-in should reveal plaintext"
    assert "show-sensitive-values" in proc.stderr.lower() or "warnung" in proc.stderr.lower()
