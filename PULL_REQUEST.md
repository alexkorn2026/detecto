# PR-Titel

Findings 1–42: Sicherheit, Erkennungsqualität, Robustheit & ehrliche Doku (v2.0.0)

---

# PR-Beschreibung (Body)

Behebt die Review-Befunde **1–42** ohne grundlegenden Architekturumbau
(bestehende Pipeline, Ergebnisstruktur und CLI bleiben kompatibel; nur gezielte,
additive Erweiterungen). Version **1.6.1 → 2.0.0** (Major, wegen sicherer
Default-Änderungen, neuem Regexp-Scope-Format und geänderter `parse_json`-Semantik).

## Ergebnis
- ✅ **295 Tests** grün (vorher 126), `ruff check src/` sauber
- ✅ Qualitäts-Benchmark (synthetischer Gold-Datensatz): Precision/Recall/F1 = 1.00
- ✅ Wheel enthält alle Datenfiles, keine JS/Node-Artefakte, läuft nach Installation
  in frischer venv **außerhalb** des Repos
- 4 neue Module: `diagnostics.py`, `regexsafe.py`, `reader.py`, `validators.py`

## Wichtigste Änderungen

**Sicherheit & Korrektheit**
- Laufzeit-Regex-DoS-Timeout (`regex`-Paket), Deaktivierung wiederholt auslösender
  Muster (F1)
- Expliziter Scan-Status complete/partial/failed + Exit-Codes 0/2/3/4/5 (F2)
- Sensible Werte **standardmäßig anonymisiert**, Klartext nur mit
  `--show-sensitive-values`; Reports mit 0600-Rechten (F3)
- Globale Speicher-/Ergebnislimits mit transparenter Zählung (F4)
- Credential-Werte mit `/`/`C:` nicht mehr verworfen; maskierte Werte als eigener,
  niedriger eingestufter Fund (F5)
- Doppelte Pattern-IDs = fataler Konfigurationsfehler (F6)
- Symlink-sicheres Öffnen der Pattern-Dateien (O_NOFOLLOW + fstat) (F41)

**Erkennung**
- Expliziter Regex-Scope `token|line`; robuster Tokenizer (URL/IPv6/JDBC via
  urllib); JSON-Modus `auto` (F8–F10)
- Validatoren: Luhn/Kreditkarte, IBAN Mod 97, Steuer-ID, JWT-Struktur,
  Private-Key-Vollständigkeit, Straßen-Kontext (F11–F17)
- Confidence low/medium/high; technische Begriffe nicht als Namen (F18/F19)

**Korrekte Ausgabe**
- Originalwert + Positionen + Zeilennummer je Fund; deterministische
  Parallelverarbeitung; positionsbasierte Anonymisierung (F7/F20/F24)
- Kontextausschnitt statt ganzer Zeile; gehärtete Excel-Formula-Injection (F23/F25)

**Betrieb**
- Container-bewusster Worker-Cap; Multiprocessing-Schwellen; Encoding-Optionen;
  Umgang mit überlangen Zeilen; Binär-/Pipe-/Symlink-/gz-Behandlung (F21/22/26/27/28)

**Packaging & Konfiguration**
- openpyxl optional (`detecto[excel]`); Supply-Chain (Constraints, CI, CycloneDX-SBOM,
  pip-audit); keine stille CWD-Config; strikte Config-Validierung (F29–F32)
- Reproduzierbare Qualitäts-/Performance-Benchmarks; Property/Fuzz-Tests;
  konsistente Defaults; Packaging-Tests; korrigierte, nicht-absolute Aussagen
  (F33–F40, F42)

## Breaking Changes / Migration
- Klartext benötigt jetzt `--show-sensitive-values` (Default anonym)
- Regexp-Dateien sollten das Scope-Feld ergänzen (Alt-Format lädt mit Warnung)
- `./detecto.ini` wird nur mit `--use-local-config` verwendet
- Ungültige Config-Werte sind standardmäßig Fehler (`--lenient-config` für Altverhalten)
- openpyxl separat: `pip install detecto[excel]`

## Testen
```bash
pip install -e ".[dev]"
pytest -q
python benchmarks/quality_benchmark.py
python -m build && pip install dist/*.whl   # außerhalb des Repos: detecto --status
```

## Hinweis zur Website
Die exakten Text-Ersetzungen für die Produktseite (Klartext, Symlink, „every
input/output/resource", Encoding, Worksheet-Anzahl, Testanzahl, JSON/E-Mail) liegen
in `WEBSITE_TEXT_CHANGES.md`. Details je Finding in
`DETECTO_FINDINGS_1_42_IMPLEMENTATION_REPORT.md`.

## Checkliste
- [x] Alle bestehenden Tests bleiben grün, keine abgeschwächt
- [x] Neue Tests je Finding (Unit/Integration/CLI/Packaging/Parallel/Fuzz/Security)
- [x] Keine `eval`/`exec`/Shell; nur synthetische Testdaten
- [x] README/Changelog/Config-Referenz aktualisiert
- [ ] Website-Texte übernehmen (siehe `WEBSITE_TEXT_CHANGES.md`)
