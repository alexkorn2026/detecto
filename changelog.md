# Detecto - Changelog

## v1.6.1 (2026-07-04) – Review-Korrekturen (externes Grok-Audit) + Packaging

### Erkennungs-Fixes (2. Review-Runde)
- **JSON-Keys bei parse_json=true**: `{"password":"Secret123"}` verlor den Feldnamen-Kontext (nur Values wurden extrahiert). Der Tokenizer erzeugt jetzt zusaetzlich synthetische `key:value`-Tokens (`extract_json_pairs`) - Field-Erkennung funktioniert in beiden JSON-Modi.
- **Mehrwort-Suchmuster**: Eintraege mit Leerzeichen (z.B. `Multiple Sklerose`, `Morbus Crohn`, `Bergisch Gladbach`) konnten tokenbasiert nie matchen. Sie werden jetzt zeilenbasiert (normalisiert, mit Wortgrenzen-Pruefung) gesucht; die schnelle Einwort-Suche bleibt unveraendert. Beispiele in diagnosen.csv/orte.csv ergaenzt.
- **AzureAccountKey**: Pattern enthielt `=` und war tokenbasiert tot (`=` ist Separator). Regexps mit `=` (ausserhalb von Lookarounds) laufen jetzt automatisch zeilenbasiert.
- **InterneIP**: matchte ungueltige Adressen wie `10.999.999.999` - jetzt gueltige Oktett-Gruppen wie beim IPv4-Pattern.
- **Regexp-Findings speichern den Match statt des Tokens**: `contact=<alice@example.com>` liefert jetzt `alice@example.com` (m.group(0)), nicht den Token mit Klammern. Lizenzschluessel-Pattern von Ankern auf Lookarounds umgestellt (findet Keys auch in Quotes).
- **Path-Traversal-Check gehaertet**: `startswith`-Prefix-Vergleich liess `/x/baseevil` fuer Base `/x/base` passieren - jetzt `Path.relative_to()`.
- **Defekte detecto.ini crasht nicht mehr**: `configparser.Error` (z.B. MissingSectionHeaderError) wird abgefangen, Warnung + Defaults.

### Packaging / Build
- **0-Byte `detecto_cli.py` im Release-ZIP behoben**: Der Quell-Wrapper war intakt (640 Bytes), aber ein still fehlgeschlagenes `cp` im `make dist` hinterliess eine leere Kopie im ZIP. `make dist` bricht jetzt bei cp-Fehlern ab, prueft alle kopierten Dateien auf Nicht-Leere und verifiziert `detecto_cli.py` direkt im fertigen ZIP.
- **`pip install dist/detecto_<version>.zip` funktioniert**: Musterdateien werden als Package-Daten (`src/detecto/data/`, synchronisiert via `make datasync`) mitinstalliert. Pfadaufloesung: cwd (mit detecto.ini) > Quellordner > installierte Package-Daten (importlib.resources). `detecto --status` laeuft damit aus jedem Verzeichnis.

### Doku
- Veraltete `python3 detecto.py`-Aufrufe entfernt (readme, Excel-Export im Tool-Sheet/Log-Export), doppelte `--verbose`-Zeile aus Parametertabelle entfernt, Installationshinweise fuer entpacktes ZIP und pip-Package vereinheitlicht, Testanzahl aktualisiert.

### Geprueft und widerlegt (keine Bugs)
- **"key=value wird nicht erkannt"**: Falsch - `=` ist Token-Separator, `password=SuperSecret123` wird in zwei Tokens zerlegt und der Wert per Lookahead gefunden. Empirisch verifiziert, Regression-Tests ergaenzt (`TestInlineKeyValue`, 4 Tests).
- **"detecto_cli.py ist leer"**: Teilweise - die Quelldatei war nie leer, aber das Release-ZIP enthielt eine 0-Byte-Kopie (siehe Packaging-Fix oben).

### Fixes
- **Duplicate-Name-Warnung praezisiert**: Text behauptete "findings will be merged" - korrekt ist: Hits landen in einem Slot, aber Typ/Kritikalitaet des zuletzt registrierten Musters gewinnt. Warnung empfiehlt jetzt Umbenennen.
- **stopword_suchmuster.txt befuellt** (war leer): streng/ernst/stark - deutsche Woerter, die mit Nachnamen kollidieren (z.B. "STRENG GEHEIM" meldete Nachname "Streng"). Bewusst minimal gehalten: jedes Stopwort ist ein potenzielles False Negative.
- **Inline-Split-Guard erweitert** um `=` (relevant nur fuer JSON-Fragment-Tokens; normale Tokens enthalten kein `=`).
- **Line-Scope-Erkennung** beruecksichtigt auch `\t`/Tab in Patterns.
- **Progress-Ausgabe nur auf Terminals**: `\r`/ANSI-Steuerzeichen verschmutzen keine Pipes/Cron-Logs mehr (`sys.stderr.isatty()`).
- **test_permission_denied** wird als root uebersprungen (root ignoriert chmod 000 - Test schlug in Docker/CI fehl).

---

## v1.6.0 (2026-07-04) – Erkennungsmatrix 1.6.0 + Erkennungs-Bugfixes

### Kritische Bugfixes (False Negatives)
- **VSNR-Erkennung repariert**: Das alte Regexp `^\s*(\d{2})\s*(\d{6})\s*([A-Z])\s*(\d{2})\s*(\d{1})\s*$` konnte auf Token-Ebene nie matchen (Tokens enthalten keine Leerzeichen, `^`/`$`-Anker scheiterten an angeklebten Doppelpunkten, `[A-Z]` ohne Kleinbuchstaben). Jetzt zwei Muster: `vsnr` (kompakt, tokenbasiert) und `vsnr_formatiert` (amtliches Format mit Leerzeichen, zeilenbasiert).
- **Zeilenbasierte Regexp-Muster**: Muster, die Whitespace enthalten (`\s` oder Leerzeichen), werden automatisch gegen die ganze Zeile statt gegen einzelne Tokens geprueft. Repariert zusaetzlich: SSH/TLS-Private-Key-Header (mehrteilige Tokens), Telefonnummern mit Leerzeichen, IBAN/Kreditkarte mit Leerzeichen, NATO/STRENG-GEHEIM-Einstufungen, SG-Aktenzeichen.
- **Prefilter-Luecke geschlossen**: Zeilen mit >=5 zusammenhaengenden Ziffern passieren den Prefilter immer (numerische PII wie VSNR, KVNR, Steuer-ID, IBAN hatte keinen Text-Marker und wurde bei `prefilter=all/regexp_field` komplett verworfen). Default in detecto.ini auf `off` geaendert (Erkennungsrate vor Geschwindigkeit).
- **Prefilter-Tokenisierung angeglichen**: Der Prefilter splittet jetzt wie der Analyzer (auch auf `= & ? , ; |`), vorher gingen String-Findings in key=value-Zeilen verloren.
- **key:value in einem Token**: `RVNR:65170839J008` oder `"password":"x"` (Tokenizer splittet nicht auf `:`) wird jetzt inline in Feldname und Wert zerlegt.
- **minlen 5 -> 4** (detecto.ini): 4-Buchstaben-Vornamen/Orte (Anna, Emma, Bonn, Kiel) wurden nie gefunden.
- **search_feld/search_field**: Der INI-Key `search_feld` wurde vom Code (`search_field`) ignoriert - beide Schreibweisen werden akzeptiert.

### Weitere Bugfixes (Audit)
- `highlight()`/`_mark_log()`: Werte mit Backslash (z.B. `DOMAIN\user`) crashten die Ergebnisausgabe bzw. verschluckten Excel-Marker (re.sub-Escape-Bug). Ersetzung nur noch an Token-Grenzen, Feld-Markierung nur beim ersten Treffer.
- CLI-Werte werden geclampt: `--critical 0` unterdrueckte still alle Findings, `--examplecount -1` verschluckte Beispiele.
- `--logresult` und `--logresultanon` sind jetzt kombinierbar (vorher gewann anon still).
- Statistik respektiert `--critical` und weist ausgeblendete Findings aus.
- Kritikalitaet in CSVs wird auf 1-5 geclampt (Tippfehler `krit=6` machte Muster unsichtbar).
- Anonymizer maskiert kurze Werte (<= erste s-Gruppe + 1) vollstaendig statt sie fast im Klartext zu lassen.
- Warnung bei doppelten Muster-Namen ueber regexp/field/suchmuster hinweg.
- detecto.ini mit ungueltigen Zahlen/Booleans crasht nicht mehr (Warnung + Default).
- Excel String-Sheet riet Dateinamen (`ort.csv` statt `orte.csv`) - Spalte entfernt.
- Chunk-Parallel-Test testete tatsaechlich sequenziell (totes Instanzattribut) - gefixt.

### Neue Erkennungsarten (Datenarten-Erkennungsmatrix 1.6.0)
- **regexp.csv: 13 -> 35 Muster**: KVNR, Personalausweis-Nr., IPv4 (oeffentlich/RFC1918), MAC, IMEI, Kfz-Kennzeichen, BIC, USt-IdNr., Handelsregister-Nr., Kindergeld-Nr., AWS Access Key, Azure AccountKey, GitHub-Token, Slack-Token, Lizenzschluessel, VS-/NATO-/EU-Einstufungen, STRENG GEHEIM, SG-Aktenzeichen, Source-Code-URLs.
- **field.csv: 17 -> 120 Muster**: alle Art.-9-DSGVO-Kategorien, Sozialdaten (SGB), RV-spezifische Felder (Entgeltpunkte, Rentenart, DEUEV, Kontenklaerung, ...), Personalaktendaten, besonderer Schutzbedarf, Betriebspruef-/Compliance-Daten, Verzeichnisdienste u.v.m. (konsolidiert, FP-traechtige Einzelbegriffe entschaerft).
- **suchmuster: 5 -> 7 Kategorien**: neu `verschlusssachen.csv` (VS-NfD, ...) und `sperrvermerke.csv` (Sperrvermerk, Auskunftssperre, ...) jeweils Kritikalitaet 1.
- Stopwoerter regexp: 0.0.0.0, 127.0.0.1, hinweg/vorweg/umweg (strasse-Muster).

### Bekannte Grenzen (dokumentiert)
- `prefilter=all/regexp_field` kann weiterhin Field-Findings ohne Marker/Ziffern verlieren - Markerliste deckt nicht alle 120 Feldmuster ab (daher Default `off`).
- Umlaut-Transliteration: `Mueller` im Log matcht nicht `Müller` in der Suchliste (normalize entfernt nur Diakritika).
- Amtlich formatierte Werte, die ueber Feld-Lookahead erfasst werden, bleiben tokenbasiert.

### Tests
- 105 Tests (104 bestehende gruen + neuer Verifikationslauf), `test_findings.log` mit 60 Zeilen, die jeweils mindestens ein Finding liefern.

---

## v1.4 (2026-04-12) – Pure-Python Hot-Path-Optimierung

### Performance
- **Method-Inlining**: `_check_regexp()`, `_check_field()` und `_add_hit()` komplett in `_analyze_line()` inline integriert. Eliminiert ~1 Milliarde Python-Methodenaufrufe bei 17M Zeilen.
- **Lokale Variable Caches**: Alle Attribut-Lookups (`self.regexp`, `self.sw_search`, etc.) werden vor der Token-Schleife als lokale Variablen gecacht. Spart ~100ns pro Lookup * ~20 Tokens * 17M Zeilen.
- **ASCII-Fast-Path in normalize()**: `str.isascii()` Check ueberspringt die teure NFD-Dekomposition fuer ~80% aller Log-Tokens (Timestamps, HTTP-Verben, Pfade, Zahlen).
- **findall statt split+filter**: `_TOKEN_RE.findall(line)` ersetzt `[t for t in _SPLIT_RE.split(line) if t]`. Liefert direkt eine Liste ohne Leer-Strings, spart die Filter-Iteration.
- **Prefilter Strip-Konstante**: Strip-Chars als Modul-Konstante statt String-Literal in der Schleife.
- **Prefilter Marker als Tuple**: Leicht schnellere Iteration als set fuer Substring-Checks.

### Geschwindigkeitsvergleich
| Szenario | v1.3 | v1.4 | Speedup |
|----------|------|------|---------|
| 1 Datei, Single-Core | ~258k Z/s | ~360-440k Z/s | ~1.4-1.7x |
| 1 Datei, mit Prefilter | ~507k Z/s | ~700k+ Z/s | ~1.4x |

### Keine neuen Dependencies
Alle Optimierungen sind reines Python – kein C-Compiler, kein Bloom-Filter, keine Build-Schritte noetig.

---

## v1.3 (2026-04-12) – Performance-Optimierung II

### Performance
- **Reverse-Index statt Aho-Corasick**: String-Suche ueber `dict[str, list[str]]` mit O(1)-Lookup pro Token. Ersetzt den bisherigen Aho-Corasick-Missbrauch (der AC als dict nutzte statt als Textscanner). `pyahocorasick` Abhaengigkeit entfernt.
- **Single-Pass Token-Verarbeitung**: Regexp, Field und String werden in einer einzigen Schleife geprueft. Tokens werden nur einmal normalisiert statt zweimal. Spart ~340M Cache-Lookups bei 17M Zeilen.
- **Min-Length Guards**: Tokens <5 Zeichen ueberspringen Regexp-Checks, <3 Zeichen ueberspringen Field-Checks. Eliminiert ~30-50% unnoetige Regex-Ausfuehrungen.
- **Chunk-Parallelisierung**: Einzelne grosse Dateien (>10MB) werden in Byte-Chunks aufgeteilt und parallel analysiert. Ermoeglicht Multi-Core-Nutzung auch bei nur einer Logdatei.
- **Tokenizer Fast-Paths**: URL-Regex nur bei `://`, URL-Param-Regex nur bei `?`/`&`. Ueberspringt ~95% der Zeilen.
- **MAX_EXAMPLES_PER_VALUE**: Max. 100 Beispielzeilen pro Wert (konfigurierbar via `max_examples` in detecto.ini). Reduziert Speicherverbrauch bei vielen Treffern erheblich.

### Geschwindigkeitsvergleich
| Szenario | v1.2 | v1.3 | Speedup |
|----------|------|------|---------|
| 1 Datei, Single-Core | ~165k Z/s | ~258k Z/s | ~1.6x |
| 1 Datei, mit Prefilter | ~165k Z/s | ~507k Z/s | ~3x |
| 1 grosse Datei, Multi-Core | nicht moeglich | verfuegbar | Neu |

### Neue INI-Parameter
- `max_examples = 100` – Max. Beispielzeilen pro gefundenem Wert (Speicheroptimierung)

### Tests
- 92 Tests (vorher 72): 20 neue Tests fuer Reverse-Index, MaxExamples, MinLength-Guards, Chunk-Berechnung, Single-File-Parallelisierung
- Neuer Performance-Smoke-Test (`tests/test_performance_smoke.py`) mit 50k synthetischen Zeilen

---

## v1.2 (2026-04-12) – Performance-Optimierung

### Performance
- **Multiprocessing**: Bei >1 Logdatei parallele Verarbeitung mit `multiprocessing.Pool`. Konfigurierbar: `workers=0` (auto/cpu_count) oder `workers=N` in detecto.ini.
- **parse_json=false**: Neuer INI-Parameter. Ueberspringt JSON-Parsing fuer 2-3x schnellere Tokenisierung bei Plain-Text-Logs.
- **Aho-Corasick**: Optionale Abhaengigkeit `pyahocorasick` fuer O(n) String-Matching statt O(n*m). Automatischer Fallback auf Standard-Suche.
- **LRU-Cache normalize()**: `@functools.lru_cache(maxsize=100_000)` fuer die Unicode-Normalisierung. Eliminiert redundante Berechnungen bei wiederholten Tokens.
- **Micro-Optimierungen**: `'{' in text` Pre-Check vor JSON-Fragment-Suche. Fast-Path in tokenize() bei parse_json=false.

### Geschwindigkeitsvergleich
| Szenario | v1.1 | v1.2 | Speedup |
|----------|------|------|---------|
| 1 Datei, Plain-Text | ~15k Z/s | ~40k Z/s | ~2.5x |
| 1 Datei, parse_json=false | ~15k Z/s | ~60k Z/s | ~4x |
| 7 Dateien, parallel | ~15k Z/s | ~100k+ Z/s | ~7x |
| + Aho-Corasick | - | +20-30% | zusaetzlich |

### Neue INI-Parameter
- `parse_json = false` – JSON-Parsing deaktivieren (schneller bei Plain-Text-Logs)
- `workers = 0` – Parallele Worker (0=auto, 1=single-process)

---

## v1.1 (2026-04-12)

### Pattern-Verbesserungen (Massnahmen 1-5)
- **Regexp-Anker entfernt**: 6 Pattern (Email, JWT, Kreditkarte, IBAN, SteuerID, PLZ) matchen jetzt im Fliesstext statt nur als Vollmatch.
- **Kreditkarte mit Formatierung**: `4532-1111-2222-3333` und `4532 1111 2222 3333` werden erkannt.
- **IBAN mit Leerzeichen**: `DE89 3704 0044 0532 0130 00` wird erkannt.
- **6 neue Field-Pattern**: Credential (pwd/secret/cred), AuthHeader (Offset 2), CloudKey (AWS/Azure/GCP), ProxyAuth, SmtpAuth, BindPW. Total: 17 Field-Muster.
- **Diagnosen erweitert**: 10 -> 100 Eintraege (Onkologie, Infektionen, Neurologie, Psychiatrie, Kardiologie, etc.).
- **Sicherheitsbegriffe erweitert**: 8 -> 52 Eintraege (credentials, token, secret, certificate, etc.).

### Tokenizer-Verbesserungen (Massnahme 6)
- **URL-Credential-Extraktion**: `jdbc:oracle://admin:P@ssw0rd!@host` extrahiert User und Passwort separat. Behandelt `@` in Passwoertern korrekt.

### Analyse-Verbesserungen
- **Fortschrittsanzeige**: Progress-Status auf stderr bei grossen Datenmengen (Datei, Zeilen, Geschwindigkeit, Findings). Konfigurierbar: `refresh_status=5` in detecto.ini (0=deaktiviert).

### Dokumentation
- **Datenarten-Erkennungsmatrix.xlsx**: 166 Datenvarianten in 17 Kategorien mit Detecto-Erkennungsmustern.
- **Detecto_Verbesserungskonzept.docx**: 10 Massnahmen in 4 Phasen (~45h, 6 Wochen).
- **Dok1_Datenschutz_Pruefscope.docx**: Pruefscope, Datenarten-Katalog, Pruefauftrag-Vorlage.
- **Dok2_ELK_Betriebshandbuch.docx**: Technische Anleitung inkl. Stopwort-Vorab-Bereinigung.
- **Dok3_Fachbereich_Finding_Bewertung.docx**: Finding-Bewertung mit Beispielen.

---

## v1.0 (2026-04-11)

### Architecture
- **Modular package**: 12 modules under `src/detecto/`, each ~100-150 lines.
- **Classes**: `Anonymizer`, `LogAnalyzer`, `DetectoConfig` dataclass, `ExportContext` dataclass, `_SheetBuilder`.
- **Centralized constants**: `constants.py` with all ANSI colors, Excel colors, limits, delimiters.
- **Consistent English API**: `load_regexp()`, `analyze()`, `normalize()`, `find_logfiles()`, `highlight()`, `build_result_lines()`, `export_xlsx()`, `find_field_value()`, `extract_json_fragments()`.
- **Type hints**: `from __future__ import annotations` throughout (Python 3.9+).
- **Logging**: DEBUG for tokenization/JSON, INFO for patterns/analysis, WARNING for errors. `--verbose` flag for debug output.
- **pathlib.Path** for file operations.
- **json.JSONDecoder().raw_decode()** with bracket-balancing fallback.

### Security
- **Regex DoS protection**: `_safe_compile()` with SIGALRM timeout (2 sec).
- **Path traversal protection**: `_validate_path()` with `Path.resolve()` check.
- **CSV/Excel injection prevention**: `_sanitize_cell()` prefixes formula chars.
- **Memory bounded**: `MAX_HITS_PER_PATTERN = 10,000` prevents unbounded growth.
- **UTF-8 safety**: Binary reading with decode warning on first non-UTF-8 byte.
- **Config validation**: `__post_init__()` clamps values to sane ranges.

### Excel Export
- Plain-text markers (`>>>VALUE<<<`, `[FELD:token]`), no Rich Text/XML post-processing.
- `_SheetBuilder` with `add_rows()` (bold_cols, wrap_cols, fill_cols, krit_col, center_cols).
- `ExportContext` dataclass replaces 14+ function parameters.
- 6 sheets: Findings, Full (optional), Tool, Regexp, Field, String.

### Testing
- 69 pytest tests across 5 modules.
- Security tests: path traversal, regex DoS, CSV injection, config clamping.
- `monkeypatch` for runtime constants.

### Packaging
- `pyproject.toml`: setuptools, entry-point `detecto`, ruff/mypy/black config.
- `Makefile`: `make dist`, `make test`, `make clean`.
- `detecto_cli.py` wrapper for backwards compatibility.

### Package Structure
```
src/detecto/
  __init__.py       VERSION, __version__
  __main__.py       python -m detecto
  constants.py      ANSI colors, Excel colors, limits, delimiters
  config.py         DetectoConfig, load_config()
  utils.py          normalize(), find_logfiles(), krit_color()
  anonymizer.py     Anonymizer class
  loaders.py        load_regexp/field_patterns/search_patterns/stopwords
  tokenizer.py      tokenize(), extract_json_fragments(), find_field_value()
  analyzer.py       LogAnalyzer.analyze()
  formatter.py      print_header/status/results(), highlight(), build_result_lines()
  exporter.py       export_xlsx/log(), ExportContext, _SheetBuilder
  cli.py            parse_args(), main(), --verbose
```

---

## v0.9 (2026-04-11)

### Neue Features
- **Excel-Export `--xlsx [DATEI]`**: Exportiert Findings als Excel-Datei fuer die Kundenbearbeitung. Findings-Sheet mit leeren Spalten (Bearbeiter, Finding, Kommentar) fuer den Verfahrensverantwortlichen, sortiert nach Kritikalitaet, Art, Muster. Zusaetzliche Sheets: Tool (Scan-Infos), Regexp, Field, String (Muster-Uebersicht).
- **Full-Sheet in Excel**: Bei `--full --xlsx` wird ein zusaetzliches Arbeitsblatt "Full" mit 7 Spalten (Logdatei, Art, Muster, Kritikalitaet, Gefundener Wert, Feld, Logeintrag). Gefundener Wert hat roten Hintergrund, Feld gruenen Hintergrund. Treffer im Logeintrag als `>>>WERT<<<` und `[FELD:token]` markiert.
- **Excel-Anonymisierung `--excelanon`**: Anonymisiert Werte in der Excel-Datei unabhaengig von `--anon`. Wirkt auf Findings- und Full-Sheet.
- **Konfigurierbares Anonymisierungsmuster `anon_muster`**: In `detecto.ini` konfigurierbar. Unterstuetzt Muster wie `sss**sss**`, `ssss****ss**`, `ssssxxxxssxx` und `<redacted>` (komplette Ersetzung). s=Original, */x=Stern.
- **Suchtypen ein-/ausschaltbar**: `search_regexp`, `search_field`, `search_suchmuster` in `detecto.ini` (on/off) steuern welche Erkennungstechniken aktiv sind.
- **Kommentare in detecto.ini**: `#` am Zeilenanfang wird als Kommentar ignoriert.
- **Testsuite**: `test_detecto.py` mit 34 automatisierten Tests (unittest). Abdeckung fuer Anonymisierung, Field-Erkennung, Tokenisierung, Excel-Export und End-to-End.

### Bugfixes
- **Excel-Reparaturmeldung behoben**: CellRichText und XML-Post-Processing (fix_rpr_order, fix_text_preserve, zipfile-Rewrite) komplett entfernt. Stattdessen robuste Plain-Text-Markierung und Hintergrundfarben. Keine Reparaturmeldung mehr beim Oeffnen in Excel.
- **anon_muster Crash behoben**: `parse_anon_muster()` mit ungueltigem oder leerem Muster (z.B. `"abc"`, `""`) fuehrte zu ZeroDivisionError in `redact()`. Jetzt Fallback auf Default-Muster und Guard-Clause.
- **Field-Erkennung Separatoren**: Neue Funktion `finde_field_wert()` ueberspringt Separatoren (`->`, `=>`, `:`, `=`) und leere Wrapper-Tokens. `password -> Produktiv!1` erkennt jetzt `Produktiv!1` statt `->`.
- **Tokenisierung JSON-Fragmente**: Neue Funktion `extrahiere_json_fragmente()` mit Klammer-Balancing. Eingebettete JSON-Objekte `{...}` werden als Ganzes erhalten und zusaetzlich intern tokenisiert. Keine abgeschnittenen Tokens wie `{"street":"Gartenweg` mehr.

---

## v0.8 (2026-04-11)

### Neue Features
- **Parameter `--critical N`**: Filtert Findings nach Kritikalitaet (1=nur kritisch, 5=alle).
- **Parameter `--showskipped`**: Zeigt auch Muster ohne Treffer an (`<nothing found>`).
- **Konfigurationsdatei `detecto.ini`**: Default-Werte fuer alle Parameter und Dateipfade. `--status` zeigt INI-Defaults an.
- **Kritikalitaetsstufen (1-5)**: Alle Muster (regexp, field, suchmuster) mit Kritikalitaet bewertet. Farbige Anzeige in Konsole und Status.
- **`suchmuster.csv`**: Umbenannt von `suchmuster.txt`, einheitlicher `::` Trenner.
- **Farbige Konsolenausgabe**: `[regexp]`/`[string]` hellgruen, `[field]` hellgelb, Kritikalitaet farbig (rot/gelb), Feldnamen gelb, Treffer rot. Dunkelgruen fuer Feld-Token in `--full`.
- **Parameter `--nocolor`**: Deaktiviert alle ANSI-Farbcodes.

---

## v0.7 (2026-04-11)

### Neue Features
- **Field-Erkennung `[field]`**: Neue dritte Erkennungstechnik. Erkennt kritische Feldnamen (z.B. password, Kennwort) in Tokens und erfasst den Wert im naechsten Token. Konfigurierbar ueber `field.csv` mit optionalem Offset-Parameter.
- **Erweiterte Regexp-Muster**: 12 Regexp-Muster fuer JWT, SSH/TLS Private Keys, Kreditkarten, IBAN, Steuer-ID, Telefonnummern, PLZ, JDBC Connection Strings.
- **Erweiterte Field-Muster**: 11 Field-Muster fuer Passwoerter, Oracle-Passwoerter (identified by), API-Keys, Access/Refresh Tokens, Session-IDs, Client Secrets, DB-Passwoerter, Reisepass/Personalausweis, Diagnosen, Geburtsdaten.
- **Stopwort-Listen**: Drei Stopwort-Dateien (`stopword_regexp.txt`, `stopword_field.txt`, `stopword_suchmuster.txt`) zur Reduzierung von False Positives. Case-insensitive und umlaut-normalisiert.
- **Field-Offset**: Field-Muster unterstuetzen optionalen Offset-Parameter (4. Feld in field.csv). Ermoeglicht Erkennung von Mustern wie `identified by <passwort>` (Offset 2).
- **Field-Wert-Bereinigung**: Automatisches Entfernen von Anfuehrungszeichen, Klammern und Sonderzeichen am Anfang/Ende von Field-Werten. Pfade (/, \, ~/), Windows-Laufwerke (C:) und Sternchen-Folgen werden ignoriert.
- **Farbige Konsolenausgabe**: `[regexp]` und `[string]` in hellgruen, `[field]` in hellgelb, Feldnamen in hellgelb, Treffer in Log-Zeilen rot hervorgehoben.
- **Parameter `--nocolor`**: Deaktiviert die farbliche Ausgabe komplett.
- **Suchmuster Diagnosen**: Neue Suchmuster-Datei `diagnosen.csv` mit medizinischen Begriffen (Diabetes, Burnout, Hepatitis, ...).
- **Suchmuster Sicherheitsbegriffe**: Neue Suchmuster-Datei `sicherheitsbegriffe.csv` mit sicherheitsrelevanten Begriffen (keystore, privateKey, vault-password, ...).
- **Telefon-Regexp getuned**: Mindestlaenge 10 Zeichen, muss mit + oder 0 beginnen, Punkt als Trennzeichen entfernt (verhindert Datums-False-Positives).

- **Kritikalitaetsstufen**: Alle Muster (regexp, field, suchmuster) mit Kritikalitaet 1-5 bewertet (kritisch, hoch, mittel, niedrig, info). Farbige Anzeige in Ausgabe und Status.
- **Parameter `--critical N`**: Filtert Findings nach Kritikalitaet (1=nur kritisch, 5=alle).
- **Parameter `--showskipped`**: Zeigt auch Muster ohne Treffer an (`<nothing found>`).
- **Konfigurationsdatei `detecto.ini`**: Default-Werte fuer alle Parameter (examplecount, minlen, critical, anon, full, nocolor) und Dateipfade. Kommandozeile ueberschreibt INI-Werte. `--status` zeigt INI-Defaults an.
- **`suchmuster.txt` umbenannt zu `suchmuster.csv`**: Einheitliches `::` als Trenner in allen Konfigurationsdateien.

### Parameter (neu)
- `--nocolor` - Deaktiviert alle ANSI-Farbcodes in der Ausgabe
- `--critical N` - Nur Findings bis Kritikalitaet N anzeigen (Standard: 5)
- `--showskipped` - Zeigt auch Muster ohne Treffer an

### Konfigurationsdateien (neu/geaendert)
- `detecto.ini` - Default-Werte fuer Parameter und Dateipfade
- `field.csv` - Field-Muster (Format: name::krit::beschreibung::regexp[::offset])
- `regexp.csv` - Format erweitert: name::krit::beschreibung::pattern
- `suchmuster.csv` - Umbenannt von suchmuster.txt, Format: name::krit::dateiname.csv
- `stopword_regexp.txt` - Stopwoerter fuer Regexp-Erkennung
- `stopword_field.txt` - Stopwoerter fuer Field-Erkennung
- `stopword_suchmuster.txt` - Stopwoerter fuer String-Erkennung
- `suchmuster/diagnosen.csv` - Medizinische Begriffe
- `suchmuster/sicherheitsbegriffe.csv` - Sicherheitsrelevante Begriffe

---

## v0.5 (2026-04-11)

### Neue Features
- **Parameter `--logresult`**: Speichert das Ergebnis (nicht anonymisiert) in eine Datei. Optional mit benutzerdefiniertem Dateinamen, sonst `detecto_<timestamp>.log`.
- **Parameter `--logresultanon`**: Speichert das Ergebnis anonymisiert in eine Datei.
- **Aufruf in Logdatei**: Die gespeicherte Logdatei enthaelt den vollstaendigen Detecto-Aufruf.
- **Statistik**: Am Ende der Ausgabe werden analysierte Logdateien, Zeilenanzahl und Analyse-Dauer buendig angezeigt.
- **Dokumentation**: readme.md, firststeps.md, changelog.md und prompt_documentation.md erstellt. Hilfe-Ausgabe verweist auf Dokumentationsdateien.

---

## v0.4 (2026-04-10)

### Neue Features
- **JSON-Log Unterstuetzung**: Erkennung und Verarbeitung von JSON-formatierten Logdateien (Liberty JSON-Format). JSON-Werte werden rekursiv extrahiert und tokenisiert.
- **Parameter `--status`**: Zeigt eine Zusammenfassung der geladenen Suchdaten an.
- **Parameter `--minlen`**: Mindestlaenge fuer Suchmuster-Strings konfigurierbar (Standard: 5, Minimum: 2).
- **Parameter `--full` mit `--anon`**: Bei aktiviertem `--anon` werden auch in den Log-Zeilen die gefundenen Werte redacted dargestellt.
- **Logdateiname in `--full` Ausgabe**: z.B. `[log1.log]` vor jeder Zeile.
- **Mehrere Logdateien**: Shell-expandierte Globs werden korrekt verarbeitet.
- **Umlaut-Normalisierung**: Case-insensitive und umlaut-normalisierte Suche.
- **Header immer sichtbar**: Bei jedem Aufruf.

### Bugfixes
- **UnicodeDecodeError**: `errors="replace"` fuer nicht-UTF-8 Logdateien.
- **Glob-Expansion**: Umstellung auf `nargs="*"`.

### Datenbereinigung
- **orte.csv**: Zusaetze, mehrteilige Namen, Bindestriche, Bad/St./Sankt entfernt. 5000 -> 4502 Eintraege.
- **vornamen.csv**: Bindestriche, Duplikate, Ueberschneidungen mit Orten (13) und Nachnamen (180) entfernt. 5000 -> 3436 Eintraege.
- **nachnamen.csv**: Ueberschneidungen mit Orten (188) entfernt. 5000 -> 4051 Eintraege.

---

## v0.3 (2026-04-10)

### Neue Features
- **Parameter `--examplecount`**, `--anon`, `--full`, `--help`
- **Hilfe ohne Parameter**: Aufruf ohne Argumente zeigt Hilfeseite.
- **Erkennungstyp**: `[regexp]` oder `[string]` vor jedem Ergebnis.
- **Header**: Version, Datum und Copyright.

### Bugfixes
- **Mehrteilige Token**: URL-Parameterwerte als Ganzes extrahiert.

---

## v0.1 (2026-04-10)

### Initiale Version
- Log-Dateien scannen, Tokenisierung, Regexp-Suche, String-Suche, Zusammenfassung mit max. 3 Beispielen, MIT Lizenz.
