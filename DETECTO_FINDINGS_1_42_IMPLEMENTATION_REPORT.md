# Detecto – Umsetzungsbericht Findings 1–42

## 1. Zusammenfassung

- **Neue Version:** 1.6.1 → **2.0.0** (Major-Bump wegen sicherer Default-Änderungen,
  neuem Regexp-Dateiformat mit Scope und geänderter `parse_json`-Semantik).
- **Geänderte Dateien:** 49 (Quellcode, Tests, Konfiguration, Doku, CI, Benchmarks).
- **Neue Quellmodule:** `diagnostics.py`, `regexsafe.py`, `reader.py`, `validators.py`.
- **Tests:** von 126 auf **295** erhöht (22 Testdateien), alle grün.
- **Testergebnis:** `pytest` → 295 passed. `ruff check src/` → sauber.
  Reproduzierbarer Qualitäts-Benchmark auf synthetischem Gold-Datensatz:
  Precision/Recall/F1 = 1.00 (Validatoren verwerfen die negativen Fälle korrekt).
- **Bekannte Restgrenzen:** heuristische Erkennung (FP/FN möglich); Chunk-Parallel-
  modus dekodiert weiterhin UTF-8 (Encoding-Optionen gelten für den Standard-Pfad);
  Multiprocessing-Worker-Initializer/Batching nicht implementiert (Schwellen +
  sequentieller Fallback vorhanden); `mypy` konnte in der Sandbox wegen eines
  defekten mypy-2.1-Builds nicht laufen (Type-Hints wurden ergänzt; CI führt mypy
  aus dem `[dev]`-Extra aus).

---

## 2. Änderungen pro Finding

### Finding 1 – Runtime-Regex-DoS-Schutz
Status: umgesetzt
Betroffene Dateien: `regexsafe.py` (neu), `analyzer.py`, `loaders.py`, `constants.py`,
`config.py`, `cli.py`, `pyproject.toml`, `tests/test_regex_timeout.py`
Technische Änderung: Neues Modul `regexsafe` kompiliert Muster mit dem `regex`-Paket
und wendet pro `search`/`finditer` ein Laufzeit-Timeout an. Muster, die
`regex_disable_threshold`-mal auslösen, werden für den Rest des Scans (pro Worker)
deaktiviert. Timeout/Deaktivierung werden im Report ausgewiesen. Der Compile-Test
bleibt als Vorprüfung, ist nicht mehr alleiniger Schutz. Aus Performancegründen wird
das Timeout erst ab `REGEX_TIMEOUT_MIN_LEN` (24) Zeichen angewandt (kurze Tokens
können kein relevantes Backtracking auslösen).
Neue Tests: catastrophic patterns beenden Scan im Zeitrahmen; Timeout + Deaktivierung.
Kompatibilität: `regex` als gekappte Core-Dependency; Fallback auf `re` ohne Timeout.
Restrisiko: ohne `regex`-Paket keine Laufzeit-Timeouts (dokumentiert).

### Finding 2 – Scanstatus & Exit-Codes
Status: umgesetzt
Betroffene Dateien: `diagnostics.py` (neu), `analyzer.py`, `cli.py`, `exporter.py`,
`tests/test_scan_status.py`
Technische Änderung: `ScanStatus` complete/partial/failed aus Dateizählern;
Exit-Codes 0/2/3/4/5; `--continue-on-error`, `--exit-on-findings`; Status in Console,
Log- und Excel-Export.
Neue Tests: Statusableitung, unlesbare/gemischte Dateien, Exit-Code-Mapping.
Restrisiko: keiner wesentlich.

### Finding 3 – Klartext & Website-Aussage
Status: umgesetzt
Betroffene Dateien: `config.py`, `cli.py`, `exporter.py`, `detecto.ini`, `readme.md`,
`WEBSITE_TEXT_CHANGES.md`, `tests/test_sensitive_output.py`
Technische Änderung: Defaults `anon=true`, `excelanon=true`; `--show-sensitive-values`
für Klartext inkl. stderr-Warnung; Reportdateien mit 0600 (POSIX, warn-only sonst).
Neue Tests: Default-Redaktion, expliziter Reveal + Warnung, 0600-Rechte.
Kompatibilität: Verhaltensänderung (Default anonym) – Major-Bump.

### Finding 4 – Globale Speicher-/Ergebnislimits
Status: umgesetzt
Betroffene Dateien: `analyzer.py`, `config.py`, `constants.py`, `diagnostics.py`,
`detecto.ini`, `tests/test_limits.py`
Technische Änderung: Zentrale `_store_hit`-Stelle erzwingt Muster-Wertlimit, Beispiel-
limits pro Wert und global sowie `max_total_findings`; Beispielzeilen werden auf
`max_example_chars` mit Marker gekürzt; alle Verwerfungen gezählt.
Neue Tests: Truncation-Marker, globale/Muster-/Wertlimits, Zähler.

### Finding 5 – Pfad-/Maskierungserkennung
Status: umgesetzt
Betroffene Dateien: `analyzer.py`, `constants.py`, `config.py`, `cli.py`,
`tests/test_credential_masking.py`
Technische Änderung: Nur eindeutige Dateipfade unterdrücken Credential-Werte;
maskierte Werte (`****`, `<redacted>`, `[MASKED]`) werden eigener, niedriger
eingestufter Fund („… (maskiert)") und nie als Secret gespeichert.
Neue Tests: `/MySecret`, `C:verySecret`, diverse Maskierungen, echter Pfad.

### Finding 6 – Doppelte Pattern-IDs
Status: umgesetzt
Betroffene Dateien: `loaders.py`, `cli.py`, `tests/test_duplicate_ids.py`
Technische Änderung: Globale Eindeutigkeit über regexp/field/string; Kollision →
`DuplicatePatternError` mit ID, Typ, Datei, Zeile und Vor-Definition; Exit 2.
`_read_lines` liefert Zeilennummern.
Neue Tests: alle Typkombinationen; mitgelieferte Muster sind eindeutig.

### Finding 7 – Originalwert & Positionen
Status: umgesetzt
Betroffene Dateien: `analyzer.py`, `utils.py`, `formatter.py`, `exporter.py`,
`tests/test_positions_determinism.py`
Technische Änderung: additive 8-Tupel-Beispiele `(datei, zeile, feld, orig_wert,
start, end, zeilennr, confidence)`; `normalize_with_offsets` bildet normalisierte
Positionen auf den Originaltext ab; Phrasen-Funde speichern den Originaltext.
Neue Tests: Offset-Mapping (ß→ss), Phrasen-Originaltext, Positionen.
Restrisiko: Token-/Field-Positionen sind Best-Effort (erste Fundstelle).

### Finding 8 – Expliziter Regex-Scope
Status: umgesetzt
Betroffene Dateien: `loaders.py`, `analyzer.py`, `regexp.csv`, `exporter.py`,
`formatter.py`, `tests/test_regex_scope.py`
Technische Änderung: Format `name::krit::desc::pattern::scope`; `replace()`-Heuristik
entfernt; alle mitgelieferten Muster mit Scope versehen; Alt-Einträge laden mit Default
`line` + Deprecation-Warnung.
Neue Tests: Parsing, Default+Warnung, explizites Routing.

### Finding 9 – Tokenizer-Robustheit
Status: umgesetzt
Betroffene Dateien: `tokenizer.py`, `tests/test_tokenizer_robustness.py`
Technische Änderung: URL-Userinfo/Query via `urllib.parse.urlsplit` (IPv6, keine
gierigen Gruppen), Query-Namen mit `-._[]`, einmaliges Percent-Decoding;
`split_inline_field` trennt nur plausible Identifier (URLs/JDBC/IPv6/Zeiten bleiben).
Neue Tests: URL/IPv6/JDBC/URN/Windows-Pfad, Inline-Feld-Fälle.

### Finding 10 – JSON `auto`
Status: umgesetzt
Betroffene Dateien: `config.py`, `analyzer.py`, `tokenizer.py`, `constants.py`,
`detecto.ini`, `tests/test_json_mode.py`
Technische Änderung: `parse_json = auto|true|false`; `auto` nur bei JSON-artigen
Zeilen; Statistiken Kandidaten/geparst/fehlgeschlagen; Tiefen- und Wertlimits.
Neue Tests: Modus-Entscheidung, Stats, ungültiges/tief verschachteltes JSON.

### Findings 11–13, 16, 17 – Validatoren
Status: umgesetzt
Betroffene Dateien: `validators.py` (neu), `analyzer.py`, `diagnostics.py`,
`regexp.csv`, `tests/test_validators.py`
Technische Änderung: Luhn (11), IBAN Mod 97 + Länderlänge (12), Steuer-ID ISO 7064
MOD 11,10 + Verteilung (13), JWT-Struktur via Base64URL+JSON, ohne Signaturprüfung,
DoS-begrenzt (16), Private-Key-Vollständigkeit header_only/incomplete/complete (17).
Ungültige Kandidaten werden verworfen und gezählt; unvollständige Private Keys landen
in einem eigenen, niedriger eingestuften Slot.
Neue Tests: 35 Validatortests mit ausschließlich synthetischen Daten.

### Finding 14 – Straßenmuster kontextsensitiv
Status: umgesetzt
Betroffene Dateien: `validators.py`, `analyzer.py`, `tests/test_validators.py`
Technische Änderung: `street_status` → drop (kleine Ausschlussliste) / high (Hausnummer
oder Adressfeld) / low (bloßes Suffix). Low-Confidence-Treffer in eigenem Slot (Info).
Neue Tests: Speicherplatz/Arbeitsplatz/Fluchtweg → drop; Hauptstraße 12/Rheinufer 5/
street= → high; Hauptstraße ohne Kontext → low.

### Finding 15 – E-Mail-Erkennung & Doku
Status: umgesetzt (dokumentativ)
Betroffene Dateien: `readme.md`, `WEBSITE_TEXT_CHANGES.md`
Technische Änderung: Bestehendes Muster deckt Plus-Adressierung, Subdomains, lange
TLDs und Punycode bereits ab (verifiziert). Aussagen präzisiert: keine RFC-Garantie,
keine absoluten Formulierungen.
Restrisiko: keine vollständige RFC-Erkennung (dokumentiert).

### Findings 18/19 – Confidence & minlen-Absicherung
Status: umgesetzt
Betroffene Dateien: `analyzer.py`, `constants.py`, `formatter.py`,
`benchmarks/quality_benchmark.py` (neu), `tests/test_confidence_quality.py`
Technische Änderung: Confidence low/medium/high je Fund; String-Namen/Orte = low,
medium bei Personen-/Adresskontext; validierte Regex/Field = high. Technische Begriffe
(`main/root/test/…`) werden nicht als Namen gemeldet. Reproduzierbarer Qualitäts-
Benchmark (Precision/Recall/F1).
Neue Tests: Confidence-Stufen, Tech-Term-Unterdrückung, Benchmark.

### Findings 20/24 – Determinismus & positionsbasierte Anonymisierung
Status: umgesetzt
Betroffene Dateien: `analyzer.py`, `formatter.py`, `exporter.py`,
`tests/test_positions_determinism.py`
Technische Änderung: geordnetes `imap` (statt `imap_unordered`) + `_finalize`-Sortierung
→ identische Ergebnisse für 1/2/4 Worker; Hervorhebung/Anonymisierung über exakten
Originalwert + Position, überlappende/mehrfache Treffer per Span-Merge, keine
Sub-Wort-Anonymisierung.
Neue Tests: Worker-Determinismus, Positions-Highlight, Duplikate/Substrings.

### Findings 21/22 – Worker-Cap & Multiprocessing-Schwellen
Status: umgesetzt (22 teilweise)
Betroffene Dateien: `analyzer.py`, `config.py`, `constants.py`, `detecto.ini`,
`tests/test_perf_and_excel.py`
Technische Änderung: container-bewusste CPU-Erkennung (sched_getaffinity + cgroup v2 +
cpu_count), Auto-Cap `max_auto_workers` (8); Multiprocessing nur oberhalb
`multiprocessing_min_total_bytes`/`_file_count`, sonst sequentiell; erkannte/limitierte/
genutzte Worker geloggt.
Restrisiko (22): Worker-Initializer und Small-File-Batching nicht umgesetzt – die
Muster werden weiterhin pro Task gepickelt; durch Schwellen selten relevant.

### Finding 23 – Kontextausschnitt statt ganzer Zeile
Status: umgesetzt
Betroffene Dateien: `analyzer.py`, `config.py`, `cli.py`, `detecto.ini`,
`tests/test_perf_and_excel.py`
Technische Änderung: gespeichert wird ein `context_chars_before/after`-Fenster um den
Treffer mit Kürzungsmarkern; `--full` speichert ganze Zeilen nur zusammen mit
`--show-sensitive-values`.
Restrisiko: mehrere Secrets im selben Fenster werden nur für den betrachteten Treffer
positionsbasiert behandelt; das schmale Fenster begrenzt jedoch die Leckage.

### Finding 25 – Excel-Formula-Injection
Status: umgesetzt
Betroffene Dateien: `exporter.py`, `tests/test_perf_and_excel.py`
Technische Änderung: erstes wirksames Zeichen nach Whitespace/Tab/CR/LF prüfen auf
`= + - @`; Steuerzeichen entfernen; Zelllänge begrenzen; als Text speichern
(verhindert Auto-Hyperlinks).
Neue Tests: `=1+1`, ` +SUM`, `\t=HYPERLINK`, `\r@SUM`, `-2+3`, Steuerzeichen, Länge.

### Findings 26/27/28 – Encoding, überlange Zeilen, Spezial-/Binär-/gz-Dateien
Status: umgesetzt
Betroffene Dateien: `reader.py` (neu), `analyzer.py`, `config.py`, `cli.py`,
`detecto.ini`, `tests/test_reader.py`
Technische Änderung: `--encoding`/`--encoding-errors`; `auto` = BOM-Erkennung + UTF-8-
Validierung + windows-1252-Fallback; Statistiken; strict → partial. `max_line_bytes` +
`oversized_line_policy` mit begrenztem Zeilenleser (keine unbegrenzte Pufferung);
korrekte Zeilennummern. Nur reguläre Dateien; Symlinks/FIFOs/Devices/Binär überspringen
und melden; `.gz` streamend mit Dekompressions-Byte-Budget.
Neue Tests: 12 Reader-Tests (Encoding, oversized, binär/symlink/FIFO/gz-Bombe).
Restrisiko: Chunk-Parallelmodus nutzt weiterhin UTF-8-Dekodierung.

### Findings 29–32 – Excel optional, Supply-Chain, Config-Priorität, strikte Config
Status: umgesetzt
Betroffene Dateien: `pyproject.toml`, `exporter.py`, `cli.py`, `config.py`,
`constraints.txt` (neu), `.github/workflows/supply-chain.yml` (neu),
`tests/test_config_precedence.py`
Technische Änderung: openpyxl als `[excel]`-Extra + klare Fehlermeldung; Constraints +
CI (Build, Wheel-Prüfung, Clean-Venv-Install, CycloneDX-SBOM, pip-audit); keine stille
CWD-Config (Priorität `--config` > `--use-local-config` > Repo > Paket) mit Warnung +
Hash; strikte Config-Validierung (unbekannte Keys/Enums/Ints → Fehler),
`--lenient-config`, `--print-effective-config` (ohne sensible Werte).
Neue Tests: Priorität, strict/lenient, Effective-Config-Redaktion, Excel-Extra.

### Findings 33–40 – Doku, Benchmarks, Worksheets, Defaults, Packaging
Status: umgesetzt
Betroffene Dateien: `benchmarks/*` (neu), `readme.md`, `WEBSITE_TEXT_CHANGES.md`,
`config.py`, `regexp.csv`, `tests/test_property_fuzz.py`,
`tests/test_worksheets_defaults.py`, `tests/test_packaging.py`
Technische Änderung: (33) Testanzahl nicht mehr als Qualitätsbeleg, Verweis auf
Benchmark; (34) reproduzierbarer Perf-Benchmark mit Testbedingungen; (35) hypothesis-
Property/Fuzz/Differential-Tests mit Invarianten; (36) 5 Standard-Worksheets + optional
`Full` (getestet); (37) IBAN-Kritikalität 2 vereinheitlicht; (38/39) Code als Single
Source of Truth (examplecount 10, minlen 4) + Konsistenztest; (40) verifiziertes Wheel
inkl. Clean-Venv-Lauf außerhalb des Repos, `--status` zeigt Datei-Hashes.
Neue Tests: Property/Fuzz, Worksheets/Defaults, Packaging.

### Findings 41/42 – Symlink-Sicherheit & absolute Versprechen
Status: umgesetzt
Betroffene Dateien: `loaders.py`, `readme.md`, `WEBSITE_TEXT_CHANGES.md`, `changelog.md`,
`tests/test_symlink_safety.py`
Technische Änderung: Pattern-Dateien mit `O_NOFOLLOW`+`O_NONBLOCK` öffnen und per
`fstat` als reguläre Datei prüfen (TOCTOU-Fenster geschlossen, Symlinks/FIFOs
abgelehnt); absolute Sicherheitsaussagen durch präzise, überprüfbare ersetzt.
Neue Tests: Symlink/FIFO abgelehnt, reguläre Datei lädt.
Restrisiko: Verzeichnis-Symlinks/Races nicht vollständig eliminierbar (dokumentiert).

---

## 3. Neue/geänderte Konfigurationswerte

| Name | Typ | Default | Werte | Beschreibung |
|---|---|---|---|---|
| anon | bool | true | true/false | Anonymisierung (Finding 3) |
| excelanon | bool | true | true/false | Excel-Anonymisierung |
| show_sensitive_values | bool | false | true/false | Klartext-Opt-in |
| parse_json | str | auto | auto/true/false | JSON-Modus (Finding 10) |
| regex_timeout_ms | int | 100 | ≥0 | Laufzeit-Regex-Timeout |
| regex_disable_threshold | int | 5 | ≥1 | Deaktivierungsschwelle |
| max_line_bytes | int | 1048576 | ≥1024 | Byte-Limit pro Zeile |
| max_example_chars | int | 4000 | ≥0 | Beispiel-Kürzung |
| max_total_findings | int | 100000 | ≥1 | globales Fund-Limit |
| max_total_examples | int | 20000 | ≥1 | globales Beispiel-Limit |
| max_values_per_pattern | int | 10000 | ≥1 | Werte je Muster |
| max_examples_per_value | int | 100 | ≥1 | Beispiele je Wert |
| masked_value_criticality | int | 4 | 1–5 | Kritikalität maskierter Werte |
| max_auto_workers | int | 8 | ≥1 | Auto-Worker-Cap |
| multiprocessing_min_total_bytes | int | 5242880 | ≥0 | MP-Schwelle Bytes |
| multiprocessing_min_file_count | int | 4 | ≥1 | MP-Schwelle Dateien |
| context_chars_before/after | int | 120 | ≥0 | Kontextfenster |
| oversized_line_policy | str | truncate | truncate/skip/fail | Umgang überlange Zeilen |
| encoding | str | auto | auto/utf-8/… | Datei-Encoding |
| encoding_errors | str | replace | strict/replace/ignore | Decodierungsfehler |
| follow_input_symlinks | bool | false | true/false | Eingabe-Symlinks folgen |

## 4. CLI-Änderungen

Neue Optionen: `--show-sensitive-values`, `--continue-on-error`, `--exit-on-findings`,
`--encoding`, `--encoding-errors`, `--config`, `--use-local-config`,
`--lenient-config`, `--print-effective-config`.
Exit-Codes: 0 vollständig, 2 Konfig/Aufruf, 3 partiell, 4 fehlgeschlagen, 5 intern.
Beispiele: `detecto app.log`; `detecto "*.log" --encoding windows-1252`;
`detecto app.log --show-sensitive-values --xlsx report.xlsx`; `detecto --status`.

## 5. Sicherheitsverbesserungen
Laufzeit-Regex-Timeout; sichere Defaults (Anonymisierung); 0600-Reportrechte;
globale Limits & überlange-Zeilen-Schutz; Excel-Formula-Injection-Härtung; strikte
Config; keine stille CWD-Config; symlink-sicheres Öffnen der Pattern-Dateien;
Dekompressions-Bomben-Budget; kein `eval`/`exec`/Shell; nur synthetische Testdaten.

## 6. Dokumentationskorrekturen
README (Testanzahl, Sicherheit/Grenzen, Benchmarks, Distribution); `changelog.md`
(v2.0.0); `WEBSITE_TEXT_CHANGES.md` mit exakten Ersetzungen für die Produktseite
(Klartext, Symlink, „every input/output/resource", Encoding, Worksheet-Anzahl,
Testanzahl, JSON/E-Mail).

## 7. Test- und Benchmark-Ergebnisse
- `pytest`: 295 passed. `ruff check src/`: sauber.
- Quality-Benchmark (synthetisch): Precision/Recall/F1 = 1.00.
- Perf-Benchmark: reproduzierbar mit ausgewiesenen Testbedingungen.
- Packaging: Wheel enthält alle Datenfiles, keine JS/Node-Artefakte, läuft nach
  Installation in frischer venv außerhalb des Repos (`detecto --status`).

## 8. Bekannte verbleibende Grenzen
Heuristische Erkennung (FP/FN); Chunk-Parallelmodus ohne Encoding-Optionen; MP-Worker-
Initializer/Batching offen; mypy in der Sandbox nicht lauffähig (defekter Build).

## 9. Migrationshinweise
- Klartext benötigt jetzt `--show-sensitive-values` (Default anonym).
- Regexp-Dateien sollten das Scope-Feld ergänzen (Alt-Format lädt mit Warnung).
- `parse_json` akzeptiert weiterhin true/false, empfohlen ist `auto`.
- Eine `./detecto.ini` wird nur mit `--use-local-config` verwendet.
- Ungültige Config-Werte sind standardmäßig Fehler (`--lenient-config` für Altverhalten).
- openpyxl separat installieren: `pip install detecto[excel]`.
