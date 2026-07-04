# Detecto - Erste Schritte

## 0. Installation und wichtigste Befehle

```bash
pip install -e .          # Installieren
detecto test.log          # Scan ausfuehren
make test                 # Tests ausfuehren
make dist                 # Distribution erstellen (dist/detecto_1.6.1.zip)
```

## 1. Schnellstart

```bash
cd /pfad/zu/Detecto

# Option A: pip install (empfohlen)
pip install -e .
detecto test.log

# Option B: Ohne Installation
python3 detecto_cli.py test.log

# Option C: Als Python-Modul
PYTHONPATH=src python3 -m detecto test.log
```

## 2. Mehrere Logdateien scannen

```bash
# Alle .log Dateien
detecto *.log

# Bestimmte Dateien
detecto server1.log server2.log

# Mit Glob-Muster
detecto log*.log
```

## 3. Mehr Beispiele anzeigen

Standardmaessig werden 3 Beispiele pro Fundtyp angezeigt:

```bash
detecto test.log --examplecount=5
```

## 4. Log-Zeilen der Treffer anzeigen

Mit `--full` wird die komplette Log-Zeile jedes Treffers angezeigt. Die gefundenen Werte sind farblich hervorgehoben (regexp/string gruen, field gelb, Treffer rot):

```bash
detecto test.log --full
```

## 5. Anonymisierte Ausgabe

Zum Teilen von Ergebnissen ohne sensible Daten preiszugeben:

```bash
# Bildschirmausgabe anonymisiert
detecto test.log --anon

# Kombination: anonymisiert mit Log-Zeilen
detecto test.log --anon --full
```

Anonymisierung: `amelie.hofmann@beispiel.de` wird zu `ame**e.h**man**bei**iel**e`

## 6. Ergebnisse in Datei speichern

```bash
# Nicht anonymisiert speichern (automatischer Dateiname)
detecto test.log --logresult

# Mit benutzerdefiniertem Dateinamen
detecto test.log --logresult=ergebnis.log

# Anonymisiert speichern
detecto test.log --logresultanon=ergebnis_anon.log
```

Die gespeicherte Datei enthaelt keine ANSI-Farbcodes und ist damit gut archivierbar.

## 7. Farben deaktivieren

```bash
detecto test.log --nocolor
```

## 7a. Debug-Ausgabe (--verbose)

Zeigt detaillierte Informationen zu JSON-Parsing, Stopwords und Pattern-Pfaden:

```bash
detecto test.log --verbose
```

## 7b. Fortschrittsanzeige bei grossen Datenmengen

Bei der Analyse grosser Log-Dateien zeigt Detecto automatisch den Fortschritt an:

```
[3/17] liberty_messages_1000000.log: 450,000 Zeilen | Gesamt: 2,450,000 | 125,000 Zeilen/s | 847 Findings
```

Die Aktualisierungsrate ist ueber `detecto.ini` konfigurierbar:

```ini
# Sekunden zwischen Updates (0 = deaktiviert)
refresh_status = 5
```

## 7c. Performance-Optimierung

Fuer grosse Datenmengen (Millionen Zeilen):

```ini
# detecto.ini – Performance-Einstellungen
parse_json = false    # JSON-Parsing deaktivieren (2-3x schneller)
workers = 0           # Parallele Worker (0=auto, 1=single)
refresh_status = 5    # Fortschritts-Update alle 5 Sekunden
```

```bash
# Schneller Scan ohne JSON (Plain-Text-Logs)
detecto *.log --xlsx report.xlsx
```

## 8. False Positives reduzieren

Kurze Suchbegriffe (z.B. Ortsname "Au" mit 2 Zeichen) erzeugen viele Fehlalarme. Mit `--minlen` kann die Mindestlaenge angepasst werden:

```bash
# Standard: Mindestlaenge 4 (findet auch Anna, Emma, Bonn, Kiel)
detecto test.log

# Auch kurze Begriffe ab 3 Zeichen finden
detecto test.log --minlen=3

# Konservativer (weniger False Positives)
detecto test.log --minlen=5
```

Zusaetzlich koennen Stopwort-Listen gepflegt werden:
- `stopword_regexp.txt` - fuer Regexp-False-Positives
- `stopword_field.txt` - fuer Field-False-Positives (z.B. `and`, `for`, `WITH`)
- `stopword_suchmuster.txt` - fuer String-False-Positives

## 9. Status der Suchdaten pruefen

```bash
detecto --status
```

Zeigt an, wie viele Muster und Eintraege geladen sind:

```
=== Detecto - Status ===

Default-Werte (detecto.ini):
  examplecount:            10
  minlen:                  4
  critical:                5
  anon:                    False
  full:                    False
  nocolor:                 False

Regexp: 35
  [kritisch] JWT: JSON Web Token (eyJ...)
  [hoch] vsnr: Deutsche Rentenversicherungsnummer (kompakt)
  [hoch] vsnr_formatiert: Deutsche Rentenversicherungsnummer (formatiert)
  [niedrig] email: Regexp fuer Email
  ...
Field: 120
  [kritisch] Passwort: Regexp fuer Passworte (offset: 1)
  [kritisch] OraclePasswort: Oracle identified by (offset: 2)
  [kritisch] Credential: Generische Credential-Felder
  [kritisch] CloudKey: Cloud-Provider Schluessel
  ...
Suchmuster: 7
  [niedrig] Vornamen: 3462 Eintraege
  [mittel] Diagnosen: 100 Eintraege
  [kritisch] Verschlusssachen: 10 Eintraege
  [kritisch] Sperrvermerke: 7 Eintraege
  ...
```

## 10. Nur kritische Findings anzeigen

```bash
# Nur kritisch (Stufe 1)
detecto server.log --critical=1

# Kritisch und hoch (Stufe 1-2)
detecto server.log --critical=2

# Alle Muster anzeigen, auch ohne Treffer
detecto server.log --critical=2 --showskipped
```

## 11. Excel-Report erstellen

```bash
# Findings als Excel exportieren
detecto server.log --xlsx

# Mit benutzerdefiniertem Dateinamen
detecto server.log --xlsx=report.xlsx

# Mit Full-Sheet (Logeintraege mit farbiger Hervorhebung)
detecto server.log --xlsx --full

# Excel anonymisiert (unabhaengig von --anon)
detecto server.log --xlsx --excelanon

# Kombination
detecto server.log --xlsx=report.xlsx --full --excelanon --critical=2
```

Die Excel-Datei enthaelt Arbeitsblaetter fuer Findings, Full (optional), Tool, Regexp, Field und String.
Das Findings-Sheet hat leere Spalten (Bearbeiter, Finding, Kommentar) fuer die Bearbeitung durch den Verfahrensverantwortlichen.

## 12. Typischer Workflow

```bash
# 1. Status pruefen
detecto --status

# 2. Schneller Scan
detecto server.log

# 3. Details anzeigen
detecto server.log --full --examplecount=10

# 4. Excel-Report erstellen (anonymisiert, nur kritisch+hoch)
detecto server.log --xlsx=report.xlsx --full --excelanon --critical=2

# 5. Ergebnis als Textdatei speichern
detecto server.log --logresultanon=bericht.log

# 6. Ohne Farben (z.B. fuer Weiterverarbeitung)
detecto server.log --nocolor > ergebnis.txt
```

## 13. Tests ausfuehren

```bash
make test
# oder: PYTHONPATH=src python3 -m pytest tests/ -v
```

## 14. Hilfe anzeigen

```bash
detecto --help
```
