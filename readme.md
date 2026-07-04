# Detecto

[![tests](https://github.com/alexkorn2026/detecto/actions/workflows/tests.yml/badge.svg)](https://github.com/alexkorn2026/detecto/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Detecto** scannt Log-Dateien (Websphere/Liberty) nach kritischen und personenbezogenen Daten und identifiziert diese.

> Schnell ausprobieren: `detecto synthetic_logs/kritische_findings_websphere_application.log`
> — synthetische Beispiel-Logs liegen in [`synthetic_logs/`](synthetic_logs/).

## Beschreibung

Detecto liest Logdateien ein, zerlegt jede Zeile in einzelne Token und prueft diese gegen drei Arten von Suchmustern:

- **Regexp** (regulaere Ausdruecke) aus `regexp.csv` - z.B. E-Mail-Adressen, Versicherungsnummern, JWTs, Kreditkarten, IBANs, JDBC-Strings
- **Field** (Feld-Erkennung) aus `field.csv` - erkennt kritische Feldnamen (z.B. password, Kennwort, api_key) und erfasst den Wert im naechsten Token
- **String-Muster** aus CSV-Dateien (referenziert ueber `suchmuster.csv`) - z.B. Vornamen, Nachnamen, Ortsnamen, Diagnosen, Sicherheitsbegriffe

Fuer jeden Erkennungstyp koennen Stopwort-Listen gepflegt werden, um False Positives zu reduzieren. Alle Einstellungen sind ueber `detecto.ini` konfigurierbar.

## Voraussetzungen

- Python 3.9 oder hoeher
- `openpyxl` (nur fuer Excel-Export mit `--xlsx`)

## Installation

```bash
# Option 1: Als pip-Package installieren (empfohlen)
pip install -e .            # aus dem Quellordner/entpackten ZIP
# oder: pip install dist/detecto_1.6.1.zip
detecto test.log            # funktioniert aus jedem Verzeichnis

# Option 2: Entpacktes ZIP / Quellordner ohne Installation
python3 detecto_cli.py test.log

# Option 3: Als Python-Modul
PYTHONPATH=src python3 -m detecto test.log
```

Musterdateien-Aufloesung: Detecto nutzt (1) das aktuelle Verzeichnis, wenn dort
eine `detecto.ini` liegt, sonst (2) den Quellordner, sonst (3) die installierten
Package-Daten (`src/detecto/data/`). Nach `pip install` funktioniert `detecto`
damit ohne weitere Dateien; eigene Muster: `detecto.ini` + CSVs ins
Arbeitsverzeichnis legen.

## Projektstruktur

```
Detecto/
  detecto_cli.py              Wrapper (python3 detecto_cli.py test.log)
  detecto.ini                 Konfiguration und Default-Werte
  pyproject.toml              Packaging, pytest-Config, Entry-Point
  Makefile                    make dist / make test / make clean
  src/
    detecto/                  Python-Package (12 Module)
      __init__.py             VERSION, __version__
      __main__.py             python -m detecto
      constants.py            Centralized constants (colors, limits, delimiters)
      config.py               DetectoConfig dataclass, load_config()
      utils.py                normalize(), find_logfiles(), krit_color()
      anonymizer.py           Anonymizer class
      loaders.py              load_regexp/field_patterns/search_patterns/stopwords
      tokenizer.py            tokenize(), extract_json_fragments(), find_field_value()
      analyzer.py             LogAnalyzer.analyze()
      formatter.py            print_header/status/results(), highlight()
      exporter.py             export_xlsx/log(), ExportContext, _SheetBuilder
      cli.py                  parse_args(), main(), --verbose
  tests/                      126 pytest tests
    test_anonymizer.py        Anonymizer: patterns, redact, error handling
    test_tokenizer.py         Tokenization, JSON fragments, field values
    test_analyzer.py          LogAnalyzer: regexp, field, string, stopwords, security, chunks
    test_exporter.py          Excel export: sheets, markers, CSV injection
    test_loaders.py           Path traversal, regex DoS, stopwords
    test_performance_smoke.py Performance smoke tests (50k lines)
  regexp.csv                  Regulaere Ausdruecke (35 Muster)
  field.csv                   Field-Muster (120 Muster)
  suchmuster.csv              Index-Datei fuer String-Suchmuster
  suchmuster/                 Suchmuster-CSV-Dateien
    vornamen.csv              Deutsche Vornamen
    nachnamen.csv             Deutsche Nachnamen
    orte.csv                  Deutsche Ortsnamen
    diagnosen.csv             Medizinische Begriffe
    sicherheitsbegriffe.csv   Sicherheitsrelevante Begriffe
    verschlusssachen.csv      VS-Einstufungen (VS-NfD, ...)
    sperrvermerke.csv         Sperrvermerke/Auskunftssperren
  stopword_regexp.txt         Stopwoerter fuer Regexp-Erkennung
  stopword_field.txt          Stopwoerter fuer Field-Erkennung
  stopword_suchmuster.txt     Stopwoerter fuer String-Erkennung
  LICENSE                     MIT-Lizenz
  readme.md                   Diese Datei
  changelog.md                Aenderungshistorie
  firststeps.md               Schnelleinstieg
  prompt_documentation.md     Prompt-Dokumentation
```

## Erkennungstechniken

### [regexp] - Regulaere Ausdruecke (35 Muster)

Jedes Token wird gegen die Muster in `regexp.csv` geprueft. Muster, die Whitespace
enthalten (`\s` oder Leerzeichen), werden automatisch **zeilenbasiert** geprueft -
z.B. `65 170839 J 008` (VSNR amtlich), IBAN/Kreditkarte mit Leerzeichen,
`STRENG GEHEIM`, SSH-Key-Header.

Aktuelle Muster u.a.: E-Mail, Rentenversicherungsnummer (kompakt + formatiert),
Krankenversichertennummer, Personalausweis-Nr., Strasse, JWT, SSH/TLS Private Key,
Kreditkarte, IBAN, BIC, Steuer-ID, USt-IdNr., Handelsregister-Nr., Kindergeld-Nr.,
Telefonnummer, PLZ, JDBC, IPv4 (oeffentlich + RFC1918), MAC, IMEI, Kfz-Kennzeichen,
AWS/Azure/GitHub/Slack-Keys, Lizenzschluessel, VS-/NATO-/EU-Einstufungen,
SG-Aktenzeichen, Source-Code-URLs.

Format in `regexp.csv`: `name::kritikalitaet::beschreibung::regexp`

### [field] - Feld-Erkennung (120 Muster)

Erkennt kritische Feldnamen und erfasst den Wert im **naechsten Token** (oder per
konfiguriertem Offset). `key:value` innerhalb eines Tokens (z.B. `RVNR:65170839J008`,
`"password":"x"`) wird inline zerlegt. Pfade, Dateinamen und Sternchen-Folgen werden
automatisch ignoriert.

Abgedeckte Bereiche (Datenarten-Erkennungsmatrix 1.6.0): Credentials/Keys/Tokens,
Art.-9-DSGVO-Kategorien (Religion, Gesundheit, Biometrie, ...), Sozialdaten (SGB),
RV-spezifische Felder (Entgeltpunkte, Rentenart, DEUEV, Kontenklaerung, ...),
Personalaktendaten, besonderer Schutzbedarf (Zeugenschutz, Sperrvermerke),
Betriebspruef-/Compliance-Daten, Verzeichnisdienste, Geo-/Bewegungsdaten u.v.m.

Format in `field.csv`: `name::kritikalitaet::beschreibung::regexp[::offset]`

### [string] - String-Muster (7 Kategorien)

Jedes Token wird case-insensitive und umlaut-normalisiert gegen die Werte aus den
Suchmuster-CSV-Dateien geprueft.

Aktuelle Kategorien: Vornamen, Nachnamen, Orte, Diagnosen, Sicherheitsbegriffe,
Verschlusssachen (Krit. 1), Sperrvermerke (Krit. 1).

Format in `suchmuster.csv`: `name::kritikalitaet::dateiname.csv`

## Unterstuetzte Log-Formate

- **Plain-Text-Logs** - Standard Websphere/Liberty Logs, Apache, Tomcat, Spring Boot
- **JSON-Logs** - Liberty JSON-Format (eine JSON-Zeile pro Logeintrag)

## Parameter

| Parameter                 | Beschreibung                                                    |
|---------------------------|-----------------------------------------------------------------|
| `logdateien`              | Log-Datei(en) zum Scannen (z.B. `test.log`, `*.log`)           |
| `--examplecount N`        | Anzahl Beispiele pro Fundtyp (Standard: 3)                     |
| `--anon`                  | Beispiele anonymisiert ausgeben                                 |
| `--full`                  | Log-Zeilen der Findings mit farblicher Hervorhebung anzeigen   |
| `--minlen N`              | Mindestlaenge fuer Suchmuster-Strings (Standard: 5, Minimum: 2)|
| `--critical N`            | Nur Findings bis Kritikalitaet N anzeigen (1-5, Standard: 5)  |
| `--showskipped`           | Zeigt auch Muster ohne Treffer an (`<nothing found>`)         |
| `--status`                | Zusammenfassung der geladenen Suchdaten und INI-Defaults       |
| `--verbose`               | Debug-Logging aktivieren (JSON, Stopwords, Pfade)             |
| `--nocolor`               | Deaktiviert die farbliche Ausgabe komplett                     |
| `--logresult [DATEI]`     | Ergebnis (nicht anonymisiert) in Datei speichern               |
| `--logresultanon [DATEI]` | Ergebnis anonymisiert in Datei speichern                       |
| `--xlsx [DATEI]`          | Findings als Excel-Datei exportieren                           |
| `--excelanon`             | Werte in der Excel-Datei anonymisieren                         |
| `--help`                  | Hilfe anzeigen                                                 |

## Kritikalitaetsstufen

| Stufe | Label    | Farbe    | Beschreibung                                          |
|-------|----------|----------|-------------------------------------------------------|
| 1     | kritisch | Rot      | Sofortiger Handlungsbedarf (Passwoerter, Keys, Tokens)|
| 2     | hoch     | Rot      | Hohes Risiko (IBAN, Steuer-ID, JDBC, Session-IDs)     |
| 3     | mittel   | Gelb     | Schuetzenswerte Daten (Reisepass, Diagnosen, Geburtsdatum) |
| 4     | niedrig  | Standard | Personenbezogene Daten (E-Mail, Telefon, Namen, Orte) |
| 5     | info     | Standard | Informativ, geringes Risiko                           |

Mit `--critical=2` werden nur kritische und hohe Findings angezeigt:
```bash
detecto server.log --critical=2
```

## Excel-Export

```bash
# Findings als Excel exportieren
detecto server.log --xlsx

# Mit Full-Sheet (Logeintraege mit farbiger Hervorhebung)
detecto server.log --xlsx --full

# Excel anonymisiert
detecto server.log --xlsx --excelanon
```

Die Excel-Datei enthaelt folgende Arbeitsblaetter:
- **Findings** - Ergebnisse mit Spalten fuer Kundenbearbeitung (Bearbeiter, Finding, Kommentar)
- **Full** (nur mit `--full`) - Detaillierte Logeintraege (7 Spalten). Gefundener Wert mit rotem Hintergrund, Feld mit gruenem Hintergrund. Treffer im Logeintrag als `>>>WERT<<<` und `[FELD:token]` markiert
- **Tool** - Scan-Informationen (Version, Aufruf, Datum, Statistik)
- **Regexp** - Alle Regexp-Muster
- **Field** - Alle Field-Muster
- **String** - Alle Suchmuster-Kategorien

## Konfigurationsdatei (detecto.ini)

```ini
[defaults]
examplecount = 10
minlen = 4
critical = 5
anon = false
full = false
nocolor = false
showskipped = false

# Anonymisierungsmuster: s=Original, */x=Stern, <redacted>=komplett ersetzen
anon_muster = sss**sss**sss**

# Suchen ein-/ausschalten
search_feld = on
search_regexp = on
search_suchmuster = on

# Fortschrittsanzeige (Sekunden zwischen Updates, 0 = deaktiviert)
refresh_status = 5

# JSON-Parsing in Logs (true = JSON-Fragmente erkennen, false = schneller)
parse_json = false

# Parallele Worker (0 = auto/cpu_count, 1 = single-process)
workers = 1

# Pre-Filter (off = kein Filter, regexp_field = nur regexp+field, all = alles)
# off empfohlen: all/regexp_field koennen Field-Findings ohne Marker verlieren
prefilter = off

# Max. Beispielzeilen pro gefundenem Wert (Speicheroptimierung)
max_examples = 100

[files]
regexp = regexp.csv
field = field.csv
suchmuster = suchmuster.csv
suchmuster_verzeichnis = suchmuster
stopword_regexp = stopword_regexp.txt
stopword_field = stopword_field.txt
stopword_suchmuster = stopword_suchmuster.txt
```

## Anonymisierungsmuster

Das Muster wird in `detecto.ini` unter `anon_muster` konfiguriert:

| Muster | Beispiel `amelie.hofmann@beispiel.de` |
|---|---|
| `sss**sss**sss**` | `ame**e.h**man**bei**iel**e` |
| `ssss****ss**` | `amel****of**nn@b****ie**de` |
| `ssssxxxxssxx` | `amel****of**nn@b****ie**de` |
| `<redacted>` | `<redacted>` |

- `s` = Originalzeichen beibehalten
- `*` oder `x` = durch Stern ersetzen
- `<redacted>` = kompletter String wird durch `<redacted>` ersetzt

## Farbschema (Konsole)

| Element           | Farbe       |
|-------------------|-------------|
| `[regexp]`        | Hellgruen   |
| `[field]`         | Hellgelb    |
| `[string]`        | Hellgruen   |
| Feldnamen         | Hellgelb    |
| Feld-Token (full) | Dunkelgruen |
| Treffer (full)    | Rot         |
| `[kritisch/hoch]` | Rot         |
| `[mittel]`        | Gelb        |

Farben deaktivieren: `--nocolor`

## Stopwort-Listen

| Datei                     | Gilt fuer        | Beispiel                              |
|---------------------------|------------------|---------------------------------------|
| `stopword_regexp.txt`     | Regexp-Treffer   | Woerter, die faelschlich matchen      |
| `stopword_field.txt`      | Field-Werte      | `and`, `for`, `WITH`, `message`, ...  |
| `stopword_suchmuster.txt` | String-Treffer   | Woerter, die auch Alltagswoerter sind |

## Eigene Suchmuster hinzufuegen

### Neuen Regexp hinzufuegen

In `regexp.csv`: `name::kritikalitaet::beschreibung::regexp`

### Neues Field-Muster hinzufuegen

In `field.csv`: `name::kritikalitaet::beschreibung::regexp[::offset]`

### Neues String-Suchmuster hinzufuegen

1. CSV-Datei in `suchmuster/` erstellen
2. In `suchmuster.csv` eintragen: `name::kritikalitaet::dateiname.csv`

## Tests

```bash
# Mit pytest (empfohlen)
PYTHONPATH=src python3 -m pytest tests/ -v

# Oder mit make
make test
```

126 Tests in 7 Modulen (inkl. `test_regressions.py` fuer die Review-Befunde):
- `test_anonymizer.py` – Pattern parsing, redact, error handling (7 Tests)
- `test_tokenizer.py` – Tokenization, JSON fragments, field values (12 Tests)
- `test_analyzer.py` – LogAnalyzer: regexp, field, string, stopwords, paths, UTF-8, limits, config, chunks (42 Tests)
- `test_exporter.py` – Excel: sheets, markers, CSV injection (10 Tests)
- `test_loaders.py` – Path traversal, regex DoS, stopwords, file parsing (14 Tests)
- `test_performance_smoke.py` – Performance smoke tests mit 50k synthetischen Zeilen (4 Tests)

## Distribution

```bash
make dist    # Erstellt dist/detecto_1.6.1.zip
make clean   # Bereinigt dist/
```

## Lizenz

MIT License - Copyright (c) 2026 Alexander Kornbrust
