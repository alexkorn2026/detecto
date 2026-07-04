# Detecto v1.0 – Release Notes

**Release-Datum:** 2026-04-11
**Autor:** Alexander Kornbrust
**Lizenz:** MIT

---

## Ueberblick

Version 1.0 markiert den Uebergang von einem monolithischen Skript (1255 Zeilen) zu einem professionellen, modularen Python-Package. Der komplette Code wurde refaktoriert, mit Security-Haertung versehen und umfassend getestet.

## Architektur

Detecto besteht aus 12 Modulen unter `src/detecto/`:

| Modul | Verantwortlichkeit |
|---|---|
| `__init__.py` | VERSION, `__version__` |
| `__main__.py` | Entry-Point (`python -m detecto`) |
| `constants.py` | ANSI-Farben, Excel-Farben, Limits, Trennzeichen |
| `config.py` | `DetectoConfig` Dataclass, `load_config()` |
| `utils.py` | `normalize()`, `find_logfiles()`, `krit_color()` |
| `anonymizer.py` | `Anonymizer`-Klasse mit konfigurierbarem Muster |
| `loaders.py` | Pattern-Laden mit Sicherheitspruefungen |
| `tokenizer.py` | `tokenize()`, `extract_json_fragments()`, `find_field_value()` |
| `analyzer.py` | `LogAnalyzer.analyze()` |
| `formatter.py` | Konsolen-Ausgabe, Farbhervorhebung |
| `exporter.py` | Excel/Log-Export, `ExportContext`, `_SheetBuilder` |
| `cli.py` | `parse_args()`, `main()`, `--verbose` |

## Erkennungstechniken

Drei komplementaere Erkennungstechniken:

- **12 Regexp-Muster**: E-Mail, Versicherungsnummer, Strasse, JWT, SSH/TLS Private Key, Kreditkarte, IBAN, Steuer-ID, Telefonnummer, PLZ, JDBC Connection String
- **11 Field-Muster**: Passwort, Oracle-Passwort, API-Key, Access Token, Refresh Token, Session-ID, Client Secret, DB-Passwort, Reisepass, Diagnose, Geburtsdatum
- **5 String-Kategorien**: Vornamen (3.436), Nachnamen (4.051), Orte (4.502), Diagnosen, Sicherheitsbegriffe

## Security-Haertung

- **Regex DoS Schutz**: `_safe_compile()` mit SIGALRM Timeout (2 Sekunden)
- **Path Traversal Schutz**: `_validate_path()` mit `Path.resolve()` Pruefung
- **CSV/Excel Injection Prevention**: `_sanitize_cell()` escaped Formel-Zeichen (`=`, `+`, `-`, `@`)
- **Memory Begrenzung**: `MAX_HITS_PER_PATTERN = 10.000` verhindert unbegrenztes Wachstum
- **UTF-8 Safety**: Binary Reading mit Warnung bei erstem Non-UTF-8 Byte
- **Config Validation**: `__post_init__()` clamps Werte auf gueltige Bereiche

## Excel-Export

6 Arbeitsblaetter mit Plain-Text-Markierungen (kein Rich Text/XML):

- **Findings** – Ergebnisse mit Kundenbearbeitungs-Spalten (Bearbeiter, Finding, Kommentar)
- **Full** – Detaillierte Logeintraege mit farbiger Hervorhebung (`>>>WERT<<<`, `[FELD:token]`)
- **Tool** – Scan-Informationen (Version, Aufruf, Datum, Statistik)
- **Regexp** – Alle Regexp-Muster
- **Field** – Alle Field-Muster
- **String** – Alle Suchmuster-Kategorien

## Konfiguration

- `detecto.ini` mit Default-Werten fuer alle Parameter
- Kommandozeilen-Parameter ueberschreiben INI-Werte
- Anonymisierungsmuster konfigurierbar (`sss**sss**`, `<redacted>`, etc.)
- Suchtypen einzeln ein-/ausschaltbar (`search_regexp`, `search_feld`, `search_suchmuster`)
- Kritikalitaetsfilter (`--critical N`, Stufen 1-5)

## Kommandozeilen-Parameter

| Parameter | Beschreibung |
|---|---|
| `logdateien` | Log-Datei(en) zum Scannen |
| `--examplecount N` | Anzahl Beispiele pro Fundtyp |
| `--anon` | Beispiele anonymisiert ausgeben |
| `--full` | Log-Zeilen mit farblicher Hervorhebung |
| `--minlen N` | Mindestlaenge fuer Suchmuster-Strings |
| `--critical N` | Nur Findings bis Kritikalitaet N |
| `--showskipped` | Auch Muster ohne Treffer anzeigen |
| `--status` | Zusammenfassung der Suchdaten |
| `--verbose` | Debug-Logging aktivieren |
| `--nocolor` | Farbliche Ausgabe deaktivieren |
| `--logresult [DATEI]` | Ergebnis in Datei speichern |
| `--logresultanon [DATEI]` | Ergebnis anonymisiert speichern |
| `--xlsx [DATEI]` | Excel-Export |
| `--excelanon` | Excel-Werte anonymisieren |

## Tests

69 pytest-Tests in 5 Modulen:

- `test_anonymizer.py` – Pattern Parsing, Redact, Error Handling (7 Tests)
- `test_tokenizer.py` – Tokenisierung, JSON-Fragmente, Field-Werte (12 Tests)
- `test_analyzer.py` – LogAnalyzer: Regexp, Field, String, Stopwords, Security (29 Tests)
- `test_exporter.py` – Excel: Sheets, Marker, CSV Injection (10 Tests)
- `test_loaders.py` – Path Traversal, Regex DoS, Stopwords, File Parsing (11 Tests)

## Packaging

- `pyproject.toml`: setuptools, Entry-Point `detecto`, pytest/ruff/mypy Config
- `Makefile`: `make dist` (ZIP), `make test`, `make clean`, `make lint`
- `detecto_cli.py`: Wrapper fuer Rueckwaertskompatibilitaet
- Minimale Abhaengigkeit: nur `openpyxl` (fuer Excel-Export)

## Unterstuetzte Log-Formate

- Plain-Text: WebSphere, Liberty, Apache, Tomcat, Spring Boot, Kubernetes
- JSON: Liberty JSON-Format (eine JSON-Zeile pro Logeintrag)

## Installation

```bash
# Als pip-Package (empfohlen)
pip install -e .
detecto test.log

# Ohne Installation
python3 detecto_cli.py test.log

# Als Python-Modul
PYTHONPATH=src python3 -m detecto test.log
```

## Voraussetzungen

- Python 3.9+
- `openpyxl` (nur fuer `--xlsx`)

## Folgeversionen

- **v1.1** (2026-04-12) – 6 neue Field-Pattern (17 total), Kreditkarte/IBAN mit Formatierung, 100 Diagnosen, 52 Sicherheitsbegriffe, URL-Credential-Extraktion
- **v1.2** (2026-04-12) – Multiprocessing, parse_json Option, LRU-Cache (2.5-7x Speedup)
- **v1.3** (2026-04-12) – Reverse-Index O(1), Chunk-Parallelisierung, 92 Tests (1.6x Speedup)
- **v1.4** (2026-04-12) – Method-Inlining, ASCII-Fast-Path, lokale Caches (1.4-1.7x Speedup, 360-440k Z/s)
